#!/bin/bash
set -m
echo Running Commands from run_opics_commands.sh
opics_eval5
cd "$1" && cp "$2" ../cfg/mcs_config.ini && bash -i ./opics_iter.sh "$3"
