#!/bin/bash

# This is a command to run from the EC2 command line that will start
# up the docker container.  It is slightly modified from the README
# included in with CORA.

# We are running headless, so these have been removed 
#  -v /tmp/.X11-unix:/tmp/.X11-unix \
#  -v /tmp/.docker.xauth:/tmp/.docker.xauth \
#  -e XAUTHORITY=/tmp/.docker.xauth \
#  -e DISPLAY=$DISPLAY \

set -x

LOC=/home/ubuntu/workspace

# Start the docker container, giving it a command that never returns
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
docker exec $CID bash -c "python3 /x_server/run_startx.py &"
sleep 20 
  
  
