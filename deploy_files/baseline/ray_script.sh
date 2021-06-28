#!/bin/bash

# Will be passed in two things:
#    mcs_configfile  scene_file
if [ -z $1 ] || [ -z $2 ]; then
    echo "Need mcs_configfile as first parameter, scene_file as second"
    exit 1
fi
mcs_configfile=$1
scene_file=$2

# Check that the files exist
if [ ! -f "$mcs_configfile" ]; then
    echo "The file $mcs_configfile does not exist"
    exit 1
fi
if [ ! -f "$scene_file" ]; then
    echo "The file $scene_file does not exist"
    exit 1
fi


echo "Running Baseline with config $mcs_configfile and scene $scene_file"


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



