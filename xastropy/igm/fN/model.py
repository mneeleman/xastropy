"""
#;+ 
#; NAME:
#; fN.model
#;    Version 1.0
#;
#; PURPOSE:
#;    Module for calculating fN models
#;   07-Nov-2014 by JXP
#;-
#;------------------------------------------------------------------------------
"""

from __future__ import print_function, absolute_import, division, unicode_literals
import numpy as np
import os, pickle, imp
from scipy import interpolate as scii

from xastropy.xutils import xdebug as xdb
from xastropy.spec import abs_line, voigt
from xastropy.stats import mcmc
from xastropy.igm import igm_utils as igmu
from xastropy.atomic import ionization as xai

from astropy.io import fits
from astropy.utils.misc import isiterable
from astropy import units as u

# Path for xastropy
xa_path = imp.find_module('xastropy')[1]

class fN_Model(object):
    """A Class for fN models

    Attributes:
       fN_mtype: string
          Model type for the fN
           'plaw' -- Power Laws
           'Hspline' -- Hermite monotonic spline 
           'Gamma' -- Gamma function [Following Inoue+14]
       zmnx: tuple
          Redshift range where this model applies (zmin,zmax)
       npivot: int 
          Number f pivots
       pivots: array 
          log NHI values for the pivots
       zpivot: float (2.4)
          Pivot for redshift evolution
       gamma: float (1.5)
          Power law for dN/dX
    """

    # Initialize with type
    def __init__(self, fN_mtype, zmnx=(0.,0.), pivots=[0.],
                 param=None, zpivot=2.4, gamma=1.5):
        self.fN_mtype = fN_mtype  # Should probably check the choice

        if fN_mtype == 'Gamma':  # I14 values
            zmnx = (0., 10.)
            param = [ [12., 23., 21., 28.], # Common
                      [1.75828e8, 9.62288e-4],             # Bi values
                      [500, 1.7, 1.2, 4.7, 0.2, 2.7, 4.5], # LAF
                      [1.1, 0.9, 2.0, 1.0, 2.0] ] # DLA
        self.zmnx = zmnx  

        # Pivots
        if pivots == None: self.pivots = np.zeros(2)
        else: self.pivots = pivots
        self.npivot = len(pivots)

        # Param
        if param is None:
            self.param = np.zeros(self.npivot)
        else:
            self.param = param
            #if np.amax(self.pivots) < 99.:
            #    self.pivots.append(99.)
            #    self.param = np.append(self.param,-30.)
            # Init
            if fN_mtype == 'Hspline':
                self.model = scii.PchipInterpolator(self.pivots, self.param)

        # Redshift (needs updating)
        self.zpivot = zpivot
        self.gamma = gamma

    ##
    # Update parameters (mainly used in the MCMC)
    def upd_param(self, parm):
        """ Update parameters (mainly used in the MCMC)
           Updates other things as needed
        """
        if self.fN_mtype == 'Hspline':
            self.param = parm
            # Need to update the model too
            self.model = scii.PchipInterpolator(self.pivots, self.param)
        elif self.fN_mtype == 'Gamma':
            if len(parm) == 4: # A,beta for LAF and A,beta for DLA
                self.param[2][0] = parm[0]
                self.param[2][1] = parm[1]
                self.param[3][0] = parm[2]
                self.param[3][1] = parm[3]
            else:
                raise ValueError('fN/model: Not ready for {:d} parameters'.format(len(param)))

    ##
    # l(X)
    def calc_lox(self, z, NHI_min, NHI_max=None, neval=10000, cumul=False):
        """ Calculate l(X) over an N_HI interval

        Parameters:
        z: float
          Redshift for evaluation
        NHI_min: float
          minimum NHI value
        NHI_max: float (Infinity)
          maximum NHI value for evaluation
        neval: int (10000)
          Discretization parameter
        cumul: boolean (False)
          Return a cumulative array?

        Returns:
        lX: float
          l(X) value

        JXP 10 Nov 2014
        """
        # Initial
        if NHI_max==None:
            NHI_max = 23.
            infinity=True
        else: infinity=False

        try:
            nz = len(z)
        except:
            nz=1
            z = np.array([z])

        # Brute force (should be good to ~0.5%)
        lgNHI = NHI_min + (NHI_max-NHI_min)*np.arange(neval)/(neval-1.)
        dlgN = lgNHI[1]-lgNHI[0]

        # Evaluate f(N,X)
        lgfNX = self.eval(lgNHI, z)
        #xdb.set_trace()

        # Sum
        lX = np.zeros(nz)
        for ii in range(nz): 
            lX[ii] = np.sum(10.**(lgfNX[:,ii]+lgNHI)) * dlgN * np.log(10.)
        if cumul==True: 
            if nz > 1: #; Have not modified this yet
                raise ValueError('fN.model: Not ready for this model type %s' % self.fN_mtype)
            cum_sum = np.cumsum(10.**(lgfNX[:,ii]+lgNHI)) * dlgN * np.log(10.)
        #xdb.set_trace()

        # Infinity?
        if infinity is True:
            # This is risky...
            # Best to cut it off
            xdb.set_trace()
            neval2 = 1000L
            lgNHI2 = NHI_max + (99.-NHI_max)*np.arange(neval2)/(neval2-1.)
            dlgN = lgNHI2[1]-lgNHI2[0]
            lgfNX = np.zeros((neval2,nz))
            lX2 = np.zeros(nz)
            for ii in range(nz):
                lgfNX[:,ii] = self.eval(lgNHI2, z[ii]).flatten()
                lX2[ii] = np.sum(10.**(lgfNX[:,ii]+lgNHI2)) * dlgN * np.log(10.)
                xdb.set_trace()
            # 
            lX = lX + lX2

        # Return
        if nz==1:
            lX = lX[0]
        if cumul==True:
            return lX, cum_sum, lgNHI
        else:
            return lX
    ##
    # Evaluate
    def eval(self, NHI, z, vel_array=None, cosmo=None):
        """ Evaluate the model at a set of NHI values

        Parameters:
        NHI: array
          NHI values
        z: float or array
          Redshift for evaluation
        vel_array: array
          Velocities relative to z

        Returns:
        log_fNX: float, array, or 2D array
          f(NHI,X)[z] values
          Float if given one NHI,z value each. Otherwise 2D array
          If 2D, it is [NHI,z] on the axes

        JXP 07 Nov 2014
        """
        # Exception checking?

        # Imports
        from astropy import constants as const

        # Tuple?
        if isinstance(NHI,tuple): # All values packed into NHI parameter
            z = NHI[1]
            NHI = NHI[0]
            flg_1D = 1
        else:  # NHI and z separate
            flg_1D = 0

        # NHI
        if isiterable(NHI): NHI = np.array(NHI) # Insist on array
        else: NHI = np.array([NHI]) 
        lenNHI = len(NHI)

        # Redshift 
        if vel_array is not None:
            z_val = z + (1+z) * vel_array/(const.c.cgs.value/1e5)
        else: z_val = z
        if isiterable(z_val): z_val = np.array(z_val)
        else: z_val = np.array([z_val])
        lenz = len(z_val)

    
        # Check on zmnx
        bad = np.where( (z_val < self.zmnx[0]) | (z_val > self.zmnx[1]))[0]
        if len(bad) > 0:
            raise ValueError(
                'fN.model.eval: z={:g} not within self.zmnx={:g},{:g}'.format(z_val[bad[0]],*(self.zmnx)))

        if self.fN_mtype == 'Hspline': 
            # Evaluate without z dependence
            log_fNX = self.model.__call__(NHI)


            # Evaluate
            #xdb.set_trace()
            if (not isiterable(z_val)) | (flg_1D == 1):  # scalar or 1D array wanted
                log_fNX += self.gamma * np.log10((1+z_val)/(1+self.zpivot))
            else:
                # Matrix algebra to speed things up
                lgNHI_grid = np.outer(log_fNX, np.ones(len(z_val)))
                lenfX = len(log_fNX)
                #xdb.set_trace()
                # 
                z_grid1 = 10**( np.outer(np.ones(lenfX)*self.gamma,
                                        np.log10(1+z_val)) )  #; (1+z)^gamma
                z_grid2 = np.outer( np.ones(lenfX)*((1./(1+self.zpivot))**self.gamma), 
                            np.ones(len(z_val))  )
                log_fNX = lgNHI_grid + np.log10(z_grid1*z_grid2) 

        # Gamma function (e.g. Inoue+14)
        elif self.fN_mtype == 'Gamma': 
            # Setup the parameters
            Nl, Nu, Nc, bval = self.param[0]

            # gNHI
            Bi = self.param[1]
            ncomp = len(Bi)
            log_gN = np.zeros((lenNHI,ncomp))
            beta = [item[1] for item in self.param[2:]] 
            for kk in range(ncomp):
                #xdb.set_trace()
                log_gN[:,kk] += (np.log10(Bi[kk]) + NHI*(-1 * beta[kk])
                                + (-1. * 10.**(NHI-Nc) / np.log(10) ) ) # log10 [ exp(-NHI/Nc) ]
            # f(z)
            fz = np.zeros((lenz,2))
            # Loop on NHI
            for kk in range(ncomp):
                if kk == 0: # LyaF
                    zcuts = self.param[2][2:4]
                    gamma = self.param[2][4:]
                else:       # DLA
                    zcuts = [self.param[3][2]]
                    gamma = self.param[3][3:]
                zcuts = [0] + list(zcuts) + [999.]
                Aval = self.param[2+kk][0]
                # Cut on z
                for ii in range(1,len(zcuts)):
                    izcut = np.where( (z_val < zcuts[ii]) & (z_val > zcuts[ii-1]) )[0]
                    liz = len(izcut)
                    # Evaluate (at last!)
                    #xdb.set_trace()
                    if (ii <=2) & (liz > 0):
                        fz[izcut,kk] = Aval * ( (1+z_val[izcut]) / (1+zcuts[1]) )**gamma[ii-1]
                    elif (ii == 3) & (liz > 0):
                        fz[izcut,kk] = Aval * ( ( (1+zcuts[2]) / (1+zcuts[1]) )**gamma[ii-2] * 
                                                    ((1+z_val[izcut]) / (1+zcuts[2]) )**gamma[ii-1] )
#                            else: 
#                                raise ValueError('fN.model.eval: Should not get here')
            # dX/dz
            dXdz = igmu.cosm_xz(z_val, cosmo=cosmo, flg=1) 

            # Final steps
            if flg_1D == 1: # 
                #xdb.set_trace()
                fnX = np.sum(fz * 10.**log_gN, 1) / dXdz
                log_fNX = np.log10(fnX)
            else: 
                # Generate the matrix
                fnz = np.zeros((lenNHI,lenz))
                for kk in range(ncomp):
                    fnz += np.outer(10.**log_gN[:,kk],fz[:,kk])
                # Finish up
                log_fNX = np.log10(fnz) - np.log10( np.outer(np.ones(lenNHI), dXdz) )
        else: 
            raise ValueError('fN.model: Not ready for this model type {:%s}'.format(self.fN_mtype))

        # Return
        if (lenNHI + lenz) == 2:
            return log_fNX.flatten()[0] # scalar
        else: return log_fNX
    ##
    # Mean Free Path
    def mfp(self, zem, neval=5000, cosmo=None, zmin=0.6):
        """ Calculate teff_LL 
        Effective opacity from LL absorption at z912 from zem

        Parameters:
        zem: float
          Redshift of source
        cosmo: astropy.cosmology (None)
          Cosmological model to adopt (as needed)
        neval: int (5000)
          Discretization parameter
        zmin: float (0.5)
          Minimum redshift in the calculation

        Returns:
        mfp : float
          Mean free path from zem (physical Mpc)

        JXP 11 Nov 2014
        """
        # Imports
        from astropy import constants as const
        from astropy import cosmology 

        # Cosmology
        if cosmo == None:
            cosmo = cosmology.core.FlatLambdaCDM(70., 0.3)

        # Calculate teff
        zval, teff_LL = self.teff_ll(zmin, zem, N_eval=neval, cosmo=cosmo)

        # Find tau=1
        imn = np.argmin( np.fabs(teff_LL-1.) )
        if np.fabs(teff_LL[imn]-1.) > 0.02:
            raise ValueError('fN.model.mfp: teff_LL too far from unity')

        # MFP
        mfp = np.fabs( cosmo.lookback_distance(zval[imn]) -
                        cosmo.lookback_distance(zem) ) # Mpc
        #xdb.set_trace()
        # Return
        return mfp
        

    ##
    # teff_LL
    def teff_ll(self, z912, zem, N_eval=5000, cosmo=None):
        """ Calculate teff_LL 
        Effective opacity from LL absorption at z912 from zem

        Parameters:
        z912: float
          Redshift for evaluation
        zem: float
          Redshift of source
        cosmo: astropy.cosmology (None)
          Cosmological model to adopt (as needed)
        N_eval: int (5000)
          Discretization parameter

        Returns:
        zval, teff_LL: array
          z values and Effective opacity from LL absorption from z912 to zem

        JXP 10 Nov 2014
        """
        # Imports
        from astropy import constants as const

        # NHI array
        lgNval = 11.5 + 10.5*np.arange(N_eval)/(N_eval-1.) #; This is base 10 [Max at 22]
        dlgN = lgNval[1]-lgNval[0]
        Nval = 10.**lgNval

        #; z array
        zval = z912 + (zem-z912)*np.arange(N_eval)/(N_eval-1.)
        dz = np.fabs(zval[1]-zval[0])

        teff_LL = np.zeros(N_eval)

        # dXdz
        dXdz = igmu.cosm_xz(zval, cosmo=cosmo, flg=1) 
        #if keyword_set(FNZ) then dXdz = replicate(1.,N_eval)

        # Evaluate f(N,X)
        velo = (zval-zem)/(1+zem) * (const.c.cgs.value/1e5) # Kludge for eval [km/s]

        log_fnX = self.eval(lgNval, zem, vel_array=velo)  
        log_fnz = log_fnX + np.outer(np.ones(N_eval), np.log10(dXdz))

        # Evaluate tau(z,N)
        teff_engy = (const.Ryd.to(u.eV,equivalencies=u.spectral()) /
                     ((1+zval)/(1+zem)) )
        sigma_z = xai.photo_cross(1,1,teff_engy)
        #xdb.set_trace()
        #sigma_z = teff_cross * ((1+zval)/(1+zem))**(2.75)  # Not exact but close
        tau_zN = np.outer(Nval, sigma_z)

        # Integrand
        intg = 10.**(log_fnz) * (1. - np.exp(-1.*tau_zN))

        # Sum
        sumz_first = False
        if sumz_first == False:
            #; Sum in N first
            N_summed = np.sum(intg * np.outer(Nval, np.ones(N_eval)),  0) * dlgN * np.log(10.)
            #xdb.set_trace()
            # Sum in z
            teff_LL = (np.cumsum(N_summed[::-1]))[::-1] * dz 
        #xdb.set_trace()

        # Debug
        debug=False
        if debug == True:
            #        x_splot, lgNval, alog10(10.d^(log_fnX) * dxdz * dz * Nval), /bloc
            #        x_splot, lgNval, total(10.d^(log_fnX) * dxdz * dz * Nval,/cumul) * dlgN * alog(10.) / teff_lyman[qq], /bloc
            #     printcol, lgnval, log_fnx, dz,  alog10(10.d^(log_fnX) * dxdz * dz * Nval)
            #     writecol, 'debug_file'+strtrim(qq,2)+'.dat', $
            #               lgNval, restEW, log_fnX
            xdb.set_trace()
        # Return
        return zval, teff_LL

    ##
    # Output
    def __repr__(self):
        return ('[%s: %s zmnx=(%g,%g)]' %
                (self.__class__.__name__,
                 self.fN_mtype, self.zmnx[0], self.zmnx[1] ) )

#########
def default_model(recalc=False, pckl_fil=None, use_mcmc=False, write=False):
    """
    Pass back a default fN_model from Prochaska+13
      Tested against XIDL code by JXP on 09 Nov 2014

    Parameters:
    recalc: boolean (False)
      Recalucate the default model
    use_mcmc: boolean (False)
      Use the MCMC chain to generate the model
    write: boolean (False)
      Write out the model
    """
    if pckl_fil==None:
        pckl_fil = xa_path+'/igm/fN/fN_model_P13.p'

    if recalc is True:
        
        if use_mcmc == True:
            # MCMC Analysis
            chain_file = (os.environ.get('DROPBOX_DIR')+
                        'IGM/fN/MCMC/mcmc_spline_k13r13o13n12_8.fits.gz')
            outp = mcmc.chain_stats(chain_file)
    
            # Build a model
            NHI_pivots = [12., 15., 17.0, 18.0, 20.0, 21., 21.5, 22.]
            fN_model = fN_Model('Hspline', zmnx=(0.5,3.0),
                            pivots=NHI_pivots, param=outp['best_p'])
        else:
            # Input the f(N) at z=2.4
            fN_file = (os.environ.get('DROPBOX_DIR')+
                        'IGM/fN/fN_spline_z24.fits.gz')
            hdu = fits.open(fN_file)
            fN_data = hdu[1].data
            #xdb.set_trace()
            # Instantiate
            fN_model = fN_Model('Hspline', zmnx=(0.5,3.0),
                            pivots=np.array(fN_data['LGN']).flatten(),
                            param=np.array(fN_data['FN']).flatten())
        # Write
        if write is True:
            print('default_model: Writing %s' % pckl_fil)
            pickle.dump( fN_model, open( pckl_fil, "wb" ), -1)
    else: fN_model = pickle.load( open( pckl_fil, "rb" ) )
        
    # Return
    return fN_model







## #################################    
## #################################    
## TESTING
## #################################    
if __name__ == '__main__':

    from matplotlib import pyplot as plt
    
    from xastropy.igm.fN import data as fN_data
    from xastropy.igm.fN import model as xifm

    flg_test = 0 
    flg_test += 2**2 # Standard model
    #flg_test += 2**3 # l(X)
    #flg_test += 64 # Akio
    #flg_test = 0 + 64
    
    if (flg_test % 2) == 1:
        # MCMC Analysis
        chain_file = os.environ.get('DROPBOX_DIR')+'IGM/fN/MCMC/mcmc_spline_k13r13o13n12_8.fits.gz'
        outp = mcmc.chain_stats(chain_file)

        # Build a model
        NHI_pivots = [12., 15., 17.0, 18.0, 20.0, 21., 21.5, 22.]
        fN_model = xifm.fN_Model('Hspline', zmnx=(0.5,3.0),
                            pivots=NHI_pivots, param=outp['best_p'])
        #xdb.set_trace()
        print(fN_model)

    # Compare default against P+13
    if (flg_test % 4) >= 2:
        fN_model = xifm.default_model()
        p13_file = (os.environ.get('DROPBOX_DIR')+'IGM/fN/fN_spline_z24.fits.gz')
        hdu = fits.open(p13_file)
        p13_data = hdu[1].data
        
        plt.clf()
        plt.scatter(p13_data['LGN'],p13_data['FN'])
        #plt.plot(p13_data['LGN'],p13_data['FN'], '-')
        xplt = np.linspace(12., 22, 10000)
        yplt = fN_model.eval(2.4,xplt)
        plt.plot(xplt, yplt, '-', color='red')
        #plt.plot(xplt, yplt, '-')
        plt.show()
        #xdb.set_trace()

    # Reproduce the main figure from P14
    # Plot with Data
    if (flg_test % 2**3) >= 2**2:
        fN_model = xifm.default_model()
        fN_data.tst_fn_data(fN_model=fN_model)

    # Check l(X)
    if (flg_test % 16) >= 8:
        fN_model = xifm.default_model()
        lX = fN_model.calc_lox(2.4, 17.19+np.log10(2.), 23.) 
        print('l(X) = %g' % lX)

    # Check teff_LL
    if (flg_test % 32) >= 16:
        fN_model = xifm.default_model()
        zval,teff_LL = fN_model.teff_ll(0.5, 2.45)
        xdb.xplot(zval,teff_LL)#,xlabel='z', ylabel=r'$\tau_{\rm LL}$')

    # Check MFP
    if (flg_test % 64) >= 32:
        fN_model = xifm.default_model()
        z = 2.44
        mfp = fN_model.mfp(z)
        print('MFP at z={:g} is {:g} Mpc'.format(z,mfp.value))

    # Check Inoue+14
    if (flg_test % 2**7) >= 2**6:
        print('Testing Akio Model')
        fN_model = fN_Model('Gamma')
        NHI = [12.,14.,17.,21.]
        z = 2.5
        dXdz = igmu.cosm_xz(z, flg=1) 
        # From Akio
          # 12 1.2e-9
          # 14 4.9e-13
          # 17 4.6e-18
          # 21 6.7e-23

        # Test 1D
        tstNz = ( NHI, [z for ii in enumerate(NHI)] )
        log_fNX = fN_model.eval(tstNz,0.)
        #xdb.set_trace()
        for kk,iNHI in enumerate(NHI):
            print('I+14 At z={:g} and NHI={:g}, f(N,z) = {:g}'.format(z,iNHI,10.**log_fNX[kk] * dXdz))
    
        # Test matrix
        log_fNX = fN_model.eval(NHI,z)
        for iNHI in NHI:
            print('I+14 At z={:g} and NHI={:g}, f(N,z) = {:g}'.format(z,iNHI,10.**log_fNX[NHI.index(iNHI),0] * dXdz))

        # Plot
        JXP_model = xifm.default_model()
        fN_data.tst_fn_data(fN_model=fN_model, model_two=JXP_model)
