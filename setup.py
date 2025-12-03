"""Setup configuration for Cython extensions."""

from Cython.Build import cythonize
from setuptools import Extension, setup

# Define Cython extensions
extensions = [
    Extension(
        "dbutils.accelerated",
        ["src/dbutils/fast_ops.pyx"],
        extra_compile_args=["-O3", "-march=native"],
        language="c",
    ),
]

setup(
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            "language_level": "3",
            "boundscheck": False,
            "wraparound": False,
            "cdivision": True,
            "nonecheck": False,
            "embedsignature": True,
        },
        annotate=False,  # Set to True to generate HTML annotation files
    ),
)
