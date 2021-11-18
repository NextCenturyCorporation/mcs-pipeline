#!/bin/bash

set -x

# Check passed mcs_config and scene file
source /home/ubuntu/check_passed_variables.sh

echo "Running CORA with config $mcs_configfile and scene $scene_file using eval dir $eval_dir"

# Start X
source /home/ubuntu/start_x_server.sh

# Clear out directories
echo Clearing History at $eval_dir/SCENE_HISTORY/
rm -f $eval_dir/SCENE_HISTORY/*

export MCS_CONFIG_FILE_PATH=$mcs_configfile

# Run the Performer code
echo Starting Evaluation:

cd $eval_dir
source /home/ubuntu/genpram_venv/bin/activate && julia run_julia_argument.jl $scene_file
