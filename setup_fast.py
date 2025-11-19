import numpy
from Cython.Build import cythonize
from setuptools import Extension, setup

extensions = [
    Extension(
        "dbutils.fast_ops",
        ["src/dbutils/fast_ops.pyx"],
        include_dirs=[numpy.get_include()],
        extra_compile_args=["-O3", "-march=native"],
        extra_link_args=["-O3"],
    )
]

setup(
    name="dbutils-fast-ops",
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            "language_level": "3",
            "boundscheck": False,
            "wraparound": False,
            "cdivision": True,
            "profile": False,
        },
    ),
)
