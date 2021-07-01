#!/bin/bash
# This file is intended to be run on local development machine.
# This will perform the following actions:
#  1. Start a ray cluster for the appropriate module
#  2. Upload the appropriate scenes
#  3. Upload the config files
#  4. Start the eval

MODULE=$1
TMP_DIR=.tmp_pipeline_ray

# We probably don't need a new 'locations' file for each team in evals
RAY_LOCATIONS_CONFIG=configs/${MODULE}_aws.ini

mkdir -p $TMP_DIR
rm -rf $TMP_DIR/*

ORIG_PWD=$PWD


#cp -R configs $TMP_DIR
cp -R deploy_files/${MODULE}/* $TMP_DIR/
#mkdir -p $TMP_DIR/scenes/tmp
#cp -R $LOCAL_SCENE_DIR/* $TMP_DIR/scenes/tmp/
RAY_CONFIG="autoscaler/ray_${MODULE}_aws.yaml"

ray up -y $RAY_CONFIG
wait

# We should copy all the pipeline code, but at least opics needs it in a special folder.  Should ray_script handle that?  
# Should we run
ray rsync_up -v $RAY_CONFIG pipeline '~'
ray rsync_up -v $RAY_CONFIG deploy_files/${MODULE}/ '~'
ray rsync_up -v $RAY_CONFIG configs/ '~/configs/'

####### STARTING EVAL SPECIFIC CODE ########

# Handle inputs:

DEFAULT_METADATA="level2"
LOCAL_SCENE_DIR=$2
# Removing ending slash of scene dir so we have consistency
LOCAL_SCENE_DIR=$(echo $LOCAL_SCENE_DIR | sed 's:/*$::')
METADATA=${3:-$DEFAULT_METADATA}

MCS_CONFIG=configs/mcs_config_${MODULE}_${METADATA}.ini

# Create necessary files:

# Create list of scenes for head node to run.  All scenes will also be rsync'ed.
for entry in $LOCAL_SCENE_DIR/*
do
  echo "`basename $entry`" >> $TMP_DIR/scenes_single_scene.txt
done

# Debug info

echo "Starting Ray Eval:"
echo "  Module:        $MODULE"
echo "  Metadata:      $METADATA"
echo "  Scene Dir:     $LOCAL_SCENE_DIR"
echo "  Ray Config:    $RAY_CONFIG"
echo "  Ray Locations: $RAY_LOCATIONS_CONFIG"
echo "  MCS config:    $MCS_CONFIG" 

ray exec $RAY_CONFIG "mkdir -p ~/scenes/tmp/"

# this may cause re-used machines to have more scenes than necessary in the follow location.
# I believe this is ok since we use the txt file to control exactly which files are run.
ray rsync_up -v $RAY_CONFIG $LOCAL_SCENE_DIR/ '~/scenes/tmp/'
ray rsync_up -v $RAY_CONFIG $TMP_DIR/scenes_single_scene.txt '~/scenes_single_scene.txt'

ray submit $RAY_CONFIG pipeline_ray.py $RAY_LOCATIONS_CONFIG $MCS_CONFIG

# Remove to cleanup?  or keep for debugging?
# rm -rf $TMP_DIR