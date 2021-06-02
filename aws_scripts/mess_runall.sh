#!/bin/bash

# Script to run all the scene files in the scenes/ directory.
# Note the calling of conda.sh and conda activate; necessary
# because by default the script does not inherit all the
# conda setup.

source /home/ubuntu/anaconda3/etc/profile.d/conda.sh
conda activate myenv

for taskfile in `find . -name '*.json' | grep 'scenes/' | sort`
do
    echo "---------------------------------------------------------"
    echo "Scene: " $taskfile
    python3 script_mess.py $taskfile
done

