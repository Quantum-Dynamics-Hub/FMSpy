"""
Compute saddle-point integrals over trajectories traveling on adiabataic
potentials

This currently uses first-order saddle point.
"""
import numpy as np
import src.integrals.nuclear_cs_gaussian as nuclear
import src.interfaces.vibronic as vibronic 
import src.interfaces.vcham.hampar as ham

# Let propagator know if we need data at centroids to propagate
require_centroids = False 

# Determines the Hamiltonian symmetry
hermitian = True 

# returns basis in which matrix elements are evaluated
basis = 'gaussian'

def elec_overlap(traj1, traj2):
    """ Returns < Psi | Psi' >, the overlap integral of two trajectories"""

#    dia1      = traj1.pes_data.diabat_pot
#    argt1     = 2. * dia1[0,1] / (dia1[1,1] - dia1[0,0])
#    theta1    = 0.5 * np.arctan(argt1)
#    st1      = np.array([[np.cos(theta1),np.sin(theta1)],[-np.sin(theta1),np.cos(theta1)]])

#    dia2      = traj2.pes_data.diabat_pot
#    argt2     = 2. * dia2[0,1] / (dia2[1,1] - dia2[0,0])
#    theta2    = 0.5 * np.arctan(argt2)
#    st2      = np.array([[np.cos(theta2),np.sin(theta2)],[-np.sin(theta2),np.cos(theta2)]])

    # determine overlap of adiabatic wave functions in diabatic basis
#    return complex( np.dot(traj1.pes_data.dat_mat[:,traj1.state],
#                           traj2.pes_data.dat_mat[:,traj2.state]), 0.)
#    if traj1.tid != traj2.tid:
#        print('tid1, tid2='+str(traj1.tid)+' '+str(traj2.tid))
#        print('arg1,arg2='+str(argt1)+' '+str(argt2))
#        print('v12_1, v12_2='+str(dia1[0,1])+' '+str(dia2[0,1]))
#        print('de_1, de_2='+str(dia1[1,1]-dia1[0,0])+' '+str(dia2[1,1]-dia2[0,0]))
#        print('theta1, theta2='+str(theta1)+' '+str(theta2))
#        print('electronic ovrlp='+str(np.dot(st1[traj1.state,:],st2[traj2.state,:])))
#    return complex( np.dot(st1[traj1.state,:],st2[traj2.state,:]), 0.)
    return complex( np.dot(traj1.pes_data.dat_mat[:,traj1.state],
                           traj2.pes_data.dat_mat[:,traj2.state]), 0.)

# returns the overlap between two trajectories (differs from s_integral in that
# the bra and ket functions for the s_integral may be different
# (i.e. pseudospectral/collocation methods). 
def traj_overlap(traj1, traj2, centroid=None, nuc_only=False):
    """ Returns < Psi | Psi' >, the overlap integral of two trajectories"""
    nuc_ovrlp = nuclear.overlap(traj1.phase(),traj1.widths(),traj1.x(),traj1.p(),
                                traj2.phase(),traj2.widths(),traj2.x(),traj2.p())

    if nuc_only:
        return nuc_ovrlp
    else:
        return nuc_ovrlp * elec_overlap(traj1, traj2)

# total overlap of trajectory basis function
def s_integral(traj1, traj2, centroid=None, nuc_only=False, Snuc=None):
    """ Returns < Psi | Psi' >, the overlap of the nuclear
    component of the wave function only"""
    if Snuc is None:
        Snuc = traj_overlap(traj1, traj2, centroid=centroid, nuc_only=True)

    if nuc_only:
        return Snuc
    else:
        return Snuc * elec_overlap(traj1, traj2) 

def prim_v_integral(N, a1, x1, p1, a2, x2, p2, gauss_overlap=None):
    """Returns the matrix element <cmplx_gaus(q,p)| q^N |cmplx_gaus(q,p)>
     -- up to an overlap integral -- 
    """
    # since range(N) runs up to N-1, add "1" to result of floor
    n_2 = int(np.floor(0.5 * N) + 1)
    a   = a1 + a2
    b   = complex(2.*(a1*x1 + a2*x2),-(p1-p2))

    # generally these should be 1D harmonic oscillators. If
    # multi-dimensional, the final result is a direct product of
    # each dimension
    v_int = complex(0.,0.)
    for i in range(n_2):
        v_int += (a**(i-N) * b**(N-2*i) /
                 (np.math.factorial(i) * np.math.factorial(N-2*i)))

    # refer to appendix for derivation of these relations
    return v_int * np.math.factorial(N) / 2.**N

#
def v_integral(traj1, traj2, centroid=None, Snuc=None):
    """Returns potential coupling matrix element between two trajectories."""
    # evaluate just the nuclear component (for re-use)
    if Snuc is None:
        Snuc = nuclear.overlap(traj1.phase(),traj1.widths(),traj1.x(),traj1.p(),
                               traj2.phase(),traj2.widths(),traj2.x(),traj2.p())

    # get the linear combinations corresponding to the adiabatic states
    nst = traj1.nstates
    st1 = traj1.pes_data.dat_mat[:,traj1.state]
    st2 = traj2.pes_data.dat_mat[:,traj2.state]

    # roll through terms in the hamiltonian
    h_nuc = np.zeros((nst,nst),dtype=complex)
    for i in range(ham.nterms):
        s1    = ham.stalbl[i,0] - 1
        s2    = ham.stalbl[i,1] - 1
      
        # adiabatic states in diabatic basis -- cross terms between orthogonal
        # diabatic states are zero
        v_term = complex(1.,0.) * ham.coe[i]
        for q in range(ham.nmode_active):
            if ham.order[i,q] > 0:
                v_term *=  prim_v_integral(ham.order[i,q],
                           traj1.widths()[q],traj1.x()[q],traj1.p()[q],
                           traj2.widths()[q],traj2.x()[q],traj2.p()[q])            
      
        h_nuc[s1,s2] += (v_term * Snuc)
      
    # Fill in the upper-triangle
    for s1 in range(nst-1):
        for s2 in range(s1+1, nst):
            h_nuc[s1,s2] = complex(0.,0.)
            h_nuc[s2,s1] = h_nuc[s1,s2]

#    print("v integral: "+str(h_nuc))
    # return potential matrix element
    return np.dot(np.dot(st1,h_nuc),st2)

# kinetic energy integral
def ke_integral(traj1, traj2, centroid=None, Snuc=None):
    """Returns kinetic energy integral over trajectories."""
    # evaluate just the nuclear component (for re-use)
    if Snuc is None:
        Snuc = nuclear.overlap(traj1.phase(),traj1.widths(),traj1.x(),traj1.p(),
                               traj2.phase(),traj2.widths(),traj2.x(),traj2.p())

    # overlap of electronic functions
    Selec = elec_overlap(traj1, traj2)

    # < chi | del^2 / dx^2 | chi'> 
    ke = nuclear.deld2x(Snuc,traj1.phase(),traj1.widths(),traj1.x(),traj1.p(),
                             traj2.phase(),traj2.widths(),traj2.x(),traj2.p())
   
    return -sum( ke * vibronic.kecoeff) * Selec

    
# time derivative of the overlap
def sdot_integral(traj1, traj2, centroid=None, Snuc=None, e_only=False, nuc_only=False):
    """Returns the matrix element <Psi_1 | d/dt | Psi_2>."""
    if Snuc is None:
        Snuc = nuclear.overlap(traj1.phase(),traj1.widths(),traj1.x(),traj1.p(),
                               traj2.phase(),traj2.widths(),traj2.x(),traj2.p())

    # overlap of electronic functions
    Selec = elec_overlap(traj1, traj2)

    # < chi | d / dx | chi'>
    deldx = nuclear.deldx(Snuc,traj1.phase(),traj1.widths(),traj1.x(),traj1.p(),
                               traj2.phase(),traj2.widths(),traj2.x(),traj2.p())
    # < chi | d / dp | chi'>
    deldp = nuclear.deldp(Snuc,traj1.phase(),traj1.widths(),traj1.x(),traj1.p(),
                               traj2.phase(),traj2.widths(),traj2.x(),traj2.p())

    # the nuclear contribution to the sdot matrix
#    sdot = ( np.dot(traj2.velocity(), deldx) + np.dot(traj2.force(), deldp) 
#            + 1j * traj2.phase_dot() * Snuc) * Selec
    sdot = (np.dot(deldx, traj2.velocity()) + np.dot(deldp, traj2.force()) ) * Selec
    print('vel, for='+str(np.dot(deldx, traj2.velocity()))+' '+str(np.dot(deldp, traj2.force())))

    if nuc_only:
        return sdot

    # the derivative coupling
    dia      = traj2.pes_data.diabat_pot
    diaderiv = traj2.pes_data.diabat_deriv
    v12      = dia[0,1]
    de       = dia[1,1] - dia[0,0]
    argt     = 2. * v12 / de
    t1       = 0.5 * np.arctan2(2.*v12, de)

    # ensure theta agrees with dat matrix
    pi_mult  = [-2.,1.,0.,1.,2.]
    dif_vec  = np.array([np.linalg.norm(traj2.pes_data.dat_mat - 
                                 np.array([[np.cos(t1+i*np.pi),-np.sin(t1+i*np.pi)],
                                           [np.sin(t1+i*np.pi),np.cos(t1+i*np.pi)]])) 
                                           for i in pi_mult])

    theta = t1 + pi_mult[np.argmin(dif_vec)]*np.pi
    dangle = np.array([(diaderiv[q,0,1]/de - 
                        v12*(diaderiv[q,1,1]- diaderiv[q,0,0])/de**2)/(1+argt**2) 
                        for q in range(traj2.dim)])
    

    dphi  = np.array([[-np.sin(theta),-np.cos(theta)],
                      [ np.cos(theta),-np.sin(theta)]])
    dtheta  = np.array([[dphi[i,traj2.state]*dangle[q] for q in range(traj2.dim)] for i in range(traj2.nstates)])
    deriv_coup = np.array([np.dot(traj1.pes_data.dat_mat[:,traj1.state],dtheta[:,q]) for q in range(traj2.dim)])

    if e_only:
        print("deriv_coup, t2.vel="+str(deriv_coup)+' '+str(traj2.velocity()))
        print("phi1, dphi2="+str(traj1.pes_data.dat_mat[:,traj1.state])+' '+str(dtheta))
        return np.dot(deriv_coup, traj2.velocity()) * Snuc

    # time-derivative of the electronic component
    sdot += np.dot(deriv_coup, traj2.velocity()) * Snuc

    return sdot
 
