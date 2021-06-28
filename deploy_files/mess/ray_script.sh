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


echo "Running MESS with config $mcs_configfile and scene $scene_file"

# Start X
# TODO: Check to see if the xserver is already running and do not restart (MCS-727)
cd mcs-pipeline/xserver
sudo python3 run_startx.py &
sleep 20

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

