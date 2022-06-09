# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #  

# Example 4: Hodgkin-Huxley Action Potential propagation model

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #  

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # IMPORTS # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

import steps.interface

from steps.model import *
from steps.geom import *
from steps.sim import *
from steps.saving import *
from steps.rng import *

import numpy as np
import os
import math

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #  
# # # # # # # # # # # # # # # # # # PARAMETERS  # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

# # # # # # # # # # # # # # # # # # CHANNELS  # # # # # # # # # # # # # # # # # #

# Potassium conductance = 0.036 S/cm2
# Sodium conductance = 0.120 S/cm2

# Potassium single-channel conductance
K_G = 20.0e-12 # Siemens

# Potassium channel density
K_ro = 18.0e12 # per square meter

# Potassium reversal potential
K_rev = -77e-3 # volts

# Sodium single-channel conductance
Na_G = 20.0e-12 # Siemens

# Sodium channel density
Na_ro = 60.0e12 # per square meter

# Sodium reversal potential
Na_rev = 50e-3 # volts

# Leak single-channel conductance
L_G = 0.3e-12 # Siemens

# Leak density
L_ro = 10.0e12 # per square meter

# Leak reveral potential
leak_rev = -54.4e-3 # volts


# A table of potassium channel population factors: 
# n0, n1, n2, n3, n4
K_facs = [ 0.21768, 0.40513, 0.28093, 0.08647, 0.00979 ]

# A table of sodium channel population factors
# m0h0, m1h0, m2h0, m3h0, m0h1, m1h1, m2h1, m3h1:
Na_facs = [[0.34412, 0.05733, 0.00327, 6.0e-05],
           [0.50558, 0.08504, 0.00449, 0.00010]]

# # # # # # # # # # # # # # # # # # RATE FUNCTION # # # # # # # # # # # # # # # #

def HHRateFunction(celsius, A, B, C, D, F, H, V, abs_tol=1e-13):
    # Temperature dependence
    thi = 1e3 * math.pow(3.0, ((celsius-6.3)/10.0))
    
    num = A + B * V * 1e3
    denom = C + H * math.exp((V * 1e3 + D) / F)
    if math.isclose(num, 0, abs_tol=abs_tol) and math.isclose(denom, 0, abs_tol=abs_tol):
        return thi * F * B / (H * math.exp((V * 1e3 + D) / F))
    else:
        return thi * num / denom

# # # # # # # # # # # # # # # # # # MESH  # # # # # # # # # # # # # # # # # # # # 

meshfile_ab = 'meshes/axon_cube_L1000um_D443nm_equiv0.5_19087tets.inp'

# # # # # # # # # # # # # # # SIMULATION CONTROLS # # # # # # # # # # # # # # # #

# Temperature for gating kinetics
celsius = 20.0

# Current injection
Iclamp = 50.0e-12 #	amps

# Voltage range for gating kinetics in Volts
Vrange = [-100.0e-3, 50e-3, 1e-4]

# The simulation dt
DT_sim = 1.0e-4 # seconds

# The time until which the simulation should be run
ENDT = 4.0e-3

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# # # # # # # # # # # # # # # BIOCHEMICAL MODEL # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

mdl = Model()

r = ReactionManager()

with mdl:
    ssys = SurfaceSystem.Create()

    #  Potassium channel
    Ko, Kc = SubUnitState.Create()
    KSU = SubUnit.Create([Ko, Kc])
    VGKC = Channel.Create([KSU]*4)

    # Sodium channel
    Na_mo, Na_mc, Na_hi, Na_ha = SubUnitState.Create()
    NamSU, NahSU = SubUnit.Create(
        [Na_mo, Na_mc],
        [Na_hi, Na_ha]
    )
    VGNaC = Channel.Create([NamSU, NamSU, NamSU, NahSU])

    # Leak channel
    lsus = SubUnitState.Create()
    Leak = Channel.Create([lsus])

    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

    # Hodgkin-Huxley gating kinetics

    _a_n = VDepRate(lambda V: HHRateFunction(celsius, -0.55, -0.01, -1, 55, -10, 1, V), vrange=Vrange)
    _b_n = VDepRate(lambda V: HHRateFunction(celsius, 1, 0, 0, 65, 80, 8, V), vrange=Vrange)
    
    _a_m = VDepRate(lambda V: HHRateFunction(celsius, -4, -0.1, -1, 40, -10, 1, V), vrange=Vrange)
    _b_m = VDepRate(lambda V: HHRateFunction(celsius, 1, 0, 0, 65, 18, 0.25, V), vrange=Vrange)
    
    _a_h = VDepRate(lambda V: HHRateFunction(celsius, 1, 0, 0, 65, 20, 1 / 0.07, V), vrange=Vrange)
    _b_h = VDepRate(lambda V: HHRateFunction(celsius, 1, 0, 1, 35, -10, 1, V), vrange=Vrange)

    with ssys:

        with VGKC[...]:
            Kc.s <r[1]> Ko.s
            r[1].K = _a_n, _b_n

        with VGNaC[...]:
            Na_hi.s <r[1]> Na_ha.s
            r[1].K = _a_h, _b_h
            
            Na_mc.s <r[1]> Na_mo.s
            r[1].K = _a_m, _b_m

        # Create ohmic current objects
        VGKC_I = OhmicCurr.Create(VGKC[Ko, Ko, Ko, Ko], K_G, K_rev)
        VGNaC_I = OhmicCurr.Create(VGNaC[Na_mo, Na_mo, Na_mo, Na_ha], Na_G, Na_rev)
        Leak_I = OhmicCurr.Create(Leak[lsus], L_G, leak_rev)

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# # # # # # # # # # # # # # # TETRAHEDRAL MESH  # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

mesh = TetMesh.LoadAbaqus(meshfile_ab, scale=1e-6)

# # # # # # # # # # # # # # # MESH MANIPULATION # # # # # # # # # # # # # # # # #

facetris = TriList([tri for tri in mesh.tris if tri.center.z == mesh.bbox.min.z])
injverts = facetris.verts

print("Found ", len(injverts), "I_inject vertices")
print("Found ", len(facetris), "triangles on bottom face")

memb_tris = mesh.surface - facetris

# The points along (z) axis at which to record potential
pot_pos = np.arange(mesh.bbox.min.z, mesh.bbox.max.z, 10e-6)
pot_tet = [mesh.tets[(0, 0, z)] for z in pot_pos]

# # # # # # # # # # # # # # # GEOMETRY OBJECTS  # # # # # # # # # # # # # # # # #

with mesh:
    # Create cytosol compartment
    cyto = Compartment.Create(mesh.tets)

    # Create the patch and associate with surface system ssys
    patch = Patch.Create(memb_tris, cyto, None, ssys)

    # Create the membrane across which the potential will be solved
    membrane = Membrane.Create([patch], opt_method = 1)

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# # # # # # # # # # # # # # # # # SIMULATION  # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

rng = RNG('mt19937', 512, 1234)

sim = Simulation('Tetexact', mdl, mesh, rng, True)

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

rs = ResultSelector(sim)

NaCurrs = rs.TRIS(memb_tris).VGNaC_I.I
KCurrs = rs.TRIS(memb_tris).VGKC_I.I
CellPot = rs.TETS(pot_tet).V

NaCurrs.metaData['trizpos'] = [tri.center.z for tri in memb_tris]
KCurrs.metaData['trizpos'] = [tri.center.z for tri in memb_tris]
NaCurrs.metaData['triarea'] = [tri.Area for tri in memb_tris]
KCurrs.metaData['triarea'] = [tri.Area for tri in memb_tris]
CellPot.metaData['tetzpos'] = pot_pos

sim.toSave(NaCurrs, KCurrs, CellPot, dt=DT_sim)

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

sim.newRun()

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

# Inject channels
surfarea = sim.patch.Area

for state in VGNaC:
    prop = Na_facs[state.Count(Na_ha)][state.Count(Na_mo)]
    sim.patch.VGNaC[state].Count = Na_ro * surfarea * prop

for state in VGKC:
    prop = K_facs[state.Count(Ko)]
    sim.patch.VGKC[state].Count = K_ro * surfarea * prop

sim.patch.Leak[lsus].Count = L_ro * surfarea

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

# Set some simulation variables:

# Set dt for membrane potential calculation to 0.01ms
sim.EfieldDT = 1.0e-5

# Initialize potential to -65mV
sim.membrane.Potential = -65e-3

# Set capacitance of the membrane to 1 uF/cm^2 = 0.01 F/m^2
sim.membrane.Capac = 1.0e-2

# Set resistivity of the conduction volume to 100 ohm.cm = 1 ohm.meter
sim.membrane.VolRes = 1.0

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Set the current clamp

sim.VERTS(injverts).IClamp = Iclamp/len(injverts)

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

# Run the simulation
sim.run(ENDT)

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

from matplotlib import pyplot as plt

NBINS = 100

def getTIdx(saver, t):
    return min(enumerate(saver.time[0]), key=lambda v: abs(v[1] - t))[0]

def plotPotential(t):
    tidx = getTIdx(CellPot, t)
    plt.plot(
        CellPot.metaData['tetzpos'] * 1e6, 
        CellPot.data[0, tidx, :] * 1e3, 
        label=f'{CellPot.time[0, tidx]*1e3} ms'
    )

def plotCurrents(t):
    tidx = getTIdx(NaCurrs, t)
    for results, currName in zip([NaCurrs, KCurrs], ['Na', 'K']):
        data = results.data[0, tidx, :] * 1e12
        pos = results.metaData['trizpos'] * 1e6
        areas = results.metaData['triarea'] * 1e12
        bins = np.histogram_bin_edges(pos, NBINS)
        dig = np.digitize(pos, bins)
        # Ignore empty bins
        with np.errstate(invalid='ignore'):
            meanData = np.bincount(dig, weights=data) / np.bincount(dig, weights=areas)
            meanPos  = np.bincount(dig, weights=pos) / np.bincount(dig)
        plt.plot(meanPos, meanData, label=f'{currName} {results.time[0, tidx]*1e3} ms')

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
    
plotPotential(1e-3)
plotPotential(2e-3)
plotPotential(3e-3)
plt.xlabel('Z-axis (um)')
plt.ylabel('Membrane potential (mV)')
plt.legend()
plt.show()
    
plotCurrents(1e-3)
plotCurrents(2e-3)
plotCurrents(3e-3)
plt.xlabel('Z-axis (um)')
plt.ylabel('Current  (pA/um^2)')
plt.legend()
plt.show()
