# distutils: language = c++
# cython: language_level=3

from libcpp.vector cimport vector

cdef extern from "POC.cpp":
    cdef cppclass BlockwisePCA:
        BlockwisePCA(int blockSize, int numComponents, int frameHeight, int frameWidth, int numChannels)
        void fitFrames(const vector[vector[vector[vector[double]]]]& frames)
        vector[vector[vector[double]]] transformFrame(const vector[vector[vector[double]]]& frame)

cdef class CythonBPCA:
    cdef BlockwisePCA* c_bpca

    def __cinit__(self, int blockSize, int numComponents, int frameHeight, int frameWidth, int numChannels):
        self.c_bpca = new BlockwisePCA(blockSize, numComponents, frameHeight, frameWidth, numChannels)

    def __dealloc__(self):
        del self.c_bpca

    def fit_frames(self, frames):
        # Assuming frames is a list of 3D numpy arrays
        cdef vector[vector[vector[vector[double]]]] c_frames
        for frame in frames:
            c_frames.push_back(frame.tolist())
        self.c_bpca.fitFrames(c_frames)

    def transform_frame(self, frame):
        # Assuming frame is a 3D numpy array
        cdef vector[vector[vector[double]]] c_frame = frame.tolist()
        return self.c_bpca.transformFrame(c_frame)