import matplotlib.pyplot as plt
import numpy as np
import scipy.optimize
import pickle
from matplotlib.collections import LineCollection
from matplotlib import rc
rc('text', usetex=True)
rc('font', **{'family': 'serif'})
times = np.linspace(.1, .95, 200)
graph = pickle.load(open('graph.pickle', 'rb'))
energies = np.zeros((len(times), graph.num_independent_sets))
rates = np.zeros((len(times), graph.num_independent_sets))
for i in range(len(times)):
    file = open('./energies_and_rates_ud/times_'+str(i)+'.out', 'r')
    energy, trash, rate = file.readlines()
    energy = energy.replace(',', '')
    energy = energy[1:]
    energy = energy.replace(']', '')
    energy = np.array(energy.split(), dtype=float)
    rate = rate.replace(',', '')
    rate = rate[1:]
    rate = rate.replace(']', '')
    rate = np.array(rate.split(), dtype=float)
    if i == 0:
        print(rate)
        print(rate[0])
        print(np.sum(rate))
    rates[i, :] = rate
    energies[i, :] = energy
energies = energies.T - energies[:,0].flatten()
energies = energies.T
rates = np.log10(rates/graph.n)
print(energies.shape)
times = times[20:-20]
energies = energies[20:-20, ...]
rates = rates[20:-20, ...]
#mask = energies<7
#rates = rates*mask
fig, ax = plt.subplots()
print(np.min(rates))
norm = plt.Normalize(-10, np.max(rates))
for i in range(graph.num_independent_sets):
    print(i)
    points = np.array([times, energies[:, i]]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    lc = LineCollection(segments, cmap='coolwarm', norm=norm)
    # Set the values used for colormapping
    lc.set_array(rates[:-1, i])
    lc.set_linewidth(1)
    line = ax.add_collection(lc)

cbar = fig.colorbar(line, ax=ax)
cbar.ax.set_ylabel(r'$\log_{10}(\rm{rate\ into\ } |j\rangle)$')
ax.set_xlim(times[0],times[-1])
ax.set_xlabel(r'Time ($t/T$)')
ax.set_ylabel(r'Eigenenergy ($E_j-E_0$)')
ax.set_ylim(-1, 12.5)
fig.tight_layout()
plt.show()























fidelities_ss_hybrid = [0.9892727714174617, 0.9852232305797289,  0.9819290366560707, 0.9789444330906605,.9761063176477378, 0.9733356232127055, 0.9705883207000972, 0.9678379039515611,
              0.9650677180756911, 0.9622671231421603, .9594293851286988, .9565504298978581, .9565504298978581, .9536280637067762]
fidelities_hybrid_3 = [0.79777504, 0.85580079, 0.88522155, 0.90294435, 0.91477952, 0.92324049,
              0.93029268,
              0.93659344, 0.9416885, 0.94589282, 0.94942109, 0.95242408, 0.95501089, 0.95726238, 0.95923972,
              0.96099009, 0.96255043, 0.96395007, 0.96521268, 0.96635734, 0.96740167, 0.96835506, 0.96923035,
              0.97003676, 0.9707821, 0.97147304, 0.97211536, 0.972714, 0.97327327, 0.97379692, 0.97428826,
              0.97475018, .97518526, 0.97559575, 0.9760258, 0.97650623, 0.97696201, 0.977395, .97780686,
              0.97819911,  0.97857311]
extra = [0.99065325, 0.99056883, 0.99048272, 0.99039485, 0.99030519,
       0.99021366, 0.99012021, 0.99002478, 0.9899273 , 0.98982771,
       0.98972595, 0.98962193, 0.98951558, 0.98940683, 0.98929559,
       0.98918177, 0.98906528, 0.98894603, 0.98882393, 0.98869885,
       0.9885707 , 0.98843937, 0.98830472, 0.98816663, 0.98802498,
       0.98787962, 0.9877304 , 0.98757716, 0.98741975, 0.98725799,
       0.98709169, 0.98692067, 0.98674472, 0.98656362, 0.98637714,
       0.98618505, 0.98598708, 0.98578295, 0.98557239, 0.98535507,
       0.98513067, 0.98489884, 0.9846592 , 0.98441135, 0.98415485,
       0.98388928, 0.9836141 , 0.98332879, 0.9830328 , 0.9827255 ,
       0.98240624, 0.98207431, 0.98172894, 0.98136929, 0.98099446,
       0.98060347, 0.98019523, 0.97976862, 0.97932235, 0.97885501]
extra.reverse()
reit = [0.98421467, 0.98408263, 0.98394801, 0.98381071, 0.98367066,
       0.98352779, 0.98341283, 0.98332819, 0.98324175, 0.98315343,
       0.9830632 , 0.98297096, 0.98287668, 0.98278026, 0.98268164,
       0.98258075, 0.9824775 , 0.98237021, 0.98226199, 0.98215116,
       0.98203761, 0.98192124, 0.98180195, 0.98167963, 0.98155417,
       0.98142543, 0.98129329, 0.98115761, 0.98101824, 0.98087504,
       0.98072783, 0.98057646, 0.98042075, 0.98026049, 0.9800955 ,
       0.97992555, 0.97975042, 0.97956988, 0.97938367, 0.97919151,
       0.97899311, 0.97878818, 0.97857637, 0.97835734, 0.97813072,
       0.9778961 , 0.97765304, 0.97740109, 0.97713975, 0.97686851,
       0.97659088, 0.97629792, 0.97599316, 0.97567588, 0.97534528,
       0.97500051, 0.97464064, 0.97426465, 0.97387145, 0.97345981,
       0.9730284 , 0.97257578, 0.97210034, 0.97160031, 0.97107372,
       0.97051841, 0.96993196, 0.96931168, 0.96865456, 0.96795721,
       0.96721582, 0.9664261 , 0.96558316, 0.96468143, 0.96371546,
       0.9626761 , 0.96155585, 0.96034487, 0.95903159, 0.95760084,
       0.9560401 , 0.95432853, 0.95244351, 0.95035729, 0.94803592,
       0.9454375 , 0.94250938, 0.93918497, 0.93537865, 0.93097636,
       0.92583256, 0.91974399, 0.9124301 , 0.90349175, 0.89235477,
       0.878168  , 0.85973331, 0.83685854, 0.83387151]
reit.reverse()
fidelities_hybrid_3 = fidelities_hybrid_3 + extra
fidelities_adiabatic = [0.41290592,  0.57237587,  0.65617537, 0.70749028,  0.7420712,  0.7669413,  0.7856811,
                        0.80030586, 0.81203566, 0.82165203, 0.82967858, .83647926, 0.84452807, 0.85190099, 0.85837998, .86411824, 0.86923588, 0.87382837, 0.87797258, 0.88173106, 0.88515526, 0.88828786, .89116458, 0.89381553, 0.89626629, 0.89853869, .90065153, 0.90262104, 0.90446131, 0.90618467, .90780192, 0.90954892, 0.91152388, .91338907, .91515341, 0.91682483, .91841052, 0.9199169, .92134977, 0.92271438, 0.92401549, .92525744, 0.92644417, 0.92757928, 0.92866607, .92970756, 0.93070653, 0.93166551, 0.93258688, 0.9334728, 0.93432527, 0.93514616, 0.93593719, 0.93669995, 0.93743594, 0.93814654, 0.93883305, .93949666, 0.94013851, 0.94075964, 0.94136105, 0.94194366, 0.94250834, 0.9430559, 0.94358711, 0.94410269, .94460332, 0.94508964, 0.94556225, 0.94602174, 0.94646863, 0.94690344, .94732665,  0.94773872, .94825444, 0.9487709, 0.94927437, 0.94976535, 0.95024428, 0.95071162, 0.95116776, .95161312, 0.9520480, 0.95247296, 0.95288816, 0.95329397, 0.95369072, 0.95407871, .95445822, 0.95482954, 0.95519291, 0.9555486, 0.95589684, 0.95623788, .95657191, .95689918, 0.95721986, 0.95753417, .95784229]

fidelities_adiabatic_5 = [0.46861935, 0.4638493 , 0.45889193, 0.45373623, 0.44837031,
       0.44278135, 0.43695551, 0.43087782, 0.42453207, 0.41790069,
       0.41384591, 0.41023317, 0.40639859, 0.40232134, 0.39797791,
       0.39334171, 0.38838257, 0.3830661 , 0.37735294, 0.37119793,
       0.36454895, 0.35734564, 0.3495178 , 0.3409834 , 0.33164619,
       0.3213928 , 0.31008926, 0.29757688, 0.28366766, 0.26813956,
       0.2507328 , 0.23114971]
fidelities_adiabatic_5_more = [0.87134626, 0.87059113, 0.86982137, 0.86903653, 0.86823617,
       0.86741982, 0.86658701, 0.86573723, 0.86486996, 0.86398464,
       0.8630793 , 0.86215435, 0.86120951, 0.86024416, 0.8592576 ,
       0.85824914, 0.85721804, 0.85616352, 0.85508479, 0.85398099,
       0.85285125, 0.85169465, 0.8505102 , 0.8492969 , 0.84805367,
       0.84688861, 0.8459025 , 0.84488882, 0.84384831, 0.84277987,
       0.84168239, 0.84055465, 0.83939538, 0.83820325, 0.83697684,
       0.83571465, 0.8344151 , 0.8330765 , 0.83169706, 0.83027489,
       0.82880797, 0.82729417, 0.82573119, 0.8241166 , 0.82244782,
       0.82072206, 0.81893635, 0.81708754, 0.8151722 , 0.8131867 ,
       0.8111271 , 0.80898919, 0.80676842, 0.80445989, 0.80205829,
       0.79955788, 0.79695246, 0.79423528, 0.791399  , 0.78843563,
       0.78574591, 0.78340526, 0.78094832, 0.77836621, 0.77564911,
       0.77278617, 0.76976535, 0.76657322, 0.76319483, 0.75961339,
       0.75581008, 0.75176365, 0.74745008, 0.74284205, 0.73790843,
       0.73261354, 0.72691629, 0.72076916, 0.71411693, 0.70764449,
       0.70231623, 0.69645937, 0.68999129, 0.68281133, 0.67479544,
       0.66578914, 0.6555975 , 0.64397116, 0.63058596, 0.61501288,
       0.59667237, 0.57636916, 0.55987642, 0.53886745, 0.51121162]
fidelities_adiabatic_5_more.reverse()
fidelities_adiabatic_5.reverse()
fidelities_adiabatic_5 = fidelities_adiabatic_5 + fidelities_adiabatic_5_more
#xis_ss = np.arange(1, 15, 1)
fidelities_hybrid_5 = [0.95961293, 0.95932886, 0.95903924, 0.95874388, 0.95844259,
       0.9581352 , 0.95782152, 0.95750135, 0.95717449, 0.95684073,
       0.95649985, 0.95615162, 0.95579579, 0.95543213, 0.95506036,
       0.95468022, 0.95429142, 0.95389366, 0.95348663, 0.95306999,
       0.95264342, 0.95220655, 0.951759  , 0.95130038, 0.95089236,
       0.95049471, 0.95008671, 0.94966795, 0.94923801, 0.94879644,
       0.94834275, 0.94787643, 0.94739697, 0.94694725, 0.94653527,
       0.94611098, 0.94567381, 0.94522318, 0.94475845, 0.94427896,
       0.94378398, 0.94327277, 0.94274451, 0.94219834, 0.94163332,
       0.94104848, 0.94044275, 0.939815  , 0.93916441, 0.93848886,
       0.93778734, 0.93705832, 0.93630016, 0.93551108, 0.93468916,
       0.93383231, 0.93293825, 0.93200451, 0.9310284 , 0.93000697,
       0.928937  , 0.92781496, 0.92663695, 0.92539869, 0.92409544,
       0.92272196, 0.92127244, 0.91974039, 0.91811857, 0.91639887,
       0.91457218, 0.91262822, 0.91055535, 0.90834035, 0.90596812,
       0.90342136, 0.90068019, 0.89772076, 0.89451348, 0.89103006,
       0.88723341, 0.88307949, 0.87851566, 0.87347849, 0.86789082,
       0.8616913 , 0.85722394, 0.85210304, 0.84617449, 0.83923165,
       0.8309912 , 0.82105437, 0.8088461 , 0.79348553, 0.77359569]
fidelities_hybrid_5.reverse()
fidelities_hybrid_7 = [0.6198093 , 0.66106082, 0.68765436, 0.71145885, 0.73334756,
       0.75065468, 0.76466842, 0.77623929, 0.78595262, 0.79440675,
       0.80322555, 0.81094717, 0.81776316, 0.82382109, 0.82924381,
       0.83413113, 0.83855558, 0.8425703 , 0.84623613, 0.84958441,
       0.85276626, 0.85617813, 0.85934199, 0.8622683 , 0.86501008,
       0.86757232, 0.8704053 , 0.87311048, 0.87567257, 0.87807744,
       0.8803445 , 0.88249384, 0.88452995, 0.88646275, 0.88829892,
       0.89004726, 0.89171266, 0.89330024, 0.89481602, 0.89630397,
       0.89795271, 0.89952582, 0.90103492, 0.90248383, 0.90387605,
       0.90521468, 0.90650281, 0.90774459]

fidelities_hybrid_9 = [0.48424807, 0.52455794, 0.55558397, 0.58321262, 0.60646486,
       0.62504156, 0.64017486, 0.65497286, 0.66831446, 0.6798226 ,
       0.68986927, 0.69866158, 0.70651497, 0.71345057, 0.71988063,
       0.72663932, 0.73280611, 0.73843679, 0.74358765, 0.74916249,
       0.75436037, 0.75921629, 0.76374301, 0.7679585 , 0.77220181,
       0.77658636, 0.78073375, 0.78461858, 0.78829526, 0.79177905,
       0.79507553, 0.79815944, 0.80112615, 0.80387724, 0.80656805,
       0.80912431, 0.81166663, 0.81398785, 0.81623099, 0.81837724,
       0.82042597, 0.8223877, 0.82421838, 0.82603185, 0.82766338,
       0.82931339, 0.83092779, 0.83247711]

fidelities_adiabatic_7 = [0.31405756, 0.38094001, 0.42585802, 0.45794657, 0.48196588,
       0.50058696, 0.51544701, 0.52757628, 0.53082767, 0.56187447,
       0.57326339, 0.55199293, 0.59010562, 0.60096684, 0.60660861,
       0.61953371, 0.61843086, 0.63482186, 0.63367594, 0.64173656,
       0.65326835, 0.65610587, 0.66333453, 0.66854951, 0.67416318,
       0.67942228, 0.68436126, 0.68899372, 0.69336944, 0.69749943,
       0.70140373, 0.70510025, 0.70860502, 0.71193251, 0.71509415,
       0.71810505, 0.72000895, 0.72371382, 0.72688873, 0.73010773,
       0.73319196, 0.73614984, 0.73898896, 0.74171629, 0.7443383 ,
       0.74686095, 0.74928975, 0.75162981]
fidelities_adiabatic_9=[0.20687531, 0.26210873, 0.30043094, 0.32831706, 0.34943632,
       0.36018815, 0.38008186, 0.39672833, 0.4108204 , 0.42292874,
       0.43339016, 0.44255308, 0.45193125, 0.46218553, 0.47138492,
       0.47975232, 0.48740176, 0.48876992, 0.50077847, 0.50666733,
       0.51211166, 0.51887541, 0.52518126, 0.53125854, 0.53670264,
       0.54186874, 0.54675944, 0.55136671, 0.55571418, 0.5597043 ,
       0.56357621, 0.56738035, 0.57095646, 0.57525252, 0.57932424,
       0.5802841 , 0.58695439, 0.59032284, 0.59373671, 0.59699387,
       0.60012402, 0.60326196, 0.60616045, 0.60894291, 0.61161696,
       0.61418713, 0.61665625, 0.6190268]
def fit_exp(data):
    def exp(x, k):
        return np.exp(-k/x)

    k, error = scipy.optimize.curve_fit(exp, data[0], data[1])
    k = k[0]
    error = np.sqrt(error[0][0])

    plt.plot(data[0], [exp(x, k) for x in data[0]], color='k')

    print('exp', k, error)

    return k, error

def fit_sqrt_exp(data):
    def exp(x, k):
        return np.exp(-k/np.sqrt(x))

    k, error = scipy.optimize.curve_fit(exp, data[0], data[1])
    k = k[0]
    error = np.sqrt(error[0][0])
    data = np.linspace(data[0], data[-1], len(data))
    plt.plot(data[0], [exp(x, k) for x in data[0]], color='k', linestyle='dashed')
    print('sqrt exp', k, error)
    return k, error
xis_hybrid_3 = np.concatenate([np.arange(60, 2110, 50), np.arange(2000, 5000, 50)])
xis_adiabatic = np.arange(60, 5000, 50)
xis_reit = np.arange(50, 5000, 50)
xis_hybrid_5 = np.arange(250, 5000, 50)
xis_hybrid_7 = np.arange(250, 5000, 100)
xis_adiabatic_7 = np.arange(250, 5000, 100)
xis_adiabatic_5 = np.concatenate([np.arange(40, 200, 5), np.arange(250, 5000, 50)])
print(len(xis_reit), len(reit))
fit_exp([xis_hybrid_3[-30:], fidelities_hybrid_3[-30:]])
fit_exp([xis_adiabatic[-30:], fidelities_adiabatic[-30:]])

k_adiabatic_3, error_adiabatic_3 = fit_sqrt_exp([xis_adiabatic[-30:], fidelities_adiabatic[-30:]])
k_adiabatic_5, error_adiabatic_5 = fit_sqrt_exp([xis_adiabatic_5[-30:], fidelities_adiabatic_5[-30:]])
k_adiabatic_7, error_adiabatic_7 = fit_sqrt_exp([xis_adiabatic_7[-20:], fidelities_adiabatic_7[-20:]])
k_adiabatic_9, error_adiabatic_9 = fit_sqrt_exp([xis_adiabatic_7[-20:], fidelities_adiabatic_9[-20:]])

#fit_exp([xis_hybrid_3, fidelities_hybrid_3])
k_hybrid_3, error_hybrid_3 = fit_sqrt_exp([xis_hybrid_3[-30:], fidelities_hybrid_3[-30:]])
#fit_exp([xis_hybrid_5, fidelities_hybrid_5])
k_hybrid_5, error_hybrid_5 = fit_sqrt_exp([xis_hybrid_5, fidelities_hybrid_5])
k_hybrid_7, error_hybrid_7 = fit_sqrt_exp([xis_hybrid_7, fidelities_hybrid_7])
k_hybrid_9, error_hybrid_9 = fit_sqrt_exp([xis_hybrid_7, fidelities_hybrid_9])

#fit_exp([xis_reit, reit])
#fit_sqrt_exp([xis_reit, reit])
#plt.scatter(xis_ss, fidelities_ss, color='green')
plt.scatter(xis_reit, reit, color='purple', label='reit 3')

plt.scatter(xis_hybrid_3, fidelities_hybrid_3, color='blue', label='hybrid 3')
plt.scatter(xis_adiabatic, fidelities_adiabatic, color='green', label='adiabatic 3')
plt.scatter(xis_adiabatic_5, fidelities_adiabatic_5, color='lightgreen', label='adiabatic 5')
plt.scatter(xis_adiabatic_7, fidelities_adiabatic_7, color='lime', label='adiabatic 7')
plt.scatter(xis_adiabatic_7, fidelities_adiabatic_9, color='springgreen', label='adiabatic 9')

plt.scatter(xis_hybrid_5, fidelities_hybrid_5, color='lightblue', label='hybrid 5')
plt.scatter(xis_hybrid_7, fidelities_hybrid_7, color='teal', label='hybrid 7')
plt.scatter(xis_hybrid_7, fidelities_hybrid_9, color='seagreen', label='hybrid 9')

plt.legend()
plt.xlabel(r'$\Omega^2 T/\gamma$')
[plt.ylabel(r'Fidelity')]
#plt.show()

def scaling_vs_n():
    plt.clf()


    plt.errorbar([3, 5, 7, 9], [k_adiabatic_3, k_adiabatic_5, k_adiabatic_7, k_adiabatic_9], yerr = [error_adiabatic_3, error_adiabatic_5, error_adiabatic_7, error_adiabatic_9], color='green', markersize=10, capsize=10, label='adiabatic')
    plt.errorbar([3, 5, 7, 9], [k_hybrid_3, k_hybrid_5, k_hybrid_7, k_hybrid_9], yerr=[error_hybrid_3, error_hybrid_5, error_hybrid_7, error_hybrid_9], color='blue', markersize=10, capsize=10, label='hybrid')
    plt.scatter([3, 5, 7, 9], [k_adiabatic_3, k_adiabatic_5, k_adiabatic_7, k_adiabatic_9], color='k')
    plt.scatter([3, 5, 7, 9], [k_hybrid_3, k_hybrid_5, k_hybrid_7, k_hybrid_9], color='k')
    plt.xlabel(r'$n$')
    plt.ylabel(r'$k$')
    plt.legend()
    plt.show()
#scaling_vs_n()