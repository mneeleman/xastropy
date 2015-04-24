"""
#;+ 
#; NAME:
#; cgm.core 
#;    Version 1.0
#;
#; PURPOSE:
#;    Module for core routines of CGM analysis
#;   29-Nov-2014 by JXP
#;-
#;------------------------------------------------------------------------------
"""
from __future__ import print_function, absolute_import, division, unicode_literals

import numpy as np
import os, imp
from astropy.io import fits, ascii
from astropy import units as u 
from astropy.coordinates import SkyCoord
#from astropy import constants as const

from xastropy.igm.abs_sys.abssys_utils import Absline_System
from xastropy.igm.abs_sys import abs_survey as xaa
reload(xaa)
from xastropy.igm.abs_sys.abs_survey import Absline_Survey
from xastropy.galaxy.core import Galaxy

from xastropy.atomic.elements import ELEMENTS
from xastropy.xutils import xdebug as xdb

from astropy.utils.misc import isiterable

# Path for xastropy
#xa_path = imp.find_module('xastropy')[1]

########################## ##########################
########################## ##########################
class CGM_Abs(Absline_System):
    """ Class for CGM absorption system

    Attributes
    ----------
    rho: float
      Impact parameter (u.kpc)

    JXP on 29 Nov 2014
    """

    # Initialize 
    def __init__(self, ras='02 26 14.5', decs='+00 15 29.8', cosmo=None,
                 g_ras='02 26 12.98', g_decs='+00 15 29.1', zgal=0.227):

        # Absorption system
        Absline_System.__init__(self,'CGM')

        self.coord = SkyCoord(ras, decs, 'icrs', unit=(u.hour, u.deg))
        # Name
        self.name = ('J'+
                    self.coord.ra.to_string(unit=u.hour,sep='',pad=True)+
                    self.coord.dec.to_string(sep='',pad=True,alwayssign=True))
        # Galaxy
        self.galaxy = Galaxy(ra=g_ras, dec=g_decs)
        self.galaxy.z = zgal

        # Calcualte rho
        if cosmo is None:
            from astropy.cosmology import WMAP9 as cosmo
            print('cgm.core: Using WMAP9 cosmology')
        ang_sep = self.coord.separation(self.galaxy.coord).to('arcmin')
        kpc_amin = cosmo.kpc_comoving_per_arcmin( self.galaxy.z ) # kpc per arcmin
        self.rho = ang_sep * kpc_amin / (1+self.galaxy.z) # Physical
        #xdb.set_trace()


    def print_abs_type(self):
        """"Return a string representing the type of vehicle this is."""
        return 'CGM'

    # Output
    def __repr__(self):
        return ('[{:s}: {:s} {:s}, zgal={:g}, rho={:g}, NHI={:g}, M/H={:g}]'.format(
                self.__class__.__name__,
                 self.coord.ra.to_string(unit=u.hour,sep=':',pad=True),
                 self.coord.dec.to_string(sep=':',pad=True),
                 self.galaxy.z, self.rho, self.NHI, self.MH))

# Class for CGM Survey
class CGM_Abs_Survey(Absline_Survey):
    """A CGM Survey class in absorption

    Attributes:
    """
    # Initialize with a .dat file
    def __init__(self, tree=None):

        from xastropy.igm.abs_sys.abs_survey import Absline_Survey

        # Generate with type
        Absline_Survey.__init__(self, '', abs_type='CGM', tree=tree)

        # Galaxies
        self.galaxies = []

#dct['megastruct']['ion'][2]['lognion'][2][6]

# ###################### #######################
# Testing
if __name__ == '__main__':

    # Initialize
    tmp = CGM_Abs()
    print(tmp)

    tmp2 = CGM_Abs_Survey()
    print(tmp2)
