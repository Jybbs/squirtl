# distutils: language = c++
# cython: language_level=3

from libcpp.vector cimport vector

cdef extern from "POC.cpp":
    cdef cppclass BlockwisePCA:
        BlockwisePCA(int blockSize, int numComponents, int frameHeight, int frameWidth)
        void fitFrames(const vector[vector[vector[double]]]& frames)
        vector[vector[double]] transformFrame(const vector[vector[double]]& frame)

cdef class CythonBPCA:
    cdef BlockwisePCA* c_bpca

    def __cinit__(self, int blockSize, int numComponents, int frameHeight, int frameWidth):
        self.c_bpca = new BlockwisePCA(blockSize, numComponents, frameHeight, frameWidth)

    def __dealloc__(self):
        del self.c_bpca

    def fit_frames(self, frames):
        cdef vector[vector[vector[double]]] c_frames = frames
        self.c_bpca.fitFrames(c_frames)

    def transform_frame(self, frame):
        cdef vector[vector[double]] c_frame = frame
        return self.c_bpca.transformFrame(c_frame)