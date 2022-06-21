#!/bin/bash
set -m
echo Running OPICS commands from run_opics_commands.sh
conda activate env_pvoe
opics_eval5
cd "$1" && cp "$2" ../cfg/mcs_config.ini && python run_opics.py --scenes "$3"
