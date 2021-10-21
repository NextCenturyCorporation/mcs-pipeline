#!/bin/bash

# Check passed mcs_config and scene file
LOCAL_DIR=$(dirname $0)
CHECK_PASSED_VAR_LOC="${LOCAL_DIR%/*}/check_passed_variables.sh"

source $CHECK_PASSED_VAR_LOC

# Your local directory - for this example, its where ever you have your 
# MCS python API package checked out
SCENE_DIR="$eval_dir/tmp_scenes/"

echo "Running local test with config $mcs_configfile and scene $scene_file using eval dir $eval_dir"
export MCS_CONFIG_FILE_PATH=$mcs_configfile

# Run a test script
cd $eval_dir
echo Starting Evaluation:
source venv/bin/activate
python machine_common_sense/scripts/run_just_pass.py $scene_file --config_file $eval_dir/mcs_config_local.ini 

unset MCS_CONFIG_FILE_PATH
