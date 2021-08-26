#!/bin/bash

# Check passed mcs_config and scene file
source /home/ubuntu/check_passed_variables.sh

SCENE_DIR="$eval_dir/scenes/"
TMP_CFG_FILE="$eval_dir/msc_cfg.ini.tmp"

echo "Running MESS with config $mcs_configfile and scene $scene_file using eval dir $eval_dir"

# Start X
source /home/ubuntu/start_x_server.sh

# Clear out the directories
echo Clearing History at $eval_dir/SCENE_HISTORY/
rm -f $eval_dir/SCENE_HISTORY/*
echo Clearing $SCENE_DIR
rm -f SCENE_DIR

# Move files to appropriate locations
echo Making SCENE_DIR=$SCENE_DIR
mkdir -p $SCENE_DIR
echo Moving scene_file=$scene_file to $SCENE_DIR
cp $scene_file $SCENE_DIR/

echo "Making temporary copy of config file ($mcs_configfile -> $TMP_CFG_FILE)"
cp $mcs_configfile $TMP_CFG_FILE
cp $mcs_configfile $eval_dir/level2.config
rm $eval_dir/mcs_config.ini
echo Moving temporary config file to config location
mv $TMP_CFG_FILE $eval_dir/mcs_config.ini

# Go to the mess_eval375/, which is where we will be running things
cd $eval_dir

# Activate conda environment
source /home/ubuntu/anaconda3/etc/profile.d/conda.sh
conda activate myenv

# Run the Performer code
echo Starting Evaluation:
echo
scene_file_basename=$(basename $scene_file)
# TODO: MCS-818: Changing this manually, but we need a way to handle 
# arguments for different submissions (perhaps this is another MCS 
# config file addition) 

# run with '1' and '2' for both MESS submissions
python3 script_mess.py scenes/$scene_file_basename 2

