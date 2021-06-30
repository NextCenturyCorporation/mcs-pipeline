#!/bin/bash

# check passed mcs_config and scene file
source /home/ubuntu/check_passed_variables.sh

echo "Running MESS with config $mcs_configfile and scene $scene_file"

source /home/ubuntu/start_x_server.sh

# Clear out the directories
rm -f /home/ubuntu/mess_eval35/scenes/*
rm -f /home/ubuntu/mess_eval35/SCENE_HISTORY/*

# Copy the scenes and config file to the right place 
scene_file_basename=$(basename $scene_file)
cp $scene_file /home/ubuntu/mess_eval35/scenes/
cp $mcs_configfile /home/ubuntu/mess_eval35/level1.config

# Go to the mess_eval35/, which is where we will be running things
echo $scene_file
cd /home/ubuntu/mess_eval35/

# Activate conda environment
source /home/ubuntu/anaconda3/etc/profile.d/conda.sh
conda activate myenv

# run model
python3 script_mess.py scenes/$scene_file_basename

mkdir -p /tmp/results/
cp /home/ubuntu/mess_eval35/SCENE_HISTORY/* /tmp/results/

