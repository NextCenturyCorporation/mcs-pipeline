#!/bin/bash

# Check passed mcs_config and scene file
LOCAL_DIR=$(dirname $0)
CHECK_PASSED_VAR_LOC="${LOCAL_DIR%/*}/check_passed_variables.sh"

source $CHECK_PASSED_VAR_LOC

# Your local directory - for this example, its where ever you have your 
# MCS python API package checked out
EVAL_DIR=some/local/path/mcs-python
SCENE_DIR="$EVAL_DIR/tmp_scenes/"
TMP_CFG_FILE="$EVAL_DIR/msc_cfg.ini.tmp"

echo "Running local test with config $mcs_configfile and scene $scene_file"

echo "Making temporary copy of config file ($mcs_configfile -> $TMP_CFG_FILE)"
cp $mcs_configfile $TMP_CFG_FILE
echo Removing old config file at $EVAL_DIR/mcs_config_local.ini
rm $EVAL_DIR/mcs_config_local.ini
echo Moving temporary config file to config location
mv $TMP_CFG_FILE $EVAL_DIR/mcs_config_local.ini

# Run a test script
cd $EVAL_DIR
echo Starting Evaluation:
source venv/bin/activate
python scripts/run_just_pass.py $scene_file --config_file $EVAL_DIR/mcs_config_local.ini 
