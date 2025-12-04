#!/bin/bash

# Launch the dbutils application with the JDBC configuration manager fix
cd /workspaces/dbutils
export PYTHONPATH="src:.$PYTHONPATH"
python3.12 run_dbutils.py --mock