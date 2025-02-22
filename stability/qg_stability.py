import numpy as np
from numpy import pi, sqrt
from scipy import integrate
import scipy as sp
import scipy.linalg
import scipy.io
import seawater as sw
import matplotlib.pyplot as plt

# compare against finite differences (2nd order)
def stretching_matrix(N,S,dz):
    """ Computes the continuously stratified QG streching matrix
        N is the size of the array and S is the stratification vector
            constant dz
                            """
    SM = np.zeros((N,N))
    for i in range(N):
        if i == 0:
            SM[0,0], SM[0,1] = -2*S[0],2*S[0]
        elif i==N-1:
            SM[-1,-2], SM[-1,-1] = 2*S[-1], -2*S[-1]
        else:
            SM[i,i-1], SM[i,i], SM[i,i+1] = S[i], -(S[i+1]+S[i]), S[i+1]

    return SM/(dz**2)

def pmodes(N,S,z,nn=10,dz=1.):
    """ Compute pressure modes

        nn: number of baroclinic modes

    """
    SM = stretching_matrix(N,S,dz)

    evals, evecs  = np.linalg.eig(-SM)
    isort = np.argsort(evals)
    evals=evals[isort][:nn+1]
    evecs = evecs[:,isort][:,:nn+1]

    evecs = normalize(evecs,z)

    return evals,evecs

def normalize(evecs,z):
    """ Normalize eigenvector to have unit
            L2 norm """

    ix,iy = evecs.shape
    for i in range(iy):
        int2 = integrate.trapz(evecs[:,i]**2,-z)/np.abs(z).max()
        evecs[:,i] = evecs[:,i]/sqrt(int2)

    return evecs

def wave_structure(a,z,k0,xmax=2*pi):
   """Compute wave structure """
   aabs = np.abs(a)
   aphase = np.arctan2(a.imag,a.real)

   x = np.linspace(0.,xmax,100)
   X,Z = np.meshgrid(x,z)
   aabs = aabs.repeat(x.size).reshape(X.shape)
   aphase = aphase.repeat(x.size).reshape(X.shape)
   A = aabs*np.cos(k0*X + aphase)
   return A, X, Z

def qg_stability(N2,ubar,z,k=1.,lat=50.,structure=True):

    f0 = sw.f(lat)
    beta = 2*7.29e-5*np.cos(lat*pi/180.)/6371.e3 

    dz = np.abs(z[1]-z[0])

    S = (f0**2)/N2
    L= stretching_matrix(z.size,S,dz)

    k2 = k**2

    L2 = L - np.eye(ubar.size)*k2
    U =  np.eye(ubar.size)*ubar
    Qy = np.eye(ubar.size)*(beta  - np.array( np.matrix(L)*np.matrix(ubar).T ) ) 

    L3 = L2.copy()
    for i in range(ubar.size):
        L3[i,:] = L2[i,:]*ubar[i]

    A = L3 + Qy
    B = L2.copy()

    evals,evecs = sp.linalg.eig(A,B)

    imax = evals.imag.argmax()
    eval_max = evals[imax]
    evec_max = evecs[:,imax]

    if structure:
        PSI, X, Z = wave_structure(evec_max,z,k)
        return eval_max,evec_max,PSI,X,Z
    else:
        return eval_max,evec_max

def qg_stability_2d(N2,ubar,vbar,z,k,l,lat,hx=0.,hy=0.,structure=False):

    f0 = sw.f(lat)
    beta = 2*7.29e-5*np.cos(lat*pi/180.)/6371.e3 

    # calculate surface shear
    ubarz, vbarz = ubar[0]-ubar[1], vbar[0]-vbar[1]

    dz = np.abs(z[1]-z[0])

    S = (f0**2)/N2
    L= stretching_matrix(z.size,S,dz)

    k2 = k**2 + l**2

    L2 = L - np.eye(ubar.size)*k2
    Qy = np.eye(ubar.size)*(beta  - np.array( np.matrix(L)*np.matrix(ubar).T ))
    Qx = np.eye(ubar.size)*np.array( np.matrix(L)*np.matrix(vbar).T )

    # bottom bc with topography
    Qx[-1,-1] += (f0/dz)*hx
    Qy[-1,-1] += (f0/dz)*hy 

    Q = k*Qy - l*Qx

    L3 = np.empty_like(L2)
    for i in range(ubar.size):
        L3[i,:] = L2[i,:]*(ubar[i]*k + vbar[i]*l)

    A = (L3 + Q)
    B = L2.copy()
  
    # append surface boundary condition
    #A = np.vstack([np.zeros_like(z),A])
    #B = np.vstack([np.zeros_like(z),B])

    #A = np.hstack([np.zeros(z),A])
    #B = np.hstack([np.zeros(z),B])

    #print(A.shape)
    #print(B.shape)

    # the upper boundary condition
    #A[0,0] = (ubar[0]*k+vbar[0]*l)
    #A[0,1] = -(ubar[0]*k+vbar[0]*l)
    #A[0,0] += -(k*ubarz + l*vbarz)
    #B[0,0], B[0,1] = dz,-dz 

    #print(A[0,:5])

    # bottom boundary condition satisfied
    # (may be should include topographic gradients)

    try:
        evals,evecs = sp.linalg.eig(A,B)
        imax = evals.imag.argmax()
        eval_max = evals[imax]
        evec_max = evecs[0:,imax]
    except:
        eval_max = np.nan + 1.j*np.nan
        evec_max = np.nan*z 
           
    #print(eval_max)

    if structure:
        PSI, X, Z = wave_structure(evec_max,z,k)
        return eval_max,evec_max,PSI,X,Z
    else:
        return eval_max,evec_max


def modal_projection(A,U):
    """ project U onto modes in columns of A """
    ATA = np.dot(A.T,A)
    ATU = np.dot(A.T,Up)
    return np.dot(np.linalg.inv(ATA),ATU)


if __name__ == "__main__":

    # now load data
    #cdrake = sp.io.loadmat('cDrake_avg.mat',squeeze_me=True,struct_as_record=False)
    cdrake = sp.io.loadmat('C09/cDrake_C09.mat',squeeze_me=True,struct_as_record=False)

    zv = np.array([   0,  100,  200,  300,  400,  500,  600,  700,  800,  900, 1000,
           1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000, 2100,
           2200, 2300, 2400, 2500, 2600, 2700, 2800, 2900, 3000, 3100, 3200,
           3300, 3400, 3500.])

    U = np.array(cdrake['vel'].u)
    V = np.array(cdrake['vel'].v)

    N2 = np.array(cdrake['density'].N2)
    zd = np.array(cdrake['density'].prs)

    zi = np.linspace(zv.min(),zv.max(),350)
    Ui = np.interp(zi,zv,U)
    Vi = np.interp(zi,zv,V)
    N2i = np.interp(zi,zd,N2)

    coefs = np.polyfit(zi, Ui, 10)
    Up = np.polyval(coefs, zi)
    coefs = np.polyfit(zi, Vi, 10)
    Vp = np.polyval(coefs, zi)

    #coefs = np.polyfit(zi, N2i, 10)
    #N2p = np.polyval(coefs, zi)

    #Le = np.linspace(750.,10.,100)
    #Le = np.linspace(750.,10.,30)
    #k = 2*pi/(Le*1.e3)

    #gr = []
    #for i in range(k.size):
    #    c,psi,PSI,X,Z = qg_stability(N2i,Up,-zi,k=k[i],lat=58)    
    #    gr.append(c.imag*k[i]) 

    #Le = np.linspace(1000.,1.,50)
    Le = np.logspace(3,5.,50)
    k = 2*pi/(Le*1.e3)

    k = np.hstack([-np.flipud(k),k])
    l = k.copy()

    f0 = sw.f(-58)
    S = f0**2/N2i
    N = N2i.size

    evals, evecs = pmodes(N,S,-zi,nn=10,dz=zi[2]-zi[1])

    xi = integrate.trapz(evecs[:,1]**3,zi)/zi.max()
    delta = .25*((np.sqrt(xi**2+4.)-xi)**2)

    # project Ui onto evecs
    #A = evecs
    #ATA = np.dot(A.T,A)
    #ATU = np.dot(A.T,Up)
    #alpha = np.dot(np.linalg.inv(ATA),ATU)

    au, av = modal_projection(evecs,Up), modal_projection(evecs,Vp)

    #l = 0

    #c,psi, A, B = qg_stability_2d(N2i,Up,Vp,-zi,k=k[10],l=l[5],lat=58)

    GR = np.zeros((k.size,l.size))
    for i in range(k.size):
    
       for j in range(l.size):

            print(i,j)

            c,psi = qg_stability_2d(N2i,Up,Vp,-zi,k=k[i],l=l[j],lat=58,hy=0.,hx=0.)
            GR[i,j] = c.imag

    np.savez('GR09.npz',k=k,l=l,GR=GR,Up=Up,Vp=Vp,N2i=N2i,zi=zi)


