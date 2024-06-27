from Cython.Build import cythonize
from setuptools   import setup, Extension
import numpy as np

ext_modules = [
    Extension \
    (
        "CythonBPCA",
        sources            = ["CythonBPCA.pyx", "POC.cpp"],
        language           = "c++",
        extra_compile_args = ["-std=c++11"],
        include_dirs       = [np.get_include(), "."]
    ),
]

setup \
(
    name        = "CythonBPCA",
    ext_modules = cythonize(ext_modules, language_level = "3"),
)