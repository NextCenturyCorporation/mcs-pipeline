#!/bin/bash
# This file is intended to be run on local development machine (driver machine).
# This will perform the following actions:
#  1. Start a ray cluster for the appropriate module
#  2. Upload the appropriate scenes
#  3. Upload the config files
#  4. Start the eval
{
MODULE=$1
TMP_DIR=.tmp_pipeline_ray

# We probably don't need a new 'locations' file for each team in evals
RAY_LOCATIONS_CONFIG=configs/${MODULE}_aws.ini

mkdir -p $TMP_DIR
rm -rf $TMP_DIR/*

cp -R deploy_files/${MODULE}/* $TMP_DIR/

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
METADATA=${METADATA:-$DEFAULT_METADATA}
SUBMIT_PARAMS=''

# Parse optional --parameters
while [ $# -gt 0 ]; do
    if [[ $1 == *"--"* ]]; then
        if [ $1 == "--disable_validation" ] ; then
            SUBMIT_PARAMS="$SUBMIT_PARAMS $1"
        elif [ $1 == "--resume" ] ; then
            SUBMIT_PARAMS="$SUBMIT_PARAMS $1"
        else
            uppercase_param=$(echo "$1" | tr '[:lower:]' '[:upper:]')
            param="${uppercase_param/--/}"
            declare $param="$2"
        fi
   fi
   shift
done

MCS_CONFIG=configs/mcs_config_${MODULE}_${METADATA}.ini

source aws_scripts/load_ini.sh $RAY_LOCATIONS_CONFIG

# Create necessary files:

# Create list of scenes for head node to run.  All scenes will also be rsync'ed.
for entry in $LOCAL_SCENE_DIR/*
do
  echo "`basename $entry`" >> $TMP_DIR/scenes_single_scene.txt
done

# Debug info

echo "Starting Ray Eval:"
echo "  Module:             $MODULE"
echo "  Metadata:           $METADATA"
echo "  Scene Dir:          $LOCAL_SCENE_DIR"
echo "  Ray Config:         $RAY_CONFIG"
echo "  Ray Locations:      $RAY_LOCATIONS_CONFIG"
echo "  MCS config:         $MCS_CONFIG"
echo "  Skip Validate Flag: $VALIDATE_CONFIG"

ray exec $RAY_CONFIG "mkdir -p $MCS_scene_location"

# this may cause re-used machines to have more scenes than necessary in the follow location.
# I believe this is ok since we use the txt file to control exactly which files are run.

ray rsync_up -v $RAY_CONFIG $LOCAL_SCENE_DIR/ "$MCS_scene_location"
ray rsync_up -v $RAY_CONFIG $TMP_DIR/scenes_single_scene.txt "$MCS_scene_list"

ray submit $RAY_CONFIG pipeline_ray.py $RAY_LOCATIONS_CONFIG $MCS_CONFIG $SUBMIT_PARAMS


# Remove to cleanup?  or keep for debugging?
# rm -rf $TMP_DIR
} 
