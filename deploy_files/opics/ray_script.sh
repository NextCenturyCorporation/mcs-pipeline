#!/bin/bash

# Will be passed in two things:
#    mcs_configfile  scene_file
mcs_configfile=$1
scene_file=$2

EVAL_DIR=/home/ubuntu/mcs_eval3-3.5.0
SCENE_DIR="$EVAL_DIR/eval_scene/"
TMP_CFG_FILE="$EVAL_DIR/msc_cfg.ini.tmp"

echo "Running OPICS with config $mcs_configfile and scene $scene_file"

# Pre setup - potentially move to run once per machine later
echo Starting X Server
#sudo nvidia-xconfig --use-display-device=None --virtual=1280x1024 --output-xconfig=/etc/X11/xorg.conf --busid=PCI:0:30:0
sudo nohup /usr/bin/Xorg :0 1>startx-out.txt 2>startx-err.txt &
echo "Sleeping for 20 seconds to wait for X server"
sleep 20
echo "Sleep finished"

echo Clearing History at $EVAL_DIR/SCENE_HISTORY/
rm -f $EVAL_DIR/SCENE_HISTORY/*

#cd $EVAL_DIR

echo Making SCENE_DIR=$SCENE_DIR
mkdir -p $SCENE_DIR
echo Clearing $SCENE_DIR
rm -rf $SCENE_DIR/*
echo Moving scene_file=$scene_file to $SCENE_DIR
cp $scene_file $SCENE_DIR/

echo "Making temporary copy of config file ($mcs_configfile -> $TMP_CFG_FILE)"
cp $mcs_configfile $TMP_CFG_FILE
echo Removing old config file at $EVAL_DIR/mcs_config.ini
rm $EVAL_DIR/mcs_config.ini
echo Moving temporary config file to config location
mv $TMP_CFG_FILE $EVAL_DIR/mcs_config.ini

echo Starting Evaluation:
echo 
cd $EVAL_DIR && source activate mcs_opics && python3 eval.py  --scenes $SCENE_DIR

# Copy the results to the right place
echo Copying results to /tmp/results/
mkdir -p /tmp/results/
cp $EVAL_DIR/SCENE_HISTORY/* /tmp/results/
