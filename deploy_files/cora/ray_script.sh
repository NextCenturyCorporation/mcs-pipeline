#!/bin/bash

# Check passed mcs_config and scene file
source /home/ubuntu/check_passed_variables.sh

EVAL_DIR=/home/ubuntu/workspace
SCENE_DIR="$EVAL_DIR/scenes/"
TMP_CFG_FILE="$EVAL_DIR/msc_cfg.ini.tmp"

echo "Running CORA with config $mcs_configfile and scene $scene_file"

# Look for the CORA docker container running.  This will occur if this
# is the second or subsequent runs on this machine.  The X Server
# runs within the docker container.
CID=`docker ps -a | grep 'cora_with_x' | awk '{print $1}'`
if [ -z $CID ]; then

    # Start docker container.  It is slightly modified from the README
    # included in with CORA.

    # Start the docker container, giving it a command that never returns,
    # with -d to run in daemon mode.
    docker run \
           --rm \
           --privileged \
           -d -t \
           -v $EVAL_DIR/GenPRAM.jl:/GenPRAM.jl \
           -v $EVAL_DIR/Perception.jl:/Perception.jl \
           -v $EVAL_DIR/GenSceneGraphs.jl:/GenSceneGraphs.jl \
           -v $EVAL_DIR/PoseComposition.jl:/PoseComposition.jl \
           -v $EVAL_DIR/scenes:/scenes \
           -v $EVAL_DIR/output:/output \
           cora_with_x tail -f /dev/null

    # Get the docker container ID
    CID=`docker ps -a | grep 'cora_with_x' | awk '{print $1}'`

    # Start the X server
    docker exec -d $CID bash -c "python3 /x_server/run_startx.py"
    sleep 20
fi

# Clear out directories
echo Clearing History at $EVAL_DIR/SCENE_HISTORY/
rm -f $EVAL_DIR/SCENE_HISTORY/*
echo Clearing $SCENE_DIR
rm -rf $SCENE_DIR/*


# Move files to appropriate locations
echo Making SCENE_DIR=$SCENE_DIR
mkdir -p $SCENE_DIR
echo Moving scene_file=$scene_file to $SCENE_DIR
cp $scene_file $SCENE_DIR/

echo "Making temporary copy of config file ($mcs_configfile -> $TMP_CFG_FILE)"
cp $mcs_configfile $TMP_CFG_FILE
echo Removing old config file at $EVAL_DIR/GenPRAM.jl/GenAgent/omg/mcs_config.ini
rm $EVAL_DIR/GenPRAM.jl/GenAgent/omg/mcs_config.ini
echo Moving temporary config file to config location
mv $TMP_CFG_FILE $EVAL_DIR/GenPRAM.jl/GenAgent/omg/mcs_config.ini

# Run the Performer code
echo Starting Evaluation:
echo
scene_file_basename=$(basename $scene_file)
time docker exec $CID bash -c "MCS_CONFIG_FILE_PATH=/GenPRAM.jl/GenAgent/omg/mcs_config.ini MCS_INPUT_PATH=/scenes julia --project=@. -e '
      import Pkg;
      Pkg.develop([Pkg.PackageSpec(path=\"/GenPRAM.jl/GenAgent\"),
                   Pkg.PackageSpec(path=\"/GenPRAM.jl/JuliaMCSPhysics\"),
                   Pkg.PackageSpec(path=\"/Perception.jl\"),
                   Pkg.PackageSpec(path=\"/GenSceneGraphs.jl\"),
                   Pkg.PackageSpec(path=\"/PoseComposition.jl\")])
      using GenAgent;
      scenes = [
      \"$scene_file_basename\",
      ];
      GenAgent.main_run(scenes, \"submission\")
  ' 2>&1 | tee /output/testrun_log_$(date +%s)"


