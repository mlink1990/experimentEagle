# -*- coding: utf-8 -*-
"""
Created on Wed Jun 29 21:52:29 2016

@author: ispielma

This program is designed to be an example of PCA based cleanup of images

It has a function that generates collections of images that can either be
the training set or the target image

We will also support masked regions

"""

import numpy as np

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

def Image(size=1024, amplitude=1, noise=0.1, sources=[[0.01, 0.1, 0.040]]):
    """
    creates a single image that is derived from a field with some fringe
    sources, along with read noise.
    """
    
    field = np.zeros((size,size), dtype=complex)
    
    xvals = np.linspace(-1,1,size)    
    yvals = np.linspace(-1,1,size)
    
    grid = np.meshgrid(xvals, yvals)
    
    field += amplitude * np.exp(-(grid[0]**2 + grid[1]**2)**2)    

    for source in sources:
        exponent = grid[0]*source[1] + grid[1]*source[2] + np.random.uniform(low=0.0, high=2*np.pi)
        exponent = np.random.normal(scale=source[0]) * np.exp(1.0j*exponent)     
        field += exponent
    
    return np.abs(field)**2 + np.random.normal(scale=noise, size=(size,size))
    
def Images(num, **kwargs):
    result = [Image(**kwargs) for i in range(num)]
    return result

def PCA(training):
    """
    Return the principle components and their eigenvalues for the
    training set
    """

    training = np.array(training)    
    
    #
    # Because we want equal weight given to each vector, we first normalize
    #
    
    norm = np.einsum("ij,ij->i",training, training) 
    M = np.einsum("ij,i->ij", training, np.power(np.multiply(1.0, np.abs(norm)), -0.5))#norm**-0.5)
    
    #
    # Contract to work in the subspace spanned by the training vectors
    #

    MM = np.einsum("ji,ki->jk", M, M) 
    vals, vecs_MM = np.linalg.eigh(MM)
    
    vals = vals[::-1]
    vecs_MM = vecs_MM[:, ::-1]    
    
    vecs = np.einsum("ij,ik,k->kj", M, vecs_MM, np.power(np.multiply(1.0,np.abs(vals)), -0.5))#vals**-0.5)
    
    #
    # These eigen vectors can be interperted as containing the coefficients
    # of the inpout vectors that make up the real eigenvalues
    #

    return vals, vecs

def PCA_mask(training_no_mask, mask):
    """
    Return the principle components and their eigenvalues for the
    training set.
    
    Here we are passed a mask containing a region where we ignore data.
    
    returns:
        values, masked_PCA vectors, unmasked_PCA vectors
    """

    training_no_mask = np.array(training_no_mask)    
    
    #
    # generate a masked training set
    #     

    
    training = np.einsum("ij,j->ij", training_no_mask, mask) 
    
    #
    # Because we want equal weight given to each vector, we first normalize
    #
    
    norm = np.einsum("ij,ij->i",training, training) 
    M = np.einsum("ij,i->ij", training, norm**-0.5)
    M_no_mask = np.einsum("ij,i->ij", training_no_mask, norm**-0.5)
    
    #
    # Contract to work in the subspace spanned by the training vectors
    #

    MM = np.einsum("ji,ki->jk", M, M) 
    vals, vecs_MM = np.linalg.eigh(MM)
    
    vals = vals[::-1]
    vecs_MM = vecs_MM[:, ::-1]    
    
    vecs = np.einsum("ij,ik,k->kj", M, vecs_MM, vals**-0.5)
    vecs_no_mask = np.einsum("ij,ik,k->kj", M_no_mask, vecs_MM, vals**-0.5)
    
    #
    # These eigen vectors can be interperted as containing the coefficients
    # of the inpout vectors that make up the real eigenvalues
    #
    
    return vals, vecs, vecs_no_mask


def Reconstruct(target, vecs, num, vecs_unmasked=None):
    """
    return a reconstruction of target using num vectors
    """
    
    if num > vecs.shape[0]: 
        num = vecs.shape[0]
    
    vecs_trunc = vecs[:num, :]    
    
    #
    # Get overlaps
    #

    coefs = np.einsum("ij,j->i", vecs_trunc, target) 

    #
    # rebuild, using unmasked vectors if desired.
    #
    
    if vecs_unmasked is None:
        result = np.einsum("ij,i->j", vecs_trunc, coefs)
    else:
        vecs_trunc = vecs_unmasked[:num, :]  
        result = np.einsum("ij,i->j", vecs_trunc, coefs)
    
    return result, coefs

#
# Run Example
#
if __name__ == "__main__":
    
    #
    # Build the training set and the target image, and make into vectors
    #    
    
    size = 512    

    mask_size=256
    
    training_size=32#64
    keep_size=16

    mask = np.ones((size,size))
    start = int((size-mask_size)/2)
    stop = int((size+mask_size)/2)
    mask_core = mask[start:stop,start:stop]    
    mask_core.fill(0)
    
    images = Images(num=training_size, size=size, amplitude=1, noise=0.1, 
                  sources=[
                          [0.03, 20, 10],
                          [0.05, -20, 30],
                          [0.1, 40, 5]
                          ])
    images = [image.ravel() for image in images]    
    
    target = images[0]
    training = images[1:]
    print np.shape(training)
    #
    # Get the principle components from the training set
    # then reconstruct
    #

    vals, vecs = PCA(training)
    print np.shape(vals)
    vec_r, coefs = Reconstruct(target, vecs, keep_size)
    delta_r = vec_r - target  


    # 
    # Perform reconstruction with mask
    #     

    vals_mask, vecs_mask, vecs_no_mask  = PCA_mask(training, mask.ravel())
        
    vec_r_mask, coefs_mask = Reconstruct(target, vecs_mask, keep_size, vecs_unmasked=vecs_no_mask)
    delta_r_mask = vec_r_mask - target  

    print "I am done. You can Plot now."
    #
    # Graph!
    #

    image = target.reshape(size,size)
    image_r = vec_r.reshape(size,size)
    image_delta_r = delta_r.reshape(size,size)

    image = target.reshape(size,size)
    image_r_mask = vec_r_mask.reshape(size,size)
    image_delta_r_mask = delta_r_mask.reshape(size,size)

    
    image_vecs = [vec.reshape(size,size) for vec in vecs]


    gs = gridspec.GridSpec(4, 3)
    gs.update(wspace=0.4, hspace=0.4)
    fig = plt.figure(1, figsize=(9,10))  

    ax = fig.add_subplot(gs[0, 0])
    ax.plot(vals)
    ax.plot(vals_mask)
    ax.set_yscale('log')

    ax = fig.add_subplot(gs[0, 1])
    ax.plot(np.abs(coefs))
    ax.plot(np.abs(coefs_mask))
    ax.set_yscale('log')

    ax = fig.add_subplot(gs[0, 2])
    ax.imshow(mask)

    #
    # Unmasked recovery
    #

    ax = fig.add_subplot(gs[1, 0])
    ax.imshow(image)

    ax = fig.add_subplot(gs[1, 1])
    ax.imshow(image_r)

    ax = fig.add_subplot(gs[1, 2])
    ax.imshow(image_delta_r)

    #
    # Masked recovery
    #

    ax = fig.add_subplot(gs[2, 0])
    ax.imshow(image)

    ax = fig.add_subplot(gs[2, 1])
    ax.imshow(image_r_mask)

    ax = fig.add_subplot(gs[2, 2])
    ax.imshow(image_delta_r_mask)

    #
    # Example components
    #

    ax = fig.add_subplot(gs[3, 0])
    ax.imshow(image_vecs[0])

    ax = fig.add_subplot(gs[3, 1])
    ax.imshow(image_vecs[1])

    ax = fig.add_subplot(gs[3, 2])
    ax.imshow(image_vecs[2])
    
