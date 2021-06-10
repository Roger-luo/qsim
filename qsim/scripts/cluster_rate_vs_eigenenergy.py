import matplotlib.pyplot as plt
import numpy as np
import pickle
import dill

import scipy.sparse as sparse
from scipy.linalg import expm
from scipy.sparse.linalg import expm_multiply, eigsh

from qsim.codes import qubit
from qsim.codes.quantum_state import State
from qsim.evolution import lindblad_operators, hamiltonian
from qsim.graph_algorithms.graph import Graph
from qsim.graph_algorithms.graph import line_graph, degree_fails_graph
from qsim.lindblad_master_equation import LindbladMasterEquation
from qsim.schrodinger_equation import SchrodingerEquation
from qsim.graph_algorithms.adiabatic import SimulateAdiabatic
from qsim.tools import tools
from qsim.evolution.lindblad_operators import SpontaneousEmission
from matplotlib import rc


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
            if code is not qubit:
                IS, num_IS = graph.independent_sets_qudit(self.code)
            else:
                # We have already solved for this information
                IS, num_IS = graph.independent_sets, graph.num_independent_sets
            self.transition = (0, 1)
            self._hamiltonian_rr = np.zeros(num_IS)
            self._hamiltonian_gg = np.zeros(num_IS)
            for k in range(IS.shape[0]):
                self._hamiltonian_rr[k] = np.sum(IS[k] == self.transition[0])
                self._hamiltonian_gg[k] = np.sum(IS[k] == self.transition[1])
            diagonal = np.arange(num_IS)
            self._hamiltonian_gg = sparse.csc_matrix((self._hamiltonian_gg, (diagonal, diagonal)),
                                                     shape=(num_IS, num_IS))
            self._hamiltonian_rr = sparse.csc_matrix((self._hamiltonian_rr, (diagonal, diagonal)),
                                                     shape=(num_IS, num_IS))
            # For each IS, look at spin flips generated by the laser
            # Over-allocate space
            rows = np.zeros(graph.n * num_IS, dtype=int)
            columns = np.zeros(graph.n * num_IS, dtype=int)
            entries = np.zeros(graph.n * num_IS, dtype=int)
            num_terms = 0
            for j in range(graph.n):
                for i in range(num_IS):
                    if IS[i, j] == self.transition[0]:
                        # Flip spin at this location
                        # Get binary representation
                        temp = IS[i].copy()
                        temp[j] = self.transition[1]
                        where_matched = (np.argwhere(np.sum(np.abs(IS - temp), axis=1) == 0).flatten())
                        if len(where_matched) > 0:
                            # This is a valid spin flip
                            rows[num_terms] = where_matched[0]
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
            self._hamiltonian_cross_terms = sparse.csc_matrix((entries, (rows, columns)), shape=(num_IS, num_IS))
        else:
            # We are not in the IS subspace
            pass

    @property
    def hamiltonian(self):
        return self.energies[0] * (self.omega_g * self.omega_r * self._hamiltonian_cross_terms +
                                   self.omega_g ** 2 * self._hamiltonian_gg +
                                   self.omega_r ** 2 * self._hamiltonian_rr)

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
                IS, num_IS = graph.independent_sets_qudit(self.code)
            else:
                # We have already solved for this information
                IS, num_IS = graph.independent_sets, graph.num_independent_sets
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
                for i in range(num_IS):
                    if IS[i, j] == self.transition[0]:
                        # Flip spin at this location
                        # Get binary representation
                        temp = IS[i].copy()
                        temp[j] = self.transition[1]
                        where_matched = (np.argwhere(np.sum(np.abs(IS - temp), axis=1) == 0).flatten())
                        if len(where_matched) > 0:
                            # This is a valid spin flip
                            rows_rg[num_terms_rg] = where_matched[0]
                            columns_rg[num_terms_rg] = i
                            entries_rg[num_terms_rg] = 1
                            num_terms_rg += 1
                    elif IS[i, j] == self.transition[1]:
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


def plot_schedule():
    laser = EffectiveOperatorHamiltonian(graph=line_graph(1), IS_subspace=True,
                                         energies=(1,),
                                         omega_g=np.cos(np.pi / 4),
                                         omega_r=np.sin(np.pi / 4))
    energy_shift = hamiltonian.HamiltonianEnergyShift(IS_subspace=True, graph=line_graph(1),
                                                      energies=(2.5,), index=0)

    def schedule_exp_fixed_true_bright(t, tf):
        k = 50
        a = .95
        b = 3.1
        x = t / tf
        max_omega_g = 1 / np.sqrt(2)
        max_omega_r = 1 / np.sqrt(2)

        amplitude = max_omega_g * max_omega_r * (
                -1 / (1 + np.e ** (k * (x - a))) ** b - 1 / (1 + np.e ** (-k * (x - (tf - a)))) ** b + 1) / \
                    (-1 / ((1 + np.e ** (k * (1 / 2 - a))) ** b) - 1 / (
                            (1 + np.e ** (-k * (1 / 2 - (tf - a)))) ** b) + 1)
        # Now we need to figure out what the driver strengths should be for STIRAP

        ratio = max_omega_g / max_omega_r
        omega_g = np.sqrt(amplitude * ratio)
        omega_r = np.sqrt(amplitude / ratio)
        laser.omega_g = omega_g
        laser.omega_r = omega_r
        offset = -3 * 2 * (1 / 2 - t / tf)
        energy_shift.energies = (offset,)

    schedule = schedule_exp_fixed_true_bright
    num = 1000
    omega_gs = np.zeros(num)
    omega_rs = np.zeros(num)
    energy_shifts = np.zeros(num)
    i = 0
    times = np.linspace(0, 1, num)
    for t in times:
        schedule(t, 1)
        omega_gs[i] = laser.energies[0] * laser.omega_g
        omega_rs[i] = laser.energies[0] * laser.omega_r
        energy_shifts[i] = energy_shift.energies[0]
        i += 1
    plt.plot(times, omega_gs, label=r'$\Omega_g$')
    plt.plot(times, omega_rs, label=r'$\Omega_r$')
    plt.plot(times, energy_shifts, label=r'$\delta_r$')
    plt.legend()
    plt.show()


def leakage(graph, t):
    max_omega_r = 1
    max_omega_g = 1
    amplitude = np.sqrt(max_omega_r ** 2 + max_omega_g ** 2)
    max_omega_r /= amplitude
    max_omega_g /= amplitude
    k = 50
    a = .95
    b = 3.1

    def schedule_exp_fixed_true_bright(t, tf):
        x = t / tf
        amplitude = max_omega_g * max_omega_r * (
                -1 / (1 + np.e ** (k * (x - a))) ** b - 1 / (1 + np.e ** (-k * (x - (tf - a)))) ** b + 1) / \
                    (-1 / ((1 + np.e ** (k * (1 / 2 - a))) ** b) - 1 / (
                            (1 + np.e ** (-k * (1 / 2 - (tf - a)))) ** b) + 1)
        # Now we need to figure out what the driver strengths should be for STIRAP

        ratio = max_omega_g / max_omega_r
        omega_g = np.sqrt(amplitude * ratio)
        omega_r = np.sqrt(amplitude / ratio)

        laser.omega_g = omega_g
        laser.omega_r = omega_r
        offset = 3 * 2 * (1 / 2 - t / tf)
        energy_shift.energies = (offset,)
        dissipation.omega_g = -omega_g
        dissipation.omega_r = omega_r

    def schedule_exp_fixed_true_dark(t, tf):
        x = t / tf
        amplitude = max_omega_g * max_omega_r * (
                -1 / (1 + np.e ** (k * (x - a))) ** b - 1 / (1 + np.e ** (-k * (x - (tf - a)))) ** b + 1) / \
                    (-1 / ((1 + np.e ** (k * (1 / 2 - a))) ** b) - 1 / (
                            (1 + np.e ** (-k * (1 / 2 - (tf - a)))) ** b) + 1)

        # Now, choose the opposite of the STIRAP sequence
        ratio = max_omega_g / max_omega_r
        omega_g = np.sqrt(amplitude * ratio)
        omega_r = np.sqrt(amplitude / ratio)
        offset = 3 * 2 * (1 / 2 - t / tf)#max_omega_g * max_omega_r * np.cos(x * np.pi) - (omega_r ** 2 - omega_g ** 2)
        energy_shift.energies = (offset,)

        laser.omega_g = omega_g
        laser.omega_r = omega_r
        dissipation.omega_g = omega_g
        dissipation.omega_r = omega_r

    def schedule_exp_fixed(t, tf=1):
        x = t / tf * np.pi / 2
        amplitude = np.abs(np.cos(x) * np.sin(x))
        # Now we need to figure out what the driver strengths should be for STIRAP
        omega_g = np.sin(x)
        omega_r = np.cos(x)
        offset = omega_r ** 2 - omega_g ** 2
        # Now, choose the opposite of the STIRAP sequence
        energy_shift.energies = (offset,)
        laser.omega_g = np.sqrt(amplitude)
        laser.omega_r = np.sqrt(amplitude)
        dissipation.omega_g = np.sqrt(amplitude)
        dissipation.omega_r = np.sqrt(amplitude)

    laser = EffectiveOperatorHamiltonian(graph=graph, IS_subspace=True,
                                         energies=(1,), omega_g=1, omega_r=1)
    #laser = dill.load(open('laser.pickle', 'rb'))
    #dill.dump(laser, open('laser.pickle', 'wb'))
    #laser = dill.load(open('laser.pickle', 'rb'))
    energy_shift = hamiltonian.HamiltonianEnergyShift(IS_subspace=True, graph=graph,
                                                      energies=(2.5,), index=0)
    dissipation = EffectiveOperatorDissipation(graph=graph, omega_r=1, omega_g=1,
                                               rates=(1,))
    #dill.dump(dissipation, open('dissipation.pickle', 'wb'))
    #dissipation = dill.load(open('dissipation.pickle', 'rb'))

    def k_alpha_rate():
        # Construct the first order transition matrix
        eigvals, eigvecs = np.linalg.eigh((laser.hamiltonian + energy_shift.hamiltonian).todense())
        eigvecs = np.array(eigvecs)
        eigvals = np.array(eigvals)
        rates = np.zeros(graph.num_independent_sets)
        shape = eigvals.shape[0]
        for op in dissipation.jump_operators:
            jump_rates = np.zeros((shape, shape))
            jump_rates = jump_rates + (np.abs(eigvecs.T @ op @ eigvecs) ** 2)
            rates = rates + jump_rates[:, 0].flatten().real
        return eigvals, rates

    schedule_exp_fixed_true_dark(t, 1)
    energy, rate = k_alpha_rate()
    print(repr(list(energy)))
    print()
    print(repr(rate.tolist()))
    return energy, rate

def low_energy_leakage(graph, t):
    max_omega_r = 1
    max_omega_g = 1
    amplitude = np.sqrt(max_omega_r ** 2 + max_omega_g ** 2)
    max_omega_r /= amplitude
    max_omega_g /= amplitude
    k = 50
    a = .95
    b = 3.1

    def schedule_exp_fixed_true_bright(t, tf):
        x = t / tf
        amplitude = max_omega_g * max_omega_r * (
                -1 / (1 + np.e ** (k * (x - a))) ** b - 1 / (1 + np.e ** (-k * (x - (tf - a)))) ** b + 1) / \
                    (-1 / ((1 + np.e ** (k * (1 / 2 - a))) ** b) - 1 / (
                            (1 + np.e ** (-k * (1 / 2 - (tf - a)))) ** b) + 1)
        # Now we need to figure out what the driver strengths should be for STIRAP

        ratio = max_omega_g / max_omega_r
        omega_g = np.sqrt(amplitude * ratio)
        omega_r = np.sqrt(amplitude / ratio)

        laser.omega_g = omega_g
        laser.omega_r = omega_r
        offset = 3 * 2 * (1 / 2 - t / tf)
        energy_shift.energies = (offset,)
        dissipation.omega_g = -omega_g
        dissipation.omega_r = omega_r

    def schedule_exp_fixed_true_dark(t, tf):
        x = t / tf
        amplitude = max_omega_g * max_omega_r * (
                -1 / (1 + np.e ** (k * (x - a))) ** b - 1 / (1 + np.e ** (-k * (x - (tf - a)))) ** b + 1) / \
                    (-1 / ((1 + np.e ** (k * (1 / 2 - a))) ** b) - 1 / (
                            (1 + np.e ** (-k * (1 / 2 - (tf - a)))) ** b) + 1)

        # Now, choose the opposite of the STIRAP sequence
        ratio = max_omega_g / max_omega_r
        omega_g = np.sqrt(amplitude * ratio)
        omega_r = np.sqrt(amplitude / ratio)
        offset = 2 * (1 / 2 - t / tf)#max_omega_g * max_omega_r * np.cos(x * np.pi) - (omega_r ** 2 - omega_g ** 2)
        energy_shift.energies = (offset,)

        laser.omega_g = omega_g
        laser.omega_r = omega_r
        dissipation.omega_g = omega_g
        dissipation.omega_r = omega_r

    def schedule_exp_fixed(t, tf=1):
        x = t / tf * np.pi / 2
        amplitude = np.abs(np.cos(x) * np.sin(x))
        # Now we need to figure out what the driver strengths should be for STIRAP
        omega_g = np.sin(x)
        omega_r = np.cos(x)
        offset = omega_r ** 2 - omega_g ** 2
        # Now, choose the opposite of the STIRAP sequence
        energy_shift.energies = (offset,)
        laser.omega_g = np.sqrt(amplitude)
        laser.omega_r = np.sqrt(amplitude)
        dissipation.omega_g = np.sqrt(amplitude)
        dissipation.omega_r = np.sqrt(amplitude)

    laser = EffectiveOperatorHamiltonian(graph=graph, IS_subspace=True,
                                         energies=(1,), omega_g=1, omega_r=1)
    #laser = dill.load(open('laser.pickle', 'rb'))
    #dill.dump(laser, open('laser.pickle', 'wb'))
    #laser = dill.load(open('laser.pickle', 'rb'))
    energy_shift = hamiltonian.HamiltonianEnergyShift(IS_subspace=True, graph=graph,
                                                      energies=(2.5,), index=0)
    dissipation = EffectiveOperatorDissipation(graph=graph, omega_r=1, omega_g=1,
                                               rates=(1,))
    #dill.dump(dissipation, open('dissipation.pickle', 'wb'))
    #dissipation = dill.load(open('dissipation.pickle', 'rb'))

    def k_alpha_rate():
        # Construct the first order transition matrix
        eigvals, eigvecs = eigsh(laser.hamiltonian + energy_shift.hamiltonian, k=100, which='SA')
        return eigvals

    schedule_exp_fixed_true_dark(t, 1)
    energy = k_alpha_rate()
    #print(repr(list(energy)))
    #print()
    return energy


"""from qsim.graph_algorithms.graph import unit_disk_grid_graph, unit_disk_graph
large = True
while large:
    n = 40
    rho = 7
    arr = np.random.uniform(0, np.sqrt(n / rho), size=2 * n)
    arr = np.reshape(arr, (-1, 2))
    graph = unit_disk_graph(arr, visualize=False)
    print(graph.num_independent_sets, graph.mis_size, graph.degeneracy)
    if graph.num_independent_sets < 15000 and graph.degeneracy == 1:
        large=False"""
#pickle.dump(graph, open('graph_nondegenerate.pickle', 'wb'))
#import networkx as nx
#nx.draw(graph.graph)
#plt.show()
#print('done bitches')
#import time
#t0 = time.time()
from matplotlib import rc
rc('text', usetex=True)
rc('font', **{'family': 'serif'})
times = np.linspace(.1, .95, 100)
graph = pickle.load(open('graph_nondegenerate.pickle', 'rb'))
#graph = line_graph(15)
print(graph.num_independent_sets)
num = 100
energies = np.zeros((len(times),num))
for index in range(len(times)):
    print(index)
    energy = low_energy_leakage(graph, times[index])
    energies[index, ...] = energy
energies = energies.T - energies[:,0].flatten()
energies = energies.T
for index in range(num):
    if index == 0:
        plt.plot(times, energies[..., index], color = 'red')
    else:
        plt.plot(times, energies[..., index], color='grey', linewidth=1)
plt.xlabel(r'Time ($t/T$)')
plt.ylabel(r'Eigenenergy ($E_j-E_0$)')
plt.show()
#energy, rate = low_energy_leakage(line_graph(2), .6)
#print((time.time()-t0)/60)
#graph = pickle.load(open('graph.pickle', 'rb'))
#print(graph.num_independent_sets)
#low_energy_leakage(graph, .5)
#print(graph.num_independent_sets, graph.n)
"""arr = np.reshape(np.random.binomial(1, [.8]*36), (6, 6))
print(repr(arr), np.sum(arr))
graph = pickle.load(open('graph.pickle', 'rb'))
print(graph.num_independent_sets, graph.n)"""
# print(graph)
# pickle.dump(graph, open('graph.pickle', 'wb'))
#index = int(sys.argv[1])
if __name__ == "__main__":
    import sys

    index = int(sys.argv[1])
    times = np.linspace(.1, .95, 200)
    #pickle.dump(graph, open('graph.pickle', 'wb'))
    graph = pickle.load(open('graph_nondegenerate.pickle', 'rb'))
    low_energy_leakage(graph, times[index])
