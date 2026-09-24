#!/bin/bash
#PBS -q normalsr
#PBS -l ncpus=16
#PBS -l mem=80GB
#PBS -l walltime=02:00:00
#PBS -l storage=gdata/xp65+gdata/gb02+scratch/gb02+scratch/ce10
#PBS -l wd
#PBS -l jobfs=40GB
#PBS -P ce10

module purge
module use /g/data/xp65/public/modules
module load conda/analysis3
module use /g/data/gb02/public/modules/
module load dask_setup

python /home/561/mjl561/git/access-am3-evaluation/notebooks/sandbox-python/compare_urban_onoff_year.py
