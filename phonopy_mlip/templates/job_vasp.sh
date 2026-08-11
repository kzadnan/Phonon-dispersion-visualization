#!/bin/bash
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=16
#SBATCH -o slurm-%j.out
##SBATCH --account=YOUR_ACCOUNT
##SBATCH --partition=YOUR_PARTITION

cd "$SLURM_SUBMIT_DIR"
# module load vasp/6.4.0

srun -n $SLURM_NTASKS vasp_std
