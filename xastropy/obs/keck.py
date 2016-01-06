'''
#;+ 
#; NAME:
#; keck
#;    Version 1.1
#;
#; PURPOSE:  Simple scripts for Keck obs
#;   2015 Written by JXP
#;-
#;------------------------------------------------------------------------------
'''

# Import libraries
import numpy as np
from numpy.ma.core import MaskedConstant
import os, subprocess

from astropy.table import Table
from astropy.coordinates import SkyCoord
from astropy import units as u

from xastropy.xutils import xdebug as xdb
from xastropy.obs import finder as x_finder

# def wiki :: Generate a Wiki Table
# def starlist :: Generate a starlist file

#### ###############################
def wiki(targs, keys, fndr_pth=None, dbx_pth=None, outfil=None):
    """
    Generate a Wiki table for Keck observing.
    Should work for any of the Wiki pages

    Parameters:
    ----------
    targs: Table (RA, DEC keys required)
    keys: List
      List of keys to include in the Table + order
    fndr_pth: string
      Folder for finder charts
    dbx_pth: string
      Dropbox path for the finders

    Writes a file to disk that can be pasted into the Wiki
    """
    reload(x_finder)
    # Outfil
    if outfil is None:
        outfil = 'tmp_wiki.txt'
    f = open(outfil, 'w')

    # Finders?
    if not fndr_pth is None:
        if dbx_pth is None:
            dbx_pth = './'
            dbx_folder = './'
        else: # Expecting Public
            ifind = dbx_pth.find('Observing/')
            if ifind == -1:
                xdb.set_trace()
            else:
                dbx_folder = os.getenv('DROPBOX_DIR')+'/Public/'+dbx_pth[ifind:]
        #
        print('keck.wiki: Will copy finders to {:s}'.format(dbx_folder))
        # Get name tag
        name_tag = get_name_tag(targs.dtype.names)
        # Finders
        fndr_files = []
        for targ in targs:
            x_finder.main([targ[name_tag], targ['RA'], targ['DEC']], radec=1,
                          fpath=fndr_pth)
            # Copy? + Save
            nm = "".join(targ[name_tag].split()) 
            fil1 = fndr_pth+ nm + '.pdf'
            fil2 = dbx_folder
            subprocess.call(["cp", fil1, dbx_folder])
            fndr_files.append(dbx_pth+nm+'.pdf')
        
    # Header
    lin = '||' 
    for key in keys:
        lin = lin+str(key)+'||'
    if 'fndr_files' in locals():
        lin=lin+'finder||'
    f.write(str(lin+'\n'))
    
    # Targets
    for ii,targ in enumerate(targs):
        lin = '||' 
        for key in keys:
            lin = lin+str(targ[key])+'||'
        # Finder chart
        if 'fndr_files' in locals():
            lin = lin+'[['+fndr_files[ii]+'| pdf_finder]]||' # Lick formatting is different
        # Write
        f.write(str(lin+'\n'))

    # Close
    print('keck.wiki: Wrote {:s}'.format(outfil))
    f.close()

#### ###############################
def starlist(targs, outfil=None):
    '''
    Generates a Keck approved starlist 
    FORMAT:
      1-16: Name (max length = 15)
      Then: RA, DEC, EPOCH [NO COLONS!]

    Parameters:
    ----------
    targs: Table (targets with RA, DEC)
    outfil: string (None)
    '''
    # Init
    if outfil is None:
        outfil = 'starlist.txt'
    # Open
    f = open(outfil, 'w')

    # Name tag
    name_tag = get_name_tag(targs.dtype.names)

    # Loop
    for jj,targ in enumerate(targs):
        ras = targ['RA'].replace(':',' ')
        decs = targ['DEC'].replace(':',' ')
        if not decs[0] in ['+','-']:
            decs = '+'+decs
        # Name
        #print('name = {:s}, {:d}'.format(targ[name_tag],jj))
        #if jj == 7:
        #    xdb.set_trace()
        mask = []
        while type(targ[name_tag]) is MaskedConstant:
            mask.append(name_tag)
            name_tag = get_name_tag(targs.dtype.names,mask=mask)
        lin = "".join(targ[name_tag][0:4].split())+'_J'+ras.replace(' ','')[0:4]+decs.replace(' ','')[0:5]
        #xdb.set_trace()
        # RA
        lin = lin + '   ' + ras
        # DEC
        lin = lin + '  ' + decs
        # EPOCH
        lin = lin + '  2000.'
        # Write
        f.write(str(lin+'\n'))

    # Close
    print('keck.wiki: Wrote starlist -- {:s}'.format(outfil))
    f.close()

#
def get_name_tag(tbl_nms,mask=[None]):
    '''
    Find the name tag + return

    Parmaters:
    --------
    tbl_nms: List of names
    '''
    # Target name key
    name_tag = None
    for tag in ['Target', 'Name', 'NAME', 'QSO']:
        if tag in tbl_nms: 
            name_tag = tag
            if not name_tag in mask:
                break

    # Return
    return name_tag
