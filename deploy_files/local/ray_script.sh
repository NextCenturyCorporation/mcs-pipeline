#!/bin/bash

# Check passed mcs_config and scene file
LOCAL_DIR=$(dirname $0)
CHECK_PASSED_VAR_LOC="${LOCAL_DIR%/*}/check_passed_variables.sh"

source $CHECK_PASSED_VAR_LOC

# Your local directory - for this example, its where ever you have your 
# MCS python API package checked out
SCENE_DIR="$eval_dir/tmp_scenes/"
TMP_CFG_FILE="$eval_dir/msc_cfg.ini.tmp"

echo "Running local test with config $mcs_configfile and scene $scene_file using eval dir $eval_dir"

echo "Making temporary copy of config file ($mcs_configfile -> $TMP_CFG_FILE)"
cp $mcs_configfile $TMP_CFG_FILE
echo Removing old config file at $eval_dir/mcs_config_local.ini
rm $eval_dir/mcs_config_local.ini
echo Moving temporary config file to config location
mv $TMP_CFG_FILE $eval_dir/mcs_config_local.ini

# Run a test script
cd $eval_dir
echo Starting Evaluation:
source venv/bin/activate
python machine_common_sense/scripts/run_just_pass.py $scene_file --config_file $eval_dir/mcs_config_local.ini 
