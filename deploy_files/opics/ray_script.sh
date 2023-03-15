#!/bin/bash
set -m

# This is what the "main_optics" command does.
echo "MCS Pipeline: Running OPICS environment setup..."
cd /home/ubuntu/ || exit
headless
export OPTICS_HOME=~/main_optics
export PYTHONPATH=$OPTICS_HOME:$OPTICS_HOME/opics_common
export OPTICS_DATASTORE=ec2b
cd $OPTICS_HOME || exit
cd scripts/ || exit

# Check passed mcs_config and scene file
# shellcheck source=/dev/null
source /home/ubuntu/check_passed_variables.sh

# shellcheck disable=SC2154
echo "MCS Pipeline: Running OPICS with MCS config file $mcs_configfile and eval dir $eval_dir and scene file $scene_file"

echo "MCS Pipeline: Clearing History at $eval_dir/SCENE_HISTORY/"
rm -f "$eval_dir"/SCENE_HISTORY/*

# Start X
source /home/ubuntu/start_x_server.sh

export MCS_CONFIG_FILE_PATH=$mcs_configfile
python opics_eval6_run_scene.py --scene "$scene_file"
unset MCS_CONFIG_FILE_PATH
