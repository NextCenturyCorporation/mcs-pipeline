#!/bin/bash

# Will be passed in two things:
#    mcs_configfile  scene_file
mcs_configfile=$1
scene_file=$2

echo "Running Baseline with config $mcs_configfile and scene $scene_file"


# TODO:  Check that files exist


source /home/ubuntu/venv/bin/activate

# Start X
# TODO:  Check to see if the xserver is already running and do not restart
cd mcs-pipeline/xserver
sudo python3 run_startx.py &
sleep 20

# Clear out the directories
rm -f /home/ubuntu/scenes/validation/*
rm -f /home/ubuntu/SCENE_HISTORY/*

# Go to the home directory, which is where we will be run
cd /home/ubuntu

# Copy the scenes and config file to the right place 
cp $scene_file /home/ubuntu/scenes/validation/
cp $mcs_configfile /home/ubuntu/mcs_config.ini

# Run the model
python3 gravity_py.py

# Copy the results to the right place
mkdir -p /tmp/results/
cp /home/ubuntu/SCENE_HISTORY/* /tmp/results/



