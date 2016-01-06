"""
#;+ 
#; NAME:
#; fN.data
#;    Version 2.0
#;
#; PURPOSE:
#;    Module for fN data constraints
#;   12-Mar-2015 by JXP edited by Alix Feinsod
#;-
#;------------------------------------------------------------------------------
"""

from __future__ import print_function, absolute_import, division, unicode_literals

import numpy as np
import os, imp
from xastropy.xutils import xdebug as xdb
from xastropy.spec import abs_line, voigt
from xastropy.igm import tau_eff
#from xastropy.igm.fN.model import fN_Model

from astropy.io import fits

# Path for xastropy
xa_path = imp.find_module('xastropy')[1]

#class fN_Constraint(object):

class fN_Constraint(object):
    """A Class for fN constraints

    Attributes:
       fN_dtype: string
          Constraint type for the fN
           'fN' -- Standard f(N) evaluation
           'MFP' -- MFP
           'LLS' -- LLS incidence 
           'teff' -- tau effective
           'beta' -- slope constraint
       flavor: string
          Specific type of constraint
       comment: string
       ref: string
          Reference
       cosm: string
          Cosmology used (e.g. WMAP05)
       zeval: float
          Redshift where the constraint is evaluated
       data: dict
          Dictionary containing the constraints
    """

    # Initialize with type
    def __init__(self, fN_dtype, zeval=0., ref='', flavor=''):
        self.fN_dtype = fN_dtype  # Should probably check the choice
        self.zeval = zeval
        self.ref = ref
        self.flavor = flavor

    # Read from binary FITS table
    def from_fits_table(self, row):
        # Common items
        common = ['REF','COSM','TYPE','COMMENT']
        self.ref = row['REF']
        self.cosm = row['COSM']
        self.flavor = row['TYPE']
        self.comment = row['COMMENT']

        # zeval
        if 'ZEVAL' in row.array.names: self.zeval = row['ZEVAL']
        elif 'Z_LLS' in row.array.names: self.zeval = row['Z_LLS']
        elif 'Z_MFP' in row.array.names: self.zeval = row['Z_MFP']
        elif 'Z_TEFF' in row.array.names: self.zeval = row['Z_TEFF']
        else:
            raise ValueError('fN.data: No redshift info!')

        # zip the rest
        self.data = dict(zip(row.array.names,row))
        for item in common: self.data.pop(item) # No need to duplicate

    # Output
    def __repr__(self):
        return ('[%s: %s_%s z=%g, ref=%s]' %
                (self.__class__.__name__,
                 self.fN_dtype, self.flavor,
                 self.zeval, self.ref) )


# ###################### ###############
# ###################### ###############
# Read from ASCII file
def fN_data_from_ascii_file(infile):

    #makes new fN constraint with data type fN
    fNc = fN_Constraint('fN')
    ftype = fNc.fN_dtype.encode('ascii')
    fNc.fN_dtype = ftype
    fNc.ref=infile.encode('ascii')
    
    # Open file
    f = open(infile, 'r')

    # Read and ignore header lines
    firstline = f.readline()
    # get rid of newline /n symbol
    firstline =firstline.strip()
    #get zeval and DX from first line
    values = firstline.split()
    fNc.zeval = float(values[0])
    ZEVAL = float(values[0])
    DX = float(values[1])

    #declaration of variables
    BINS1 =[]
    BINS2 = []
    fn = []
    SIG_FN1 = []
    SIG_FN2 = []
    count = 0
    numlines=0

    # Loop over lines and extract info
    for line in f:
    	line = line.strip()
    	columns = line.split()
    	BINS1.append(float(columns[0]))
    	BINS2.append(float(columns[1]))
	fn.append(float(columns[2]))
	SIG_FN1.append(float(columns[3]))
	SIG_FN2.append(float(columns[3]))
	numlines +=1
	if (float(columns[0])!=0) or (float(columns[1])!=0) or (float(columns[2])!=0) or (float(columns[3])!=0):
	    count +=1
    f.close()

    NPT = int(count)
    bins = []
    bins.append(BINS1)
    bins.append(BINS2)
    sig_fn = []
    sig_fn.append(SIG_FN1)
    sig_fn.append(SIG_FN2)
    
    BINS = np.ndarray(shape=(2, numlines), dtype=float, buffer=np.array(bins))
    SIG_FN = np.ndarray(shape=(2, numlines), dtype=float, buffer=np.array(sig_fn))
    FN = np.ndarray(shape=(numlines,), dtype=float, buffer=np.array(fn))
    
    #makes array with names in ASCII not unicode
    arrayofnames = ['BINS','FN','SIG_FN','DX','NPT','ZEVAL']
    names = []
    for name in arrayofnames:
    	newname = name.encode('ascii')
    	names.append(newname)
    	
    values = [BINS,FN,SIG_FN,DX,NPT,ZEVAL]
    	
    fNc.data = dict(zip(names, values))
    
    return fNc

def fn_data_from_fits(fits_file):
    """ Build up a list of fN constraints from a multi-extension FITS file

    Parameters:
       fits_file: string
          Name of FITS file

    Returns:
       fN_list: list
          List of fN_Constraint objects

    JXP 07 Nov 2014
    """

    # List of constraints
    fN_cs = []

    # Read
    if isinstance(fits_file,list):
        for ifile in fits_file:
            tmp_cs = fn_data_from_fits(ifile)
            for cs in tmp_cs: fN_cs.append(cs)
    else:

        hdus = fits.open(fits_file)
        if len(hdus) == 1:
            raise ValueError('fN.data: Expecting a multi-extension fits file -- %s' % fits_file)
    
    
        # Loop through hdu
        for hdu in hdus[1:]:
            data = hdu.data
            # Get ftype
            if 'FN' in data.dtype.names: ftype = 'fN' # Standard f(N) data
            elif 'TAU_LIM' in data.dtype.names: ftype = 'LLS' # LLS survey
            elif 'MFP' in data.dtype.names: ftype = 'MFP' # MFP measurement
            elif 'TEFF' in data.dtype.names: ftype = 'teff' # tau effective (Lya)
            else: 
                raise ValueError('fN.data: Cannot figure out ftype')
    
            # Loop on the Table
            for row in data:
                fNc = fN_Constraint(ftype)
                fNc.from_fits_table(row)
                fN_cs.append(fNc)

    # Return
    return fN_cs

# Reproduce the main figure from P14 (data only)
def tst_fn_data(fN_model=None, model_two=None, data_list=None, outfil=None):
    """ Make a plot like the final figure from P14 

    Parameters:
       noshow: boolean (False)
          Show the plot?

    JXP 07 Nov 2014
    """

    import matplotlib as mpl
    mpl.rcParams['font.family'] = 'STIXGeneral-Regular' # Not for PDF
    mpl.rcParams['lines.linewidth'] = 2
    from matplotlib import pyplot as plt
    #from matplotlib.backends.backend_pdf import PdfPages

    # Output
    #if outfil != None:
    #    pp = PdfPages(outfil)

    #mpl.rcParams['font.family'] = 'stixgeneral'  # For PDF

    # fN data
    #fn_file = os.environ.get('XIDL_DIR')+'IGM/fN_empirical/fn_constraints_z2.5_vanilla.fits'
    #k13r13_file = os.environ.get('XIDL_DIR')+'IGM/fN_empirical/fn_constraints_K13R13_vanilla.fits'
    #n12_file = os.environ.get('XIDL_DIR')+'IGM/fN_empirical/fn_constraints_N12_vanilla.fits'
    fn_file = xa_path+'/igm/fN/fn_constraints_z2.5_vanilla.fits'
    k13r13_file = xa_path+'/igm/fN/fn_constraints_K13R13_vanilla.fits'
    n12_file = xa_path+'/igm/fN/fn_constraints_N12_vanilla.fits'
    all_fN_cs = fn_data_from_fits([fn_file,k13r13_file, n12_file])
    #ascii_file = xa_path+'/igm/fN/asciidatan12'
    #ascii_data = fN_data_from_ascii_file(ascii_file)
    #all_fN_cs.append(ascii_data)
    
    # Remove K12
    #data_list = ['K13R13','OPB07', 'N12']
    #outfil = 'tmp.png'
    if data_list is None:
        fN_cs = [fN_c for fN_c in all_fN_cs if ((fN_c.ref != 'K02') & (fN_c.ref != 'PW09'))]
    else:
        fN_cs = [fN_c for fN_c in all_fN_cs if fN_c.ref in data_list]
    fN_dtype = [fc.fN_dtype for fc in fN_cs]

    fig = plt.figure(figsize=(8, 5))
    fig.clf()
    main = fig.add_axes( [0.1, 0.1, 0.8, 0.8] ) # xypos, xy-size

    # f(N) data
    main.set_ylabel(r'$\log f(N_{\rm HI})$')
    main.set_xlabel(r'$\log N_{\rm HI}$')
    main.set_ylim(-25., -9)

    for fN_c in fN_cs: 
        if fN_c.fN_dtype == 'fN':
            # Length
            ip = range(fN_c.data['NPT'])
            #xdb.set_trace()
            val = np.where(fN_c.data['FN'][ip] > -90)[0]
            #xdb.set_trace()
            if len(val) > 0:
                #xdb.set_trace()
                ipv = np.array(ip)[val]
                xval = np.median(fN_c.data['BINS'][:,ipv],0)
                xerror = [ fN_c.data['BINS'][1,ipv]-xval, xval-fN_c.data['BINS'][0,ipv] ]
                yerror = [ fN_c.data['SIG_FN'][1,ipv], fN_c.data['SIG_FN'][0,ipv] ] # Inverted!
                main.errorbar(xval, fN_c.data['FN'][ipv], xerr=xerror, yerr=yerror, fmt='o',
                             label=fN_c.ref,capthick=2)
    main.legend(loc='lower left', numpoints=1)

    # Model?
    #print(fN_model.param)
    if fN_model is not None: 
        xplt = 12.01 + 0.01*np.arange(1100)
        yplt = fN_model.eval(xplt, 2.4)
        main.plot(xplt,yplt,'-',color='black')
        print(xplt[0],yplt[0])
    if model_two is not None: 
        xplt = 12.01 + 0.01*np.arange(1100)
        yplt = model_two.eval(xplt, 2.4)
        main.plot(xplt,yplt,'-',color='gray')
        

    #xdb.set_trace()

    # Extras
    #mpl.rcParams['lines.capthick'] = 2

    inset = fig.add_axes( [0.55, 0.6, 0.25, 0.25] ) # xypos, xy-size
    inset.set_ylabel('Value') # LHS
    inset.xaxis.set_major_locator(plt.FixedLocator(range(5)))
    #lbl1 = r'$\tau_{\rm eff}^{\rm Ly\alpha}'
    inset.xaxis.set_major_formatter(plt.FixedFormatter(['',r'$\tau_{\rm eff}^{\rm Ly\alpha}$',
                                                        r'$\ell(X)_{\rm LLS}$',
                                                        r'$\lambda_{\rm mfp}^{912}$', '']))
    inset.set_ylim(0., 0.6)

    ## #######
    # tau_eff
    flg_teff = 1
    try:
        itau = fN_dtype.index('teff') # Passes back the first one
    except:
        #raise ValueError('fN.data: Missing teff type')
        flg_teff = 0    
    
    #xdb.set_trace()
    if flg_teff: 
        teff=float(fN_cs[itau].data['TEFF'])
        D_A = 1. - np.exp(-1. * teff)
        SIGDA_LIMIT = 0.1  # Allows for systemtics and b-value uncertainty
        sig_teff = np.max([fN_cs[itau].data['SIG_TEFF'], (SIGDA_LIMIT*teff)])
        # Plot
        inset.errorbar(1, teff, sig_teff, fmt='_', capthick=2)
        # Model
        if fN_model != None: 
            model_teff = tau_eff.ew_teff_lyman(1215.6701*(1+fN_cs[itau].zeval), fN_cs[itau].zeval+0.1,
                                        fN_model, NHI_MIN=fN_cs[itau].data['NHI_MNX'][0],
                                        NHI_MAX=fN_cs[itau].data['NHI_MNX'][1])
            inset.plot(1, model_teff, 'ko')
        #xdb.set_trace()

    ## #######
    # LLS constraint
    flg_LLS = 1    
    try:
        iLLS = fN_dtype.index('LLS') # Passes back the first one
    except:
        #raise ValueError('fN.data: Missing LLS type')
        flg_LLS = 0    
    if flg_LLS: 
        inset.errorbar(2, fN_cs[iLLS].data['LX'], yerr=fN_cs[iLLS].data['SIG_LX'],
                    fmt='_', capthick=2)
        # Model
        if fN_model != None:
            lX = fN_model.calc_lox(fN_cs[iLLS].zeval,
                                17.19+np.log10(fN_cs[iLLS].data['TAU_LIM']), 22.) 
            inset.plot(2, lX, 'ko')

    ## #######
    # MFP constraint
    flg_MFP = 1
    try:
        iMFP = fN_dtype.index('MFP') # Passes back the first one
    except:
        #raise ValueError('fN.data: Missing MFP type')
        flg_MFP = 0

    if flg_MFP:
        inset2 = inset.twinx()
        inset2.errorbar(3, fN_cs[iMFP].data['MFP'], yerr=fN_cs[iMFP].data['SIG_MFP'], 
                    fmt='_', capthick=2)
        inset2.set_xlim(0,4)
        inset2.set_ylim(0,350)
        inset2.set_ylabel('(Mpc)')

        # Model
        if fN_model != None:
            #fN_model.zmnx = (0.1, 20.) # Reset for MFP calculation
            mfp = fN_model.mfp(fN_cs[iMFP].zeval)
            inset2.plot(3, mfp, 'ko')

    # Show
    if outfil != None:
        plt.savefig(outfil,bbox_inches='tight')
    else: 
        plt.show()
        
    
## #################################    
## #################################    
## TESTING
## #################################    
if __name__ == '__main__':

    # Read a dataset
    fn_file = xa_path+'/igm/fN/fn_constraints_z2.5_vanilla.fits'
    k13r13_file = xa_path+'/igm/fN/fn_constraints_K13R13_vanilla.fits'
    n12_file = xa_path+'/igm/fN/fn_constraints_N12_vanilla.fits'
    all_fN_cs = fn_data_from_fits([fn_file, k13r13_file, n12_file])
    #ascii_file = xa_path+'/igm/fN/asciidatan12'
    #ascii_data = fN_data_from_ascii_file(ascii_file)
    #all_fN_cs.append(ascii_data)
    
    print(all_fN_cs)
    for fN_c in all_fN_cs: print(fN_c)

    # Plot
    tst_fn_data()
    xdb.set_trace()
    print('fN.data: All done testing..')

