import unittest
from qsim.graph_algorithms import graph
import networkx as nx
from qsim.evolution import hamiltonian
from qsim.graph_algorithms.adiabatic import SimulateAdiabatic
import numpy as np
import matplotlib.pyplot as plt
from qsim.tools.tools import equal_superposition
from qsim.graph_algorithms.graph import Graph
from qsim.codes.quantum_state import State
from qsim.test.tools_test import sample_graph


def adiabatic_simulation(graph, show_graph=False, IS_subspace=True):
    if show_graph:
        nx.draw(graph)
        plt.show()
    # Generate the driving and Rydberg Hamiltonians
    laser = hamiltonian.HamiltonianDriver(IS_subspace=IS_subspace, graph=graph)
    detuning = hamiltonian.HamiltonianMIS(graph, IS_subspace=IS_subspace)
    rydberg_hamiltonian_cost = hamiltonian.HamiltonianMIS(graph, IS_subspace=IS_subspace)
    # Initialize adiabatic algorithm
    simulation = SimulateAdiabatic(graph, hamiltonian=[laser, detuning], cost_hamiltonian=rydberg_hamiltonian_cost,
                                   IS_subspace=IS_subspace)
    return simulation


class TestAdiabatic(unittest.TestCase):
    def test_trotterize(self):
        # Compare that the integrator adiabatic results match the trotterized results
        # First, compare the non-IS subspace results
        simulation = adiabatic_simulation(sample_graph(), IS_subspace=False)
        res_trotterize = simulation.performance_vs_total_time(np.arange(1, 5, 1), metric='optimum_overlap',
                                                   initial_state=State(equal_superposition(6)),
                                                   schedule=lambda t, tf: simulation.linear_schedule(t, tf,
                                                                                                     coefficients=[10,
                                                                                                                   10]),
                                                   plot=False, verbose=True, method='trotterize')
        res_RK45 = simulation.performance_vs_total_time(np.arange(1, 5, 1), metric='optimum_overlap',
                                                   initial_state=State(equal_superposition(6)),
                                                   schedule=lambda t, tf: simulation.linear_schedule(t, tf,
                                                                                                     coefficients=[10,
                                                                                                                   10]),
                                                   plot=False, verbose=True, method='RK45')
        # Now test in the IS subspace
        self.assertTrue(np.allclose(res_trotterize, res_RK45, atol=1e-2))
        simulation = adiabatic_simulation(sample_graph(), IS_subspace=True)
        res_trotterize = simulation.performance_vs_total_time(np.arange(1, 4, 1)*10, metric='optimum_overlap',
                                                              schedule=lambda t, tf: simulation.linear_schedule(t, tf,
                                                                                                                coefficients=[
                                                                                                                    10,
                                                                                                                    10]),
                                                              plot=False, verbose=True, method='trotterize')
        res_RK45 = simulation.performance_vs_total_time(np.arange(1, 4, 1)*10, metric='optimum_overlap',
                                                        schedule=lambda t, tf: simulation.linear_schedule(t, tf,
                                                                                                          coefficients=[
                                                                                                              10,
                                                                                                              10]),
                                                        plot=False, verbose=True, method='RK45')
        self.assertTrue(np.allclose(res_trotterize, res_RK45, atol=1e-2))


if __name__ == '__main__':
    unittest.main()
