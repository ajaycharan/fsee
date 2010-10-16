#!/usr/bin/env python

# Copyright (C) 2005-2008 California Institute of Technology, All
# rights reserved

# Author: Andrew D. Straw

from __future__ import division

import math, sys, sets, os
import cgtypes # cgkit 1.x
import numpy
import scipy
import scipy.sparse
import scipy.io
from drosophila_eye_map.util import cube_order, make_repr_able, save_as_python,\
     make_receptor_sensitivities, flatten_cubemap
from emd_util import find_edges, pseudo_voronoi


def precompute_generic(configuration_name, receptor_dirs, tris):
    script_dir = os.path.abspath(os.path.split(__file__)[0])
    os.chdir(script_dir)

########################################################
#    SAVE INFO (from save_sparse_weights.py)
########################################################

#    receptor_dirs, tris = make_subdivided_unit_icosahedron(n_subdivides=3) # n_subidivisions
#    receptors_by_phi = sort_receptors_by_phi(receptor_dirs,nbins = 32)
    edges = find_edges( tris )
    verts = receptor_dirs

    rad2deg = 180/math.pi
    v0 = verts[0]
    a_degs = [v0.angle(v)*rad2deg for v in verts[1:]]
    a_degs.sort()
    delta_phi_deg = a_degs[0] # inter receptor angle, 6.848549293 when 3 subdivisions of icosahedron
    print 'delta_phi_deg',delta_phi_deg
    delta_phi = delta_phi_deg/rad2deg

    delta_rho = delta_phi * 1.1 # rough approximation. follows from caption of Fig. 18, Buchner, 1984 (in Ali)

    weight_maps_64 = make_receptor_sensitivities( receptor_dirs, delta_rho_q=delta_rho, res=64 )
    print 'weight_maps calculated'

    #####################################

    clip_thresh=1e-5
    floattype=numpy.float32

    weights = flatten_cubemap( weight_maps_64[0] ) # get first one to take size

    n_receptors = len(receptor_dirs)
    len_wm = len(weights)

    print 'allocating memory...'
    bigmat_64 = numpy.zeros( (n_receptors, len_wm), dtype=floattype )
    print 'done'

    print 'flattening, clipping, casting...'
    for i, weight_cubemap in enumerate(weight_maps_64):
        weights = flatten_cubemap( weight_cubemap )
        if clip_thresh is not None:
            weights = numpy.choose(weights<clip_thresh,(weights,0))
        bigmat_64[i,:] = weights.astype( bigmat_64.dtype )
    print 'done'

    print 'worst gain (should be unity)',min(numpy.sum( bigmat_64, axis=1))
    print 'filling spmat_64...'
    sys.stdout.flush()
    spmat_64 = scipy.sparse.csc_matrix(bigmat_64)
    print 'done'

    M,N = bigmat_64.shape
    print 'Compressed to %d of %d'%(len(spmat_64.data),M*N)

    faces = pseudo_voronoi(receptor_dirs,tris)

    ##################################################
    # Save matlab version

    fd = open('precomputed_%s.m' % configuration_name,'w')
    fd.write( 'receptor_dirs = [ ...')
    for rdir in receptor_dirs:
        fd.write( '\n    %s %s %s;'%( repr(rdir[0]), repr(rdir[1]), repr(rdir[2]) ) )
    fd.write( '];\n\n')

    fd.write( 'edges = [ ...')
    for e in edges:
        fd.write( '\n    %d %d;'%( e[0]+1, e[1]+1 )) # convert to 1-based indexing
    fd.write( '];\n\n')
    fd.close()
    ##################################################

    receptor_dir_slicer = {None:slice(0,len(receptor_dirs),1)}
    edge_slicer = {None:slice(0,len(edges),1)}
    #

    fd = open('precomputed_%s.py' % configuration_name,'wb')
    fd.write( '# Automatically generated by %s\n'%os.path.split(__name__)[-1])
    fd.write( 'import numpy\n')
    fd.write( 'import scipy\n')
    fd.write( 'import scipy.sparse\n')
    fd.write( 'import scipy.io\n')
    fd.write( 'import cgtypes # cgkit 1.x\n')
    fd.write( 'from cgtypes import vec3, quat #cgkit 1.x\n')
    fd.write( 'import os\n')
    fd.write( 'datadir = os.path.split(__file__)[0]\n')
    fd.write( 'cube_order = %s\n'%repr(cube_order) )
    save_as_python(fd, receptor_dir_slicer, 'receptor_dir_slicer', fname_extra='_synthetic' )
    save_as_python(fd, edge_slicer, 'edge_slicer', fname_extra='_synthetic' )
    save_as_python(fd, spmat_64, 'receptor_weight_matrix_64', fname_extra='_synthetic' )
    save_as_python(fd, map(make_repr_able,receptor_dirs), 'receptor_dirs', fname_extra='_synthetic' )
    save_as_python(fd, tris, 'triangles')
    save_as_python(fd, edges, 'edges')
    save_as_python(fd, map(make_repr_able,faces), 'hex_faces')
#    save_as_python(fd, receptors_by_phi, 'receptors_by_phi',fname_extra='_synthetic' )
    fd.write( '\n')
    fd.write( '\n')
    fd.write( '\n')
    extra = open('plot_receptors_vtk.py','r').read()
    fd.write( extra )
    fd.close()
    