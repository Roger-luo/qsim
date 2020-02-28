import networkx as nx
from . import plot
from qsim.noise import noise_models
from qsim.qaoa import simulate, variational_parameters
from qsim.state import JordanFarhiShor

# Construct a simple graph
G = nx.random_regular_graph(1, 2)
for e in G.edges:
    G[e[0]][e[1]]['weight'] = 1

# Uncomment to visualize graph
plot.draw_graph(G)

p = 2
sim_code = simulate.SimulateQAOA(G, p, 2, is_ket=False, code=JordanFarhiShor)

# Set the default variational operators
sim_code.variational_params = [variational_parameters.HamiltonianC(sim_code.C),
                               variational_parameters.HamiltonianB()]

sim_code.noise = [noise_models.PauliNoise((.025, 0, 0)), noise_models.PauliNoise((.025, 0, 0))]

sim_penalty = simulate.SimulateQAOA(G, p, 3, is_ket=False, code=JordanFarhiShor)

# Set the default variational parameters and noise
sim_penalty.variational_params = [variational_parameters.HamiltonianC(sim_penalty.C),
                                  variational_parameters.HamiltonianB(),
                                  variational_parameters.HamiltonianBookatzPenalty()]
sim_penalty.noise = [noise_models.PauliNoise((.025, 0, 0)), noise_models.PauliNoise((.025, 0, 0)),
                     noise_models.PauliNoise((.025, 0, 0))]

#sim_code.find_parameters_brute(n=15)
sim_penalty.find_parameters_brute(n=4)
