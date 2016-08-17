import sys
import numpy as np
import copy
import src.dynamics.timings as timings
import src.fmsio.glbl as glbl
import src.basis.bundle as bundle
import src.utils.linear as linear

selected = []
coeff = []
nbas = 0
conv = None
gamma = 0.

def reexpress_basis(master):
    """ Re-expresses the Gaussian basis using the matching pursuit
    method. The specific algorithm used is taken from
    S. Habershon, J. Chem. Phys. 136, 014109 (2102)."""

    # Condition number threshold
    epsilon = 1e+7

    # If the condition number of the overlap matrix is below
    # threshold, then return, else re-exress the basis using the
    # matching pursuit algorithm 
    Sinv, cond = linear.pseudo_inverse(master.S)
    if cond <= epsilon:
        return
    else:
        matching_pursuit(master)

    return


def matching_pursuit(master):

    global conv, gamma, nbas, selected, coeff

    # Convergence threshold
    gamma = 1e-4

    # Initialise arrays
    nbas = 0
    selected = []
    coeff = []

    # Initialise the residual wavefunction
    residual = bundle.copy_bundle(master)

    # Perform the MP iterations
    conv = False
    while not conv:
        mp_1iter(residual,master)

    # Construct the new wavefunction
    reset_wavefunction(master)

    return


def mp_1iter(residual,master):

    global selected, nbas, coeff, conv

    # (1) Basis function selection
    indx = select_basfunc(residual)
    selected.append(indx)
    nbas += 1

    # (2) Coefficients for the selected basis functions
    coeff.append(complex(0., 0.))
    coeff_basfunc(residual,master)

    # Exit if we have reached the
    # maximum number of trajectories
    if nbas == len(master.traj):
        conv = True
        return

    # (3) Check for convergence
    check_conv(residual,master)
    if conv == True:
        return

    # (4) Update the residual
    update_residual(residual)
    
    return


def select_basfunc(residual):

    global selected

    indx = -1    
    maxovrlp = 0.
    for i in range(residual.nalive + residual.ndead):
        ovrlp = residual.traj[i].overlap_bundle(residual)
        if abs(ovrlp) > abs(maxovrlp) and i not in selected:
            maxovrlp = ovrlp
            indx = i

    return indx


def coeff_basfunc(residual,master):

    global selected, nbas

    # Construct the inverse overlap matrix for the selected basis functions
    smat = np.zeros((nbas,nbas), dtype=np.complex)
    for i in range(nbas):
        iindx = selected[i]
        for j in range(i+1):
            jindx = selected[j]
            smat[i,j] = residual.traj[iindx].overlap(residual.traj[jindx], 
                                                     st_orthog=True)
            smat[j,i] = smat[i,j].conjugate()
    sinv, cond = linear.pseudo_inverse(smat)

    # Project the selected basis functions onto the target
    for i in range(nbas):
        iindx = selected[i]
        coe = complex(0., 0.)
        for j in range(nbas):
            jindx = selected[j]
            coe += (sinv[i,j] *
                    residual.traj[jindx].overlap_bundle(master))
        coeff[i]=coe

    return


def check_conv(residual,master):
    
    global selected, nbas, coeff, conv, gamma
    
    # Create a bundle corresponding to the selected basis functions
    new = bundle.copy_bundle(residual)
    for i in range(new.nalive+new.ndead):
        new.traj[i].amplitude = np.copy(complex(0., 0.))
    for i in range(nbas):
        indx = selected[i]
        new.traj[indx].amplitude = np.copy(coeff[i])

    # Normalise (?)
    new.renormalize()

    # Check convergence
    eta = 1.0 - new.overlap(master).real
    if eta < gamma:
        conv = True

    return


def update_residual(residual):

    global selected, nbas, coeff

    # Residual -> residual - new
    for i in range(nbas):
        indx = selected[i]        
        residual.traj[indx].amplitude -= np.copy(coeff[i])

    # Renormalisation
    residual.renormalize()

    return


def reset_wavefunction(master):

    global selected, nbas, coeff
    
    # Sort the selected basis functions and coefficients in order of
    # ascending basis function index
    indxmap = sorted(range(len(selected)), key=lambda k: selected[k])
    tmp = copy.copy(coeff)
    for i in range(nbas):
        coeff[i] = tmp[indxmap[i]]
    selected.sort()

    # Kill all trajectories
    indx = np.copy(master.alive)
    for i in range(len(indx)):
        master.kill_trajectory(indx[i])
    
    # Add the selected trajectories
    for i in range(nbas):
        indx = selected[i]
        master.revive_trajectory(indx)

    # Set the new coefficients
    for i in range(master.nalive+master.ndead):
        master.traj[i].amplitude = np.copy(complex(0., 0.))
    for i in range(nbas):
        indx = selected[i]
        master.traj[indx].amplitude = np.copy(coeff[i])

    # Re-calculate the overlap matrix for the subset of selected basis
    # functions.
    # Note that this needs to be done so that we can renormalise, and
    # that we need to renormalise so that the matrices T, V, Sdot,
    # etc. can be calculated.
    # This incurs one additional (and unecessary) calculation of the
    # S-matix, as this matrix is also calculated in update-matrices,
    # but will do for now.
    recalc_overlap(master)
    
    # Renormalise
    master.renormalize()

    # Rebuild all matrices T, V, S, Sdot, and Heff now that our basis
    # has changed
    master.update_matrices()

    return


def recalc_overlap(master):

    for i in range(master.nalive):
        iindx = master.alive[i]
        for j in range(i+1):
            jindx = master.alive[j]
            master.S[i,j] = (master.traj[iindx].overlap(master.traj[jindx],
                                                        st_orthog=False))
            master.S[j,i] = master.S[i,j].conjugate()

    return
