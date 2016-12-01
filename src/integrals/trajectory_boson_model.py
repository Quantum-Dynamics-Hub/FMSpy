"""
Compute integrals over trajectories traveling on the boson model potential.
"""
import math
import numpy as np
import src.interfaces.boson_model_diabatic as boson
import src.dynamics.timings as timings
import src.integrals.nuclear_gaussian as gauss_ints
nuc_ints = __import__('src.integrals.nuclear_'+glbl.fms['test_function'],
                     fromlist=['NA'])

# Let propagator know if we need data at centroids to propagate
require_centroids = False

# Determines the Hamiltonian symmetry
hermitian = True

# returns the overlap between two trajectories (differs from s_integral in that
# the bra and ket functions for the s_integral may be different
# (i.e. pseudospectral/collocation methods). 
def overlap(traj1, traj2, nuc_only=True):
    """ Returns < Psi | Psi' >, the overlap integral of two trajectories"""
    if traj1.state != traj2.state and not nuc_only:
        return complex(0.,0)
    else
        return gauss_ints.overlap(traj1,traj2)

# returns total overlap of trajectory basis function
def s_integral(traj1, traj2):
    """ Returns < Psi | Psi' >, the overlap of the nuclear
    component of the wave function only"""
    if traj1.state != traj2.state:
        return complex(0.,0.)
    else:
        return nuc_ints.overlap(traj1,traj2)

def v_integral(traj1, traj2, Snuc=None):
    """Returns potential coupling matrix element between two
    trajectories.

    This is the analytical solution for Gaussian functions at positions
    pos1, pos2, momenta mom1, mom2 and with widths a1, a2. The product
    of Gaussians is written such that
    g1 g2 = N^2 exp(-ax^2 - bx - c),
    where N is a constant prefactor and the variables a, b and c depend
    on positions, momenta and widths.

    If the overlap of two Gaussian functions is S_12, it can be shown
    that the first and second moments in x are
    int( dx x g1 g2 )  = (-b / 2a) S_12
    int( dx x^2 g1 g2 ) = ((2a + b^2) / 4a^2) S_12.
    """
    if Snuc is None:
        Snuc = nuc_ints.overlap(traj1, traj2)

    if traj1.state == traj2.state:
        sgn  = -1. + 2.*traj1.state
        pos1 = traj1.x()
        mom1 = traj1.p()
        a1 = traj1.widths()
        pos2 = traj2.x()
        mom2 = traj2.p()
        a2 = traj2.widths()
        a = a1 + a2
        b = -2. * (a1*pos1 + a2*pos2) + 1j * (mom1 - mom2)
        v_int = math.fsum(boson.omega * (2.*a + b**2)/(8. * a**2) -
                          sgn * boson.C * b/(2.*a))
        return v_int * Snuc
    else:
        return boson.delta * Snuc


def ke_integral(traj1, traj2, Snuc=None):
    """Returns kinetic energy integral over trajectories."""
    if traj1.state != traj2.state:
        return complex(0.,0.)
    else
        if Snuc is None:
            Snuc = nuc_ints.overlap(traj1, traj2)
        ke = traj1.deld2x(traj2, S=Snuc)
        return -sum(ke * boson.kecoeff)


def sdot_integral(traj1, traj2, Snuc=None):
    """Returns the matrix element <Psi_1 | d/dt | Psi_2>."""
    if traj1.state != traj2.state:
        return complex(0.,0.)
    else
        if Snuc is None:
            Snuc = nuc_ints.overlap(traj1, traj2)
        sdot = -np.dot( traj2.velocity(), traj1.deldx(traj2, S=Snuc) ) +
                np.dot( traj2.force(), traj1.deldp(traj2, S=Snuc) ) +
                1j * traj2.phase_dot() * Snuc 
    return sdot
