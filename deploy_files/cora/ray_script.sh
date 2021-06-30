!/bin/bash

set -x

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


echo "Running Cora with config $mcs_configfile and scene $scene_file"


# Copy the scenes and config file to the right place
LOC=/home/ubuntu/workspace

cp $scene_file $LOC/scenes/
cp $mcs_configfile $LOC/GenPRAM.jl/GenAgent/omg/mcs_config.ini


# TODO: MCS-709 Handle:  'Exception in create_controller() Time out!' error gracefully


# Look for the CORA docker container running.  This will occur if this
# is the second or subsequent runs on this machine.
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
           -v $LOC/GenPRAM.jl:/GenPRAM.jl \
           -v $LOC/Perception.jl:/Perception.jl \
           -v $LOC/GenSceneGraphs.jl:/GenSceneGraphs.jl \
           -v $LOC/PoseComposition.jl:/PoseComposition.jl \
           -v $LOC/scenes:/scenes \
           -v $LOC/output:/output \
           cora_with_x tail -f /dev/null

    # Get the docker container ID
    CID=`docker ps -a | grep 'cora_with_x' | awk '{print $1}'`

    # Start the X server
    docker exec -d $CID bash -c "python3 /x_server/run_startx.py"
    sleep 20
fi

# Run the CORA software, using the passes mcs_config file and scene file
time docker exec $CID bash -c "MCS_CONFIG_FILE_PATH=/GenPRAM.jl/GenAgent/omg/mcs_config.ini MCS_INPUT_PATH=/scenes julia --project=@. -e '
      import Pkg;
      Pkg.develop([Pkg.PackageSpec(path=\"/GenPRAM.jl/GenAgent\"),
                   Pkg.PackageSpec(path=\"/GenPRAM.jl/JuliaMCSPhysics\"),
                   Pkg.PackageSpec(path=\"/Perception.jl\"),
                   Pkg.PackageSpec(path=\"/GenSceneGraphs.jl\"),
                   Pkg.PackageSpec(path=\"/PoseComposition.jl\")])
      using GenAgent;
      scenes = [
      \"$scene_file\",
      ];
      GenAgent.main_run(scenes, \"submission\")
  ' 2>&1 | tee /output/testrun_log_$(date +%s)"


