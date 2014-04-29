# Tests the Finder chart program
#   Requires "requests", "astropy", "aplpy", "PIL"
from xastropy.obs import x_finder as xf
from xastropy.obs import x_radec as x_r

def main():
    reload(x_r)
    reload(xf)
    # SDSS
    xf.main(['TST', '10:31:38.87', '+25:59:02.3'],radec=1, imsize=8.)#,BW=1)
    # DSS
    xf.main(['TST2', '10:31:38.87', '-25:59:02.3'],radec=1, DSS=1, imsize=8.,BW=1)
    return

if __name__ == '__main__':
    main()