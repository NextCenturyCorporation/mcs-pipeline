#!/bin/bash
# This file is intended to be run on local development machine (driver machine).
# This will perform the following actions:
#  1. Start a ray cluster for the appropriate module
#  2. Upload the appropriate scenes
#  3. Upload the config files
#  4. Start the eval

#
# Usage: run_eval <module> <scene_folder> [--metadata <metadata_level>] [--resume] 
#    [--cluster_suffix] [--disable_validation]
#  module: the module to use to know where to look for files in the configs and 
#    deploy_files folders.  Typical modules are opics, baseline, cora, mess
#  scene_folder: folder containing the files exist to run through the pipeline.  
#    Typically these are scene files, but they don't need to be.
#  metadata_level: metadata level to run MCS at
#  resume: Signals the head node to attempt to resume its last run.  This just removes
#    files that the head node recorded as completed in its last run.  
#  cluster_suffix: Adds a suffix to the cluster name already in the ray configuration
#    yaml file.  A new copy of the configuration will be put in .ray_configs/.  This 
#    is useful to run multiple clusters using the same yaml file.  For example, running
#    a bunch of clusters for different sets of files and/or metadata levels.
#  workers: override number of workers
#  disable_validation: Disables the validation on the MCS configuration.  Useful when
#    testing or running against the development infrastructure.
{
MODULE=$1
TMP_DIR=.tmp_pipeline_ray

# We probably don't need a new 'locations' file for each team in evals
RAY_LOCATIONS_CONFIG=configs/${MODULE}_aws.ini

mkdir -p $TMP_DIR
rm -rf $TMP_DIR/*

cp -R deploy_files/${MODULE}/* $TMP_DIR/

RAY_CONFIG="autoscaler/ray_${MODULE}_aws.yaml"


####### STARTING EVAL SPECIFIC CODE ########

# Handle inputs:

DEFAULT_METADATA="level2"
LOCAL_SCENE_DIR=$2
# Removing ending slash of scene dir so we have consistency
LOCAL_SCENE_DIR=$(echo $LOCAL_SCENE_DIR | sed 's:/*$::')
METADATA=${METADATA:-$DEFAULT_METADATA}
SUBMIT_PARAMS=''
WORKERS=""

# Parse optional --parameters
while [ $# -gt 0 ]; do
    if [[ $1 == *"--"* ]]; then
        if [ $1 == "--disable_validation" ] ; then
            SUBMIT_PARAMS="$SUBMIT_PARAMS $1"
        elif [ $1 == "--resume" ] ; then
            SUBMIT_PARAMS="$SUBMIT_PARAMS $1"
        elif [ $1 == "--dev_validation" ] ; then
            SUBMIT_PARAMS="$SUBMIT_PARAMS $1"
        else
            # this takes care of any flags with parameters such as metadata
            uppercase_param=$(echo "$1" | tr '[:lower:]' '[:upper:]')
            param="${uppercase_param/--/}"
            declare $param="$2"
            shift
        fi
   fi
   shift
done

# If the user assigns a cluster suffix, the code below will create a copy of 
# the config file and append this suffix to the existing cluster_name:  The 
# script will put that file in .ray_configs/ in case the user needs it later 
# for shutdown, attach, etc.

if [ -n "$CLUSTER_SUFFIX" ] || [ -n :"$WORKERS" ]; then
    mkdir -p .ray-configs
    # Copy config and add suffix
    CFG_SUFFIX=$CLUSTER_SUFFIX-$WORKERS
    CFG_FILE="$(basename "${RAY_CONFIG}")"
    CFG_DIR="$(dirname "${RAY_CONFIG}")"
    NEW_CFG=".ray-configs/${CFG_FILE%.yaml}-$CFG_SUFFIX.yaml"
    cat $RAY_CONFIG > $NEW_CFG

    if [ -n "$CLUSTER_SUFFIX" ]; then
        CL=`grep cluster_name: $NEW_CFG`
        NEW_CLUSTER_LINE="$CL-$CLUSTER_SUFFIX"
        sed -i "s/cluster_name:\s*\S*/$NEW_CLUSTER_LINE/g" $NEW_CFG
        RAY_CONFIG=$NEW_CFG

        echo "Replaced cluster name line with:"
        echo "  `grep cluster_name: $NEW_CFG`"
    fi

    if [ -n "$WORKERS" ]; then
        MW=`grep -m 1 max_workers: $NEW_CFG`
        NEW_WORKERS_LINE="max_workers: $WORKERS"
        sed -i "s/$MW/$NEW_WORKERS_LINE/g" $NEW_CFG
        RAY_CONFIG=$NEW_CFG

        echo "Replaced max workers name line with:"
        echo "  `grep -m 1 max_workers: $NEW_CFG`"
    fi
fi

ray up -y $RAY_CONFIG
wait

# We should copy all the pipeline code, but at least opics needs it in a special folder.  Should ray_script handle that?  
# Should we run
ray rsync_up -v $RAY_CONFIG pipeline '~'
ray rsync_up -v $RAY_CONFIG deploy_files/${MODULE}/ '~'
ray rsync_up -v $RAY_CONFIG configs/ '~/configs/'


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
