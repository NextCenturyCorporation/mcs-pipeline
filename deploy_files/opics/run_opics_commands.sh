#!/bin/bash
set -m
conda activate env_pvoe
opics_eval5
sudo /usr/bin/Xorg :0 &
sudo nvidia-xconfig --use-display-device=None --virtual=600x400 --output-xconfig=/etc/X11/xorg.conf --busid=PCI:0:30:0
echo $2
cd "$1" && cp "$2" ../cfg/mcs_config.ini && python run_opics.py --scenes "$3"
