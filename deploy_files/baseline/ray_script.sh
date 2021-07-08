#!/bin/bash

# Check passed mcs_config and scene file
source /home/ubuntu/check_passed_variables.sh

EVAL_DIR=/home/ubuntu
SCENE_DIR="$EVAL_DIR/scenes/validation/"
TMP_CFG_FILE="$EVAL_DIR/msc_cfg.ini.tmp"

echo "Running Baseline with config $mcs_configfile and scene $scene_file"

# Start X
source /home/ubuntu/start_x_server.sh

# Clear out the directories
echo Clearing History at $EVAL_DIR/SCENE_HISTORY/
rm -f $EVAL_DIR/SCENE_HISTORY/*
echo Clearing $SCENE_DIR
rm -rf $SCENE_DIR/*

# Move files to appropriate locations
echo Making SCENE_DIR=$SCENE_DIR
mkdir -p $SCENE_DIR
echo Moving scene_file=$scene_file to $SCENE_DIR
cp $scene_file $SCENE_DIR/

echo "Making temporary copy of config file ($mcs_configfile -> $TMP_CFG_FILE)"
cp $mcs_configfile $TMP_CFG_FILE
echo Removing old config file at $EVAL_DIR/mcs_config.ini
rm $EVAL_DIR/mcs_config.ini
echo Moving temporary config file to config location
mv $TMP_CFG_FILE $EVAL_DIR/mcs_config.ini

# Run the Performer code
cd $EVAL_DIR
echo Starting Evaluation:
echo
source /home/ubuntu/venv/bin/activate
python3 gravity_py.py
