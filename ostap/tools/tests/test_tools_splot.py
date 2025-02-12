#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file ostap/tools/tests/test_tools_splot.py
# Test sPlotting macheinery (outside of RooFit)
# - fill histogram from the TTree 
# - fit the histogram
# - make sPlot
# - write sPlot results into oroigin Ttree
# ============================================================================= 
""" Test sPlotting macheinery (outside of RooFit)
- fill histoigram from TTree 
- fit the histogram
- make sPlot
- write sPlot results into oroigin Ttree
"""
# ============================================================================= 
from   __future__               import print_function
import ostap.trees.trees
import ostap.histos.histos
from   ostap.core.core          import Ostap, hID 
from   ostap.trees.data         import Data
from   ostap.utils.timing       import timing 
from   ostap.utils.progress_bar import progress_bar
from   ostap.fitting.variables  import FIXVAR 
from   ostap.tools.splot        import sPlot1D
from   ostap.plotting.canvas    import use_canvas 
from   ostap.utils.utils        import wait
import ostap.fitting.models     as     Models 
import ostap.io.zipshelve       as     DBASE 
import ROOT, math, random, array  
# ============================================================================= 
# logging 
# =============================================================================
from ostap.logger.logger import getLogger
if '__main__' ==  __name__ : logger = getLogger ( 'test_tools_splot' )
else                       : logger = getLogger ( __name__           )
# =============================================================================
## create a file with tree 
def create_tree ( fname , nentries = 1000 ) :
    """Create a file with a tree
    >>> create_tree ( 'file.root' ,  1000 ) 
    """
    
    import ROOT, random 
    import ostap.io.root_file
    
    from array import array 
    var1 = array ( 'd', [ 0 ] )
    var2 = array ( 'd', [ 0 ] )
    var3 = array ( 'd', [ 0 ] )
    
    from ostap.core.core import ROOTCWD

    with ROOTCWD() , ROOT.TFile.Open( fname , 'new' ) as root_file:
        root_file.cd () 
        tree = ROOT.TTree ( 'S','tree' )
        tree.SetDirectory ( root_file  ) 
        tree.Branch ( 'mass'  , var1 , 'mass/D' )
        tree.Branch ( 'ctau'  , var2 , 'ctau/D' )
        
        for i in range ( nentries ) : 

            u = random.uniform  ( 0 , 1 )
            if 0.5 < u :
                m    = random.gauss  ( 3.1 ,  0.015 )
                ctau = random.expovariate ( 1/1.0 ) 
            else       :
                m  = random.uniform  ( 3.0 , 3.2  )
                ctau = random.expovariate ( 1/0.1 ) 
                
            var1[0] = m
            var2[0] = ctau 
            
            tree.Fill()
            
        root_file.Write()
        
# =============================================================================
def prepare_data ( nfiles = 50 ,  nentries = 500  ) :

    from ostap.utils.cleanup import CleanUp    
    files = [ CleanUp.tempfile ( prefix = 'ostap-test-tools-splot-%d-' % i ,
                                 suffix = '.root' ) for i in range ( nfiles)  ]
    
    for f in progress_bar ( files ) : create_tree ( f , nentries )
    return files

# =============================================================================
## Test sPlotting macheinery (outside of RooFit)
# - fill histogram for Ttree 
# - fit the histogram
# - make sPlot
# - write sPlot results into oroigin Ttree
def test_splotting  () : 
    """ Test sPlotting macheinery (outside of RooFit)
    - fill histogram from TTree 
    - fit the histogram
    - make sPlot
    - write sPlot results into oroigin Ttree
    """
    
    files = prepare_data ( 200 , 5000 )
    
    logger.info ( '#files:    %s'  % len ( files ) )  
    data = Data ( 'S' , files )
    logger.info ( 'Initial Tree/Chain:\n%s' % data.chain.table ( prefix = '# ' ) )
    
    chain  = data.chain 
    histo = ROOT.TH1D       ( hID() , 'mass distibution' , 200 , 3.0 , 3.2 )

    chain.project ( histo , 'mass' )
    
    mass  = ROOT.RooRealVar ( 'mass' , 'mass-variable' , 3.0 , 3.2  )
    
    gauss = Models.Gauss_pdf ( 'G' , xvar = mass ,
                               mean  = (3.1   , 3.1-0.01     , 3.1 + 0.01 ) ,
                               sigma = (0.015 , 0.8 * 0.015 , 1.2 * 0.015 ) ) 
    model = Models.Fit1D( signal = gauss , background = 0 )
    
    model.S = 0.5 * ( histo.Integral() )
    model.B = 0.5 * ( histo.Integral() )

    with FIXVAR ( [ gauss.mean , gauss.sigma ] ) : 
        model.fitTo ( histo , draw = False , silent = True )
        model.fitTo ( histo , draw = False , silent = True )
        
    model.fitTo ( histo , draw = False , silent = True )

    with use_canvas ( 'test_tools_splot: Fit') :
        r, f = model.fitTo ( histo , draw = True  , nbins = 100 , silent = True ) 
        
    title = "Fit results for" 
    logger.info ('%s:\n%s' % ( title  , r.table ( title = title , prefix = '# ') ) ) 
  
    ds  = model.histo_data.dset 
    sp  = sPlot1D ( model , ds  , nbins = 100 , fast = True ) ## SPLOT IT! 
    sph = sp.hweights['S']
    
    with use_canvas ( 'test_tools_splot: sPlot') :
        sph.draw ()
        if 0 > float ( sph ( r.mean_G * 1 ) ) :
            logger.error ( "Something totally wrong here!" ) 
            
    fnsp = Ostap.Functions.FuncTH1 ( sph , 'mass' )
    
    with DBASE.tmpdb()  as db :
        db ['histo'   ] = histo 
        db ['splot'   ] = sp
        db ['splot,h' ] = sph 
        db ['splot,f' ] = fnsp
        db.ls()
        
    with timing ( "Adding sPlot results to TTree" , logger = logger ) : 
        chain.add_new_branch ( 'sw_S' , fnsp ) 

    chain = data.chain 
    logger.info ( 'Updated Tree/Chain:\n%s' % chain.table ( prefix = '# ' ) )
    
    hs = ROOT.TH1D( hID() , 'ctau for signal'     , 200 , 0 , 5 )
    hb = ROOT.TH1D( hID() , 'ctau for background' , 200 , 0 , 5 )
    chain.project ( hs , 'ctau' , 'sw_S'   )
    chain.project ( hb , 'ctau' , '1-sw_S' )

    
    with wait ( 3 ) , use_canvas ( 'test_tools_splot: c*tau') :
        hs.red ()
        hb.blue()
        hb.draw()
        hs.draw('same')

        cnts = chain.statVar ('ctau' , 'sw_S'   )
        cntb = chain.statVar ('ctau' , '1-sw_S' )
        logger.info ( 'ctau S:%s' % cnts.mean() )
        logger.info ( 'ctau B:%s' % cntb.mean() )

        
    
# =============================================================================
if '__main__' ==  __name__  :

    test_splotting ()
    
# =============================================================================
##                                                                      The END 
# =============================================================================

