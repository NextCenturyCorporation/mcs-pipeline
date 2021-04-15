#!/bin/bash

# This is a command that gets the docker container (assumed to already running)
# and runs the CORA software on it. 

set -x


# Get the docker container ID
CID=`docker ps -a | grep 'cora_with_x' | awk '{print $1}'`

# Run the CORA software
time docker exec $CID bash -c "MCS_CONFIG_FILE_PATH=/GenPRAM.jl/GenAgent/omg/config_level2.ini MCS_INPUT_PATH=/scenes julia --project=@. -e '
      import Pkg;
      Pkg.develop([Pkg.PackageSpec(path=\"/GenPRAM.jl/GenAgent\"),
                   Pkg.PackageSpec(path=\"/GenPRAM.jl/JuliaMCSPhysics\"),
                   Pkg.PackageSpec(path=\"/Perception.jl\"),
                   Pkg.PackageSpec(path=\"/GenSceneGraphs.jl\"),
                   Pkg.PackageSpec(path=\"/PoseComposition.jl\")])
      using GenAgent;
      scenes = [
      \"gravity_support_ex_05.json\",
      ];
      GenAgent.main_run(scenes, \"submission\")
  ' 2>&1 | tee /output/testrun_log_$(date +%s)"
