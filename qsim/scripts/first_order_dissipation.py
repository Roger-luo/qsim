import itertools

import sys
import numpy as np
import scipy.integrate
import scipy.optimize
from odeintw import odeintw
import matplotlib.pyplot as plt
import networkx as nx

import scipy.sparse as sparse
from scipy.linalg import expm
from scipy.sparse.linalg import expm_multiply

from qsim.codes import qubit
from qsim.codes.quantum_state import State
from qsim.evolution import lindblad_operators, hamiltonian
from qsim.graph_algorithms.graph import Graph
from qsim.graph_algorithms.graph import line_graph, degree_fails_graph, ring_graph
from qsim.lindblad_master_equation import LindbladMasterEquation
from qsim.schrodinger_equation import SchrodingerEquation
from qsim.tools import tools


class EffectiveOperatorHamiltonian(object):
    def __init__(self, omega_g, omega_r, energies=(1,), graph: Graph = None, IS_subspace=True, code=qubit):
        # Just need to define self.hamiltonian
        assert IS_subspace
        self.energies = energies
        self.IS_subspace = IS_subspace
        self.graph = graph
        self.omega_r = omega_r
        self.omega_g = omega_g
        self.code = code
        assert self.code is qubit

        if self.IS_subspace:
            # Generate sparse mixing Hamiltonian
            assert graph is not None
            assert isinstance(graph, Graph)
            # We have already solved for this information
            IS, nary_to_index, num_IS = graph.independent_sets, graph.binary_to_index, graph.num_independent_sets
            self.transition = (0, 1)
            self._hamiltonian_rr = np.zeros((num_IS, num_IS))
            self._hamiltonian_gg = np.zeros((num_IS, num_IS))
            self._hamiltonian_cross_terms = np.zeros((num_IS, num_IS))
            for k in IS:
                self._hamiltonian_rr[k, k] = np.sum(IS[k][2] == self.transition[0])
                self._hamiltonian_gg[k, k] = np.sum(IS[k][2] == self.transition[1])
            self._csc_hamiltonian_rr = sparse.csc_matrix(self._hamiltonian_rr)
            self._csc_hamiltonian_gg = sparse.csc_matrix(self._hamiltonian_gg)
            # For each IS, look at spin flips generated by the laser
            # Over-allocate space
            rows = np.zeros(graph.n * num_IS, dtype=int)
            columns = np.zeros(graph.n * num_IS, dtype=int)
            entries = np.zeros(graph.n * num_IS, dtype=float)
            num_terms = 0
            for i in IS:
                for j in range(len(IS[i][2])):
                    if IS[i][2][j] == self.transition[1]:
                        # Flip spin at this location
                        # Get binary representation
                        temp = IS[i][2].copy()
                        temp[j] = self.transition[0]
                        flipped_temp = tools.nary_to_int(temp, base=code.d)
                        if flipped_temp in nary_to_index:
                            # This is a valid spin flip
                            rows[num_terms] = nary_to_index[flipped_temp]
                            columns[num_terms] = i
                            entries[num_terms] = 1
                            num_terms += 1
            # Cut off the excess in the arrays
            columns = columns[:2 * num_terms]
            rows = rows[:2 * num_terms]
            entries = entries[:2 * num_terms]
            # Populate the second half of the entries according to self.pauli
            columns[num_terms:2 * num_terms] = rows[:num_terms]
            rows[num_terms:2 * num_terms] = columns[:num_terms]
            entries[num_terms:2 * num_terms] = entries[:num_terms]
            # Now, construct the Hamiltonian
            self._csc_hamiltonian_cross_terms = sparse.csc_matrix((entries, (rows, columns)), shape=(num_IS, num_IS))
            try:
                self._hamiltonian_cross_terms = self._csc_hamiltonian_cross_terms.toarray()
            except MemoryError:
                self._hamiltonian_cross_terms = self._csc_hamiltonian_cross_terms

        else:
            # We are not in the IS subspace
            pass

    @property
    def hamiltonian(self):
        return self.energies[0] * (self.omega_g * self.omega_r * self._hamiltonian_cross_terms +
                                   self.omega_g ** 2 * self._csc_hamiltonian_gg +
                                   self.omega_r ** 2 * self._csc_hamiltonian_rr)

    def left_multiply(self, state: State):
        return self.hamiltonian @ state

    def right_multiply(self, state: State):
        return state @ self.hamiltonian

    def evolve(self, state: State, time):
        if state.is_ket:
            return State(expm_multiply(-1j * time * self.hamiltonian, state),
                         is_ket=state.is_ket, IS_subspace=state.IS_subspace, code=state.code, graph=self.graph)

        else:
            exp_hamiltonian = expm(-1j * time * self.hamiltonian)
            return State(exp_hamiltonian @ state @ exp_hamiltonian.conj().T,
                         is_ket=state.is_ket, IS_subspace=state.IS_subspace, code=state.code, graph=self.graph)


class EffectiveOperatorDissipation(lindblad_operators.LindbladJumpOperator):
    def __init__(self, omega_g, omega_r, rates=(1,), graph: Graph = None, IS_subspace=True, code=qubit):
        self.omega_g = omega_g
        self.omega_r = omega_r

        self.IS_subspace = IS_subspace
        self.transition = (0, 1)
        self.graph = graph
        # Construct jump operators
        if self.IS_subspace:
            # Generate sparse mixing Hamiltonian
            assert graph is not None
            assert isinstance(graph, Graph)
            if code is not qubit:
                IS, nary_to_index, num_IS = graph.independent_sets_code(self.code)
            else:
                # We have already solved for this information
                IS, nary_to_index, num_IS = graph.independent_sets, graph.binary_to_index, graph.num_independent_sets
            self._jump_operators_rg = []
            self._jump_operators_gg = []
            # For each atom, consider the states spontaneous emission can generate transitions between
            # Over-allocate space
            for j in range(graph.n):
                rows_rg = np.zeros(num_IS, dtype=int)
                columns_rg = np.zeros(num_IS, dtype=int)
                entries_rg = np.zeros(num_IS, dtype=int)
                rows_gg = np.zeros(num_IS, dtype=int)
                columns_gg = np.zeros(num_IS, dtype=int)
                entries_gg = np.zeros(num_IS, dtype=int)
                num_terms_gg = 0
                num_terms_rg = 0
                for i in IS:
                    if IS[i][2][j] == self.transition[0]:
                        # Flip spin at this location
                        # Get binary representation
                        temp = IS[i][2].copy()
                        temp[j] = self.transition[1]
                        flipped_temp = tools.nary_to_int(temp, base=code.d)
                        if flipped_temp in nary_to_index:
                            # This is a valid spin flip
                            rows_rg[num_terms_rg] = nary_to_index[flipped_temp]
                            columns_rg[num_terms_rg] = i
                            entries_rg[num_terms_rg] = 1
                            num_terms_rg += 1
                    elif IS[i][2][j] == self.transition[1]:
                        rows_gg[num_terms_gg] = i
                        columns_gg[num_terms_gg] = i
                        entries_gg[num_terms_gg] = 1
                        num_terms_gg += 1

                # Cut off the excess in the arrays
                columns_rg = columns_rg[:num_terms_rg]
                rows_rg = rows_rg[:num_terms_rg]
                entries_rg = entries_rg[:num_terms_rg]
                columns_gg = columns_gg[:num_terms_gg]
                rows_gg = rows_gg[:num_terms_gg]
                entries_gg = entries_gg[:num_terms_gg]
                # Now, append the jump operator
                jump_operator_rg = sparse.csc_matrix((entries_rg, (rows_rg, columns_rg)), shape=(num_IS, num_IS))
                jump_operator_gg = sparse.csc_matrix((entries_gg, (rows_gg, columns_gg)), shape=(num_IS, num_IS))

                self._jump_operators_rg.append(jump_operator_rg)
                self._jump_operators_gg.append(jump_operator_gg)
            self._jump_operators_rg = np.asarray(self._jump_operators_rg)
            self._jump_operators_gg = np.asarray(self._jump_operators_gg)
        else:
            # self._jump_operators_rg = []
            # self._jump_operators_gg = []
            op_rg = np.array([[[0, 0], [1, 0]]])
            op_gg = np.array([[[0, 0], [0, 1]]])
            self._jump_operators_rg = op_rg
            self._jump_operators_gg = op_gg

        super().__init__(None, rates=rates, graph=graph, IS_subspace=IS_subspace, code=code)

    @property
    def jump_operators(self):
        return np.sqrt(self.rates[0]) * (self.omega_g * self._jump_operators_gg +
                                         self.omega_r * self._jump_operators_rg)

    @property
    def liouville_evolution_operator(self):
        if self._evolution_operator is None and self.IS_subspace:
            num_IS = self.graph.num_independent_sets
            self._evolution_operator = sparse.csr_matrix((num_IS ** 2, num_IS ** 2))
            for jump_operator in self.jump_operators:
                # Jump operator is real, so we don't need to conjugate
                self._evolution_operator = self._evolution_operator + sparse.kron(jump_operator,
                                                                                  jump_operator) - 1 / 2 * \
                                           sparse.kron(jump_operator.T @ jump_operator, sparse.identity(num_IS)) - \
                                           1 / 2 * sparse.kron(sparse.identity(num_IS), jump_operator.T @ jump_operator)

        elif self._evolution_operator is None:
            # TODO: generate the evolution operator for non-IS subspace states
            raise NotImplementedError
        return self.rates[0] * self._evolution_operator


def rate_vs_eigenenergy(time, graph=line_graph(n=2), mode='hybrid', visualize=False):
    """For REIT, compute the total leakage from the ground state to a given state. Plot the total leakage versus
    the final eigenenergy"""

    # Good is a list of good eigenvalues
    # Bad is a list of bad eigenvalues. If 'other', defaults to all remaining eigenvalues outside of 'good'
    def schedule_hybrid(t, tf):
        phi = (tf - t) / tf * np.pi / 2
        energy_shift.energies = (np.sin(2 * ((tf - t) / tf - 1 / 2) * np.pi),)
        laser.omega_g = np.cos(phi)
        laser.omega_r = np.sin(phi)
        dissipation.omega_g = np.cos(phi)
        dissipation.omega_r = np.sin(phi)

    def schedule_reit(t, tf):
        phi = (tf - t) / tf * np.pi / 2
        laser.omega_g = np.cos(phi)
        laser.omega_r = np.sin(phi)
        dissipation.omega_g = np.cos(phi)
        dissipation.omega_r = np.sin(phi)

    def schedule_adiabatic(t, tf):
        phi = (tf - t) / tf * np.pi / 2
        energy_shift.energies = (2 * ((tf - t) / tf - 1 / 2),)
        laser.omega_g = np.sqrt(np.abs(np.sin(phi) * np.cos(phi)))
        laser.omega_r = np.sqrt(np.abs(np.sin(phi) * np.cos(phi)))
        dissipation.omega_g = np.sqrt(np.abs(np.sin(phi) * np.cos(phi)))
        dissipation.omega_r = np.sqrt(np.abs(np.sin(phi) * np.cos(phi)))

    laser = EffectiveOperatorHamiltonian(graph=graph, IS_subspace=True,
                                         energies=(1,),
                                         omega_g=np.cos(np.pi / 4),
                                         omega_r=np.sin(np.pi / 4))
    energy_shift = hamiltonian.HamiltonianEnergyShift(IS_subspace=True, graph=graph,
                                                      energies=(2.5,), index=0)
    dissipation = EffectiveOperatorDissipation(graph=graph, omega_r=1, omega_g=1,
                                               rates=(1,))
    if mode == 'hybrid':
        schedule = schedule_hybrid
    elif mode == 'adiabatic':
        schedule = schedule_adiabatic
    else:
        schedule = schedule_reit
    if mode != 'reit':
        eq = SchrodingerEquation(hamiltonians=[laser, energy_shift])
    else:
        eq = SchrodingerEquation(hamiltonians=[laser])

    def compute_rate():
        # Construct the first order transition matrix
        energies, states = eq.eig(k='all')
        states = states.T
        rates = np.zeros(energies.shape[0] ** 2)
        nh_rates =  np.zeros(energies.shape[0] ** 2)
        for op in dissipation.jump_operators:
            rates = rates + (np.abs(states.conj().T @ op @ states) ** 2).flatten()
            nh_rates = nh_rates + (states.conj().T @ op.conj().T @ op @ states).flatten()
        # Select the relevant rates from 'good' to 'bad'
        rates = np.reshape(rates.real, (graph.num_independent_sets, graph.num_independent_sets))
        nh_rates = np.reshape(nh_rates.real, (graph.num_independent_sets, graph.num_independent_sets))
        if visualize:
            plt.imshow(rates)
            plt.colorbar()
            plt.show()
            plt.clf()
            plt.scatter(range(rates.shape[0]), (np.diag(nh_rates)/graph.n-2*np.diag(nh_rates)**2/graph.n**2), color='black')
            plt.scatter(range(rates.shape[0]),np.diag(rates)/graph.n, label = r'$\frac{1}{n}\sum_u|\langle j |c_u |j\rangle|^2$')
            plt.scatter(range(nh_rates.shape[0]),np.diag(nh_rates)/graph.n, label =r'$\frac{1}{n}\sum_u\langle j |c_u^\dagger c_u |j\rangle$')
            plt.scatter(range(nh_rates.shape[0]),(np.diag(nh_rates)-np.diag(rates))/graph.n, label = r'$\frac{1}{n}\sum_u\left(\langle j |c_u^\dagger c_u |j\rangle-|\langle j |c_u |j\rangle|^2\right)$')
            plt.scatter(range(nh_rates.shape[0]),np.diag(rates)/(np.diag(nh_rates)), label = r'$\sum_u\langle j |c_u |j\rangle|^2/\sum_u\langle j |c_u^\dagger c_u |j\rangle|$')
            plt.xlabel(r'$|j\rangle$')
            plt.legend()
            plt.show()
        rates = rates[:, 0].flatten()
        return rates, energies
    schedule(time, 1)
    rates, energies = compute_rate()
    return rates, energies

#rate_vs_eigenenergy(.4, graph=line_graph(n=15), mode='reit', visualize=True)

def compute_rate_from_spectrum(energies, bins=20):
    assert bins % 2 == 0
    energy_max, energy_min = (np.max(energies), np.min(energies))
    spacing = (energy_max-energy_min)/bins
    density_of_states = np.zeros(bins)
    energy_function = np.zeros(bins)

    for i in range(bins):
        in_bin = energies[(energies > energy_min + i*spacing) * (energies <= energy_min + (i+1)*spacing)]
        if len(in_bin) == 0:
            print('Warning: empty slice')
        else:
            density_of_states[i] = len(in_bin)
            energy_function[i] = np.mean(in_bin)

    matrix_elements = 1/density_of_states[0:bins//2]
    energy_function = np.reshape(energy_function, (len(energy_function)//2, 2), order='C')
    energy_function = np.mean(energy_function, axis=1)
    return matrix_elements, energy_function

def cutoff(time, graph=line_graph(n=2), mode='hybrid', visualize=False, threshold = .99):
    # Compute the eigenenergy where 99% of the total rate has been reached
    rates, energies = rate_vs_eigenenergy(time, graph=graph, mode=mode)
    energies = energies - energies[0]
    cumulative_rates = np.cumsum(rates)
    total_rate = np.max(cumulative_rates)
    cutoff_rates = cumulative_rates[np.argwhere(cumulative_rates < threshold*total_rate)].flatten()
    num_states = len(cutoff_rates)
    fraction_rates = num_states/graph.num_independent_sets
    print(n, num_states, fraction_rates)
    cmap = plt.get_cmap("tab20")

    if visualize:
        if graph.n % 2 == 0:
            plt.scatter(energies[int(graph.n/2)+1:], cumulative_rates[int(graph.n/2)+1:], label=str(graph.n)+' atoms', color=cmap(graph.n-5), s=5)
            plt.scatter(energies[0:int(graph.n/2)+1], cumulative_rates[0:int(graph.n/2)+1], marker='^', color=cmap(graph.n-5))
        else:
            plt.scatter(energies[1:], cumulative_rates[1:], label=str(graph.n)+' atoms', color=cmap(graph.n-5), s=5)
            plt.scatter(energies[0], cumulative_rates[0], marker='^', color=cmap(graph.n-5))

        plt.vlines(energies[num_states-1], 0, np.max(cumulative_rates), colors='k', linestyles=':')

def scaling_line(time, graph=line_graph(n=2), mode='hybrid', visualize=False, threshold = .99):
    # Compute the eigenenergy where 99% of the total rate has been reached
    rates, energies = rate_vs_eigenenergy(time, graph=graph, mode=mode)
    energies = energies - energies[0]
    print(rates[0])
    cumulative_rates = np.cumsum(rates)
    total_rate = np.max(cumulative_rates)
    cutoff_rates = cumulative_rates[np.argwhere(cumulative_rates < threshold*total_rate)].flatten()
    num_states = len(cutoff_rates)
    cmap = plt.get_cmap("tab20")

    if visualize:
        if graph.n % 2 == 0:
            plt.scatter(energies[int(graph.n/2)+1:num_states], cumulative_rates[int(graph.n/2)+1:num_states], label=str(graph.n)+' atoms', color=cmap(graph.n-5), s=5)
            plt.scatter(energies[0:int(graph.n/2)+1], cumulative_rates[0:int(graph.n/2)+1], marker='^', color=cmap(graph.n-5))
        else:
            plt.scatter(energies[1:num_states], cumulative_rates[1:num_states], label=str(graph.n)+' atoms', color=cmap(graph.n-5), s=5)
            plt.scatter(energies[0], cumulative_rates[0], marker='^', color=cmap(graph.n-5))

def scaling(time, graph=line_graph(n=2), mode='hybrid', visualize=False, threshold = .99):
    # Compute the eigenenergy where 99% of the total rate has been reached
    rates, energies = rate_vs_eigenenergy(time, graph=graph, mode=mode)
    energies = energies - energies[0]
    print(rates[0])
    cumulative_rates = np.cumsum(rates)
    total_rate = np.max(cumulative_rates)
    cutoff_rates = cumulative_rates[np.argwhere(cumulative_rates < threshold*total_rate)].flatten()
    num_states = len(cutoff_rates)
    cmap = plt.get_cmap("tab20")

    if visualize:
        plt.scatter(energies, cumulative_rates, color=cmap(graph.n-5), s=5)

from qsim.graph_algorithms.graph import unit_disk_graph
graph = nx.erdos_renyi_graph(20, .4)
graph = Graph(graph)

#arr = np.reshape(np.random.binomial(1, [.65]*20), (4, 5))
#graph = unit_disk_graph(arr)
#nx.draw(graph)
#plt.show()
rates, energies = rate_vs_eigenenergy(.5, graph=graph, mode='reit', visualize=True)

seen_n = []
def full_scaling(time, graph=line_graph(n=2), mode='hybrid', visualize=False,  bins=20, threshold=.99):
    # Compute the eigenenergy where 99% of the total rate has been reached
    rates, energies = rate_vs_eigenenergy(time, graph=graph, mode=mode)
    energies = energies - energies[0]
    energy_max, energy_min = (np.max(energies), np.min(energies))
    spacing = (energy_max - energy_min) / bins
    binned_rates = np.zeros(bins)
    binned_energies = np.zeros(bins)
    empty = []
    for i in range(bins):
        in_bin = energies[(energies > energy_min + i * spacing) * (energies <= energy_min + (i + 1) * spacing)]
        if len(in_bin) == 0:
            empty.append(i)
        else:
            binned_rates[i] = np.sum(rates[(energies > energy_min + i * spacing) * (energies <= energy_min + (i + 1) * spacing)])
            binned_energies[i] = np.mean(in_bin)

    for i in np.flip(empty):
        binned_energies = np.delete(binned_energies, i)
        binned_rates = np.delete(binned_rates, i)

    cmap = plt.get_cmap("tab20")
    """cumulative_rates = np.cumsum(binned_rates)
    total_rate = np.max(cumulative_rates)
    cutoff_rates = cumulative_rates[np.argwhere(cumulative_rates < threshold * total_rate)].flatten()
    num_states = len(cutoff_rates)"""
    if visualize:
        if False:#graph.n not in seen_n:
            seen_n.append(graph.n)
            plt.scatter(binned_energies, binned_rates/graph.n, label=str(graph.n)+' atoms', color=cmap(graph.n-6), s=10)
        else:
            plt.scatter(binned_energies, binned_rates/graph.n, color='purple', s=10)#cmap(graph.n-6)

"""cmap = plt.get_cmap("tab20")

ns = np.flip(np.arange(9, 18))
rates = [2.084603970778938, 1.9580976047147012, 1.8324084100867386, 1.7054004924363282, 1.5805061615414315,
         1.452245256773329, 1.3292903489681183, 1.198035727816749, 1.0795279857577094]
plt.plot(ns, rates, c='k', zorder=1)

for i in range(len(rates)):
    plt.scatter(ns[i], rates[i], color=cmap(ns[i]- 5), zorder=2)
plt.xlabel(r'$n$')
plt.ylabel(r"$r_{0\rightarrow 0}$ at $t/T = 1/2$")
#plt.legend()
#plt.semilogy()
plt.show()"""

def reduced_density_matrix(time, graph=line_graph(3), mode='hybrid'):
    def schedule_hybrid(t, tf):
        phi = (tf - t) / tf * np.pi / 2
        energy_shift.energies = (np.sin(2 * ((tf - t) / tf - 1 / 2) * np.pi),)
        laser.omega_g = np.cos(phi)
        laser.omega_r = np.sin(phi)

    def schedule_reit(t, tf):
        phi = (tf - t) / tf * np.pi / 2
        laser.energies = (np.abs(np.cos(phi)*np.sin(phi)),)
        energy_shift_g.energies = (np.cos(phi)**2,)
        energy_shift_r.energies = (np.sin(phi)**2,)

    def schedule_adiabatic(t, tf):
        phi = (tf - t) / tf * np.pi / 2
        energy_shift.energies = (2 * ((tf - t) / tf - 1 / 2),)
        laser.omega_g = np.sqrt(np.abs(np.sin(phi) * np.cos(phi)))
        laser.omega_r = np.sqrt(np.abs(np.sin(phi) * np.cos(phi)))\

    laser = hamiltonian.HamiltonianDriver(graph=graph, IS_subspace=False, energies=(1/2,))
    energy_shift_g = hamiltonian.HamiltonianEnergyShift(IS_subspace=False, graph=graph,
                                                      energies=(1/2,), index=1)
    energy_shift_r = hamiltonian.HamiltonianEnergyShift(IS_subspace=False, graph=graph,
                                                      energies=(1/2,), index=0)
    blockade = hamiltonian.HamiltonianMIS(graph, energies=(0, -50), IS_subspace=False)
    schedule_reit(time, 1)
    if mode == 'hybrid':
        schedule = schedule_hybrid
    elif mode == 'adiabatic':
        schedule = schedule_adiabatic
    else:
        schedule = schedule_reit
    if mode != 'reit':
        eq = SchrodingerEquation(hamiltonians=[laser, energy_shift_g, energy_shift_r, blockade])
    else:
        eq = SchrodingerEquation(hamiltonians=[laser, blockade])
    cmap = plt.get_cmap("tab20")
    def compute_reduced_density_matrix():
        # Construct the first order transition matrix
        energy, state = eq.ground_state()
        if time >.98:
            print(np.argwhere(np.abs(state)>.5))
        rho1 = State(tools.outer_product(state, state), graph=graph)
        #print(energy)

        #plt.imshow(np.log(np.abs(rho.real)))

        #plt.show()
        omega_g = np.sin(time * np.pi / 2)
        omega_r = np.cos(time * np.pi / 2)
        for index in range(graph.n):
            print(index)
            ind = list(range(graph.n))
            ind.remove(index)
            rho = tools.trace(rho1, ind=ind)

            dark = np.array([[-omega_g], [omega_r]])
            bright = np.array([[omega_r], [omega_g]])
            ground = np.array([[0], [1]])
            rho_bd = np.zeros((2 ,2), dtype=np.complex128)
            rho_bd[1,1] = np.trace(rho @ tools.outer_product(bright, bright))
            rho_bd[0, 1] = np.trace(rho @ tools.outer_product(bright, dark))
            rho_bd[1, 0] = np.trace(rho @ tools.outer_product(dark, bright))
            rho_bd[0, 0] = np.trace(rho @ tools.outer_product(dark, dark))
            plt.scatter(time, np.trace(tools.outer_product(bright, bright)@rho)-np.abs(np.trace(tools.outer_product(ground, bright)@rho))**2, color=cmap(index))
            if l == 0:
                plt.scatter(time, np.trace(tools.outer_product(bright, bright) @ rho) - np.abs(
                    np.trace(tools.outer_product(ground, bright) @ rho)) ** 2, color=cmap(index), label=graph.n-index)

            if rho_bd[1,1]<= 1/(1+omega_g**2/omega_r**2):
                if rho_bd[1,1]>=.1:
                    print('first case', rho)
                plt.scatter(time, rho_bd[1,1], color=cmap(index), marker='p')

            else:
                upper_bound = omega_g**2*rho_bd[1,1]-(omega_g**2-omega_r**2)*rho_bd[1,1]**2+2*omega_g*omega_r*rho_bd[1,1]*np.sqrt(rho_bd[1,1]*(1-rho_bd[1,1]))
                if upper_bound>.1:
                    print('second case', time, rho, upper_bound, omega_g**2*rho_bd[1,1]-(omega_g**2-omega_r**2)*rho_bd[1,1]**2- 2*omega_g*omega_r*rho_bd[1,1]*np.sqrt(rho_bd[1,1]*(1-rho_bd[1,1])))
                    print(np.array([[rho_bd[0,0], -np.sqrt(rho_bd[1,1]*(1-rho_bd[1,1]))], [-np.sqrt(rho_bd[1,1]*(1-rho_bd[1,1])), rho_bd[1,1]]]), rho_bd)
                    print(rho_bd[1,1]-rho_bd[1,1]**2*omega_g**2-omega_r**2*rho_bd[1,0]**2-2*omega_g*omega_r*rho_bd[1,1]*rho_bd[1,0],np.trace(tools.outer_product(bright, bright)@rho)-np.abs(np.trace(tools.outer_product(ground, bright)@rho))**2)
                plt.scatter(time, upper_bound, color=cmap(index), marker='*')
    #schedule(time, 1)
    return compute_reduced_density_matrix()

def plot_gd_overlap():
    graph = nx.Graph()
    graph.add_weighted_edges_from([(0, 1, 1), (0, 4, 1), (1, 6, 1),(0, 7, 1), (1, 3, 1), (0, 2, 1), (2, 3, 1), (2, 4, 1), (2, 6, 1), (2, 7, 1), (3, 5, 1), (3, 6, 1), (3, 7, 1), (4, 5, 1), (4, 7, 1), (5, 6, 1), (5, 7, 1)])
    nx.draw(graph, with_labels=True)
    plt.show()
    graph=Graph(graph)
    print(graph.independent_sets[0], graph.degeneracy)
    def schedule_reit(t, tf):
        phi = (tf - t) / tf * np.pi / 2
        laser.energies = (np.abs(np.cos(phi) * np.sin(phi)),)
        energy_shift_g.energies = (np.cos(phi) ** 2,)
        energy_shift_r.energies = (np.sin(phi) ** 2,)


    laser = hamiltonian.HamiltonianDriver(graph=graph, IS_subspace=False, energies=(0,))

    energy_shift_g = hamiltonian.HamiltonianEnergyShift(IS_subspace=False, graph=graph,
                                                        energies=(0,), index=1)
    energy_shift_r = hamiltonian.HamiltonianEnergyShift(IS_subspace=False, graph=graph,
                                                        energies=(0,), index=0)
    blockade = hamiltonian.HamiltonianMIS(graph, energies=(0, -10), IS_subspace=False)
    eq = SchrodingerEquation(hamiltonians=[laser, energy_shift_g, energy_shift_r, blockade])

    cmap = plt.get_cmap("tab20")

    for time in np.linspace(.00, .99, 100):
        # Construct the first order transition matrix
        schedule_reit(time, 1)
        energy, state = eq.ground_state()
        omega_g = np.sin(time * np.pi / 2)
        omega_r = np.cos(time * np.pi / 2)
        dark = np.array([[-omega_g], [omega_r]]).flatten()
        #print(dark)
        ground = np.array([[0], [1]]).flatten()
        #gd =tools.tensor_product([ground, ground, dark, ground, ground, dark, dark, ground])
        #print(state)
        gd =tools.tensor_product([ground, dark, dark, ground, ground, dark, ground, ground])
        print(np.argwhere(gd>.5))

        #print(np.abs(state.T.conj()@gd))
        plt.scatter(time, np.linalg.norm(state.T.conj()@np.array([gd]).T)**2, color='blue')

plot_gd_overlap()
plt.xlabel(r'$t/T$')
plt.ylabel(r'ground state overlap with MIS in ground dark basis')

plt.show()
degeneracy = 0
while degeneracy != 1:
    graph = nx.erdos_renyi_graph(8, .5)
    #nx.draw(graph)
    #plt.show()
    graph1=Graph(graph)
    degeneracy = graph1.degeneracy
nx.draw(graph, with_labels=True)
plt.show()
graph=Graph(graph)
print(graph.independent_sets[0])
#graph=line_graph(3)
l = 0

for time in np.linspace(.01, .99, 100):
    reduced_density_matrix(time, graph=graph)
    l+=1
plt.legend()
plt.show()
def schedule_adiabatic(t, tf):
    phi = (tf - t) / tf * np.pi / 2
    energy_shift.energies = (2 * ((tf - t) / tf - 1 / 2),)
    laser.omega_g = np.sqrt(np.abs(np.sin(phi) * np.cos(phi)))
    laser.omega_r = np.sqrt(np.abs(np.sin(phi) * np.cos(phi)))
    dissipation.omega_g = np.sqrt(np.abs(np.sin(phi) * np.cos(phi)))
    dissipation.omega_r = np.sqrt(np.abs(np.sin(phi) * np.cos(phi)))


laser = EffectiveOperatorHamiltonian(graph=graph, IS_subspace=True,
                                     energies=(1,),
                                     omega_g=np.cos(np.pi / 4),
                                     omega_r=np.sin(np.pi / 4))
energy_shift = hamiltonian.HamiltonianEnergyShift(IS_subspace=True, graph=graph,
                                                  energies=(2.5,), index=0)
dissipation = EffectiveOperatorDissipation(graph=graph, omega_r=1, omega_g=1,
                                           rates=(1,))

graph = nx.erdos_renyi_graph(30, .13)
nx.draw(graph)
plt.show()
graph = Graph(graph)
print(graph.num_independent_sets)
eq = SchrodingerEquation(hamiltonians=[laser])
schedule_adiabatic(.5, 1)
energy, state = eq.ground_state()
plt.scatter(range(len(state)), state.T[0])
plt.xlabel('index')
plt.ylabel('matrix element')
plt.show()
dark = np.array([[1/np.sqrt(2)], [-1/np.sqrt(2)]])
bright = np.array([[1/np.sqrt(2)], [1/np.sqrt(2)]])
ground = np.array([[0], [1]])
"""gs = np.zeros((5, 1), dtype=np.complex128)
gs[0,0] = (np.vdot(state, np.delete(tools.tensor_product([dark, ground, dark]), [0, 1, 4])))
gs[1,0] = (np.vdot(state, np.delete(tools.tensor_product([dark, ground, ground]), [0, 1, 4])))
gs[2,0] = (np.vdot(state, np.delete(tools.tensor_product([ground, dark, ground]), [0, 1, 4])))
gs[3,0] = (np.vdot(state, np.delete(tools.tensor_product([ground, ground, dark]), [0, 1, 4])))
gs[4,0] = (np.vdot(state, np.delete(tools.tensor_product([ground, ground, ground]), [0, 1, 4])))
print(gs.real)
print(state.real)"""
"""
6 10 0.47619047619047616
7 12 0.35294117647058826
8 15 0.2727272727272727
9 19 0.21348314606741572
10 23 0.1597222222222222
11 28 0.12017167381974249
12 32 0.08488063660477453
13 39 0.06393442622950819
14 44 0.044579533941236066
15 50 0.031308703819661866
16 57 0.022058823529411766
17 66 0.015785697201626404
num_states = [10, 12, 15, 19, 23, 28, 32, 39, 44, 50, 57, 66]
"""

"""ns = np.arange(6, 18, 1)
num_states = [10, 12, 15, 19, 23, 28, 32, 39, 44, 50, 57, 66]
plt.scatter(ns, num_states)
print(np.polyfit(np.log(ns), np.log(num_states), deg=1))
plt.loglog()
plt.show()"""
from qsim.graph_algorithms.graph import unit_disk_graph
"""for i in range(100):
    print(i)
    #arr = np.reshape(np.random.binomial(1, [.65]*25), (5, 5))
    arr = np.zeros(25)
    arr[0:19] = 1
    np.random.shuffle(arr)
    arr = np.reshape(arr, (5, 5))
    print(arr)
    graph = unit_disk_graph(arr)
    full_scaling(.5, graph=graph, mode='reit', visualize=True, bins=40)
plt.semilogy()
#plt.legend()
plt.xlabel(r'$E-E_0$')
plt.ylabel(r"$r_{0\rightarrow E}$ at $t/T = 1/2$")
plt.show()"""

'''graph = line_graph(11)


for n in []:
    print(n)
    graph = nx.erdos_renyi_graph(n, .3)#line_graph(n)
    nx.draw(graph)
    plt.show()
    graph = Graph(graph)
    scaling(.5, graph=graph, mode='reit', visualize=True)
plt.xlabel(r'$E-E_0$')
plt.ylabel(r"$r_{0\rightarrow E}$ at $t/T = 1/2$")
plt.legend()'''
#plt.semilogy()
#plt.show()

    #rates, energies = rate_vs_eigenenergy(.4, graph=graph, mode='reit', visualize=True)
    #matrix_elements, energy_function = compute_rate_from_spectrum(energies, bins=10)
    #plt.scatter(energies, rates, label='reit')

#plt.scatter(energy_function, matrix_elements)