#!/bin/bash

# Common code to make sure that our scripts are passed config files properly and that they exist

# Will be passed in two things:
#    mcs_configfile  scene_file
if [ -z $1 ] || [ -z $2 ]; then
    echo "Need mcs_configfile as first parameter, scene_file as second"
    exit 1
fi
export mcs_configfile=$1
export scene_file=$2

# Check that the files exist
if [ ! -f "$mcs_configfile" ]; then
    echo "The file $mcs_configfile does not exist"
    exit 1
fi
if [ ! -f "$scene_file" ]; then
    echo "The file $scene_file does not exist"
    exit 1
fi

