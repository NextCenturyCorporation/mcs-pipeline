#!/bin/bash
# This file is intended to be run on local development machine.
# This will perform the following actions:
#  1. Start a ray cluster for the appropriate team
#  2. Upload the appropriate scenes
#  3. Upload the config files
#  4. Start the eval

# 3 parameters
# TODO make usage
DEFAULT_METADATA="level2"

TEAM=$1
LOCAL_SCENE_DIR=$2
METADATA=${3:-$DEFAULT_METADATA}

# Removing ending slash of scene dir so we have consistency
LOCAL_SCENE_DIR=$(echo $LOCAL_SCENE_DIR | sed 's:/*$::')
TMP_DIR=.tmp_pipeline_ray
RAY_CONFIG="autoscaler/ray_${TEAM}_aws.yaml"
# We probably don't need a new 'locations' file for each team
RAY_LOCATIONS_CONFIG=configs/${TEAM}_aws.ini
MCS_CONFIG=configs/mcs_config_${TEAM}_${METADATA}.ini

echo "Starting Ray Eval:"
echo "  Team:          $TEAM"
echo "  Metadata:      $METADATA"
echo "  Scene Dir:     $LOCAL_SCENE_DIR"
echo "  Ray Config:    $RAY_CONFIG"
echo "  Ray Locations: $RAY_LOCATIONS_CONFIG"
echo "  MCS config:    $MCS_CONFIG" 

mkdir -p $TMP_DIR
rm -rf $TMP_DIR/*

ORIG_PWD=$PWD

echo $LOCAL_SCENE_DIR/

for entry in $LOCAL_SCENE_DIR/*
do
  echo "`basename $entry`" >> $TMP_DIR/scenes_single_scene.txt
done

#cp -R configs $TMP_DIR
cp -R deploy_files/${TEAM}/* $TMP_DIR/
#mkdir -p $TMP_DIR/scenes/tmp
#cp -R $LOCAL_SCENE_DIR/* $TMP_DIR/scenes/tmp/



ray exec $RAY_CONFIG "mkdir -p ~/scenes/tmp/"
ray up -y $RAY_CONFIG
wait
ray rsync_up -v $RAY_CONFIG configs/ '~/configs/'
ray rsync_up -v $RAY_CONFIG deploy_files/${TEAM}/ '~'


# We should copy all the pipeline code, but at least opics needs it in a special folder.  Should ray_script handle that?  
# Should we run
ray rsync_up -v $RAY_CONFIG pipeline '~'

# this may cause re-used machines to have more scenes than necessary in the follow location.
# I believe this is ok since we use the txt file to control exactly which files are run.
ray rsync_up -v $RAY_CONFIG $LOCAL_SCENE_DIR/ '~/scenes/tmp/'
ray rsync_up -v $RAY_CONFIG $TMP_DIR/scenes_single_scene.txt '~/scenes_single_scene.txt'

ray submit $RAY_CONFIG pipeline_ray.py $RAY_LOCATIONS_CONFIG $MCS_CONFIG

# rm -rf $TMP_DIR