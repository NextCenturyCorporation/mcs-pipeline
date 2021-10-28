#!/bin/bash

# Check passed mcs_config and scene file
# LOCAL_DIR=$(dirname $0)
# CHECK_PASSED_VAR_LOC="${LOCAL_DIR%/*}/check_passed_variables.sh"
# source $CHECK_PASSED_VAR_LOC
source /home/ubuntu/check_passed_variables.sh
SCENE_DIR="$eval_dir/scenes/"

echo "Running Baseline with config $mcs_configfile and scene $scene_file using eval dir $eval_dir"

# Start X
source /home/ubuntu/start_x_server.sh

# Clear out the directories
echo Clearing History at $eval_dir/SCENE_HISTORY/
rm -f $eval_dir/SCENE_HISTORY/*
echo Clearing $SCENE_DIR
rm -rf $SCENE_DIR/*

# Move files to appropriate locations
echo Making SCENE_DIR=$SCENE_DIR
mkdir -p $SCENE_DIR
echo Moving scene_file=$scene_file to $SCENE_DIR
cp $scene_file $SCENE_DIR/

export MCS_CONFIG_FILE_PATH=$mcs_configfile

# Run the Performer code
cd $eval_dir
echo Starting Evaluation:
echo $eval_dir

venv/bin/python baseline_reori.py --scene_file $scene_file

unset MCS_CONFIG_FILE_PATH