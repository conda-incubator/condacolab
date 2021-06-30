#!/bin/sh
. $PREFIX/etc/profile.d/conda.sh  # do not edit
conda activate $PREFIX  # do not edit

# add your pip packages here
python -m pip install bottle