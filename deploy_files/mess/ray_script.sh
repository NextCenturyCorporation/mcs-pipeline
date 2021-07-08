#!/bin/bash

# Check passed mcs_config and scene file
source /home/ubuntu/check_passed_variables.sh

EVAL_DIR=/home/ubuntu/mess_eval35/
SCENE_DIR="$EVAL_DIR/scenes/"
TMP_CFG_FILE="$EVAL_DIR/msc_cfg.ini.tmp"

echo "Running MESS with config $mcs_configfile and scene $scene_file"

# Start X
source /home/ubuntu/start_x_server.sh

# Clear out the directories
echo Clearing History at $EVAL_DIR/SCENE_HISTORY/
rm -f $EVAL_DIR/SCENE_HISTORY/*
echo Clearing $SCENE_DIR
rm -f SCENE_DIR

# Move files to appropriate locations
echo Making SCENE_DIR=$SCENE_DIR
mkdir -p $SCENE_DIR
echo Moving scene_file=$scene_file to $SCENE_DIR
cp $scene_file $SCENE_DIR/

echo "Making temporary copy of config file ($mcs_configfile -> $TMP_CFG_FILE)"
cp $mcs_configfile $TMP_CFG_FILE
cp $mcs_configfile $EVAL_DIR/level1.config
rm $EVAL_DIR/mcs_config.ini
echo Moving temporary config file to config location
mv $TMP_CFG_FILE $EVAL_DIR/mcs_config.ini

# Go to the mess_eval35/, which is where we will be running things
cd $EVAL_DIR

# Activate conda environment
source /home/ubuntu/anaconda3/etc/profile.d/conda.sh
conda activate myenv

# Run the Performer code
echo Starting Evaluation:
echo
scene_file_basename=$(basename $scene_file)
python3 script_mess.py scenes/$scene_file_basename

