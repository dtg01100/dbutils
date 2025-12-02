#!/usr/bin/env bash
set -e

echo "Building Cython extensions..."

# Install build dependencies
uv pip install Cython setuptools wheel

# Build extensions
uv run python setup.py build_ext --inplace

echo "Cython extensions built successfully!"
echo "Extensions will be available as 'dbutils.accelerated'"
