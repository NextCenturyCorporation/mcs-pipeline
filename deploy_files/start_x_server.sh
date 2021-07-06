#!/bin/bash

# Common code to determine if the X server is running and start it if it is not.

XPROCESS=`ps aux | grep 'sudo /usr/bin/Xorg :0' | grep -v grep | awk '{print $1}'`
if [ -z $XPROCESS ]; then
  echo 'X Server is running'
else
  echo "Starting X Server"
  sudo nvidia-xconfig --use-display-device=None --virtual=1280x1024 --output-xconfig=/etc/X11/xorg.conf --busid=PCI:0:30:0
  sudo /usr/bin/Xorg :0 &
  echo "Sleeping for 20 seconds to wait for X server"
  sleep 20
  echo "Sleep finished"

  XPROCESS=`ps aux | grep 'sudo /usr/bin/Xorg :0' | grep -v grep | awk '{print $1}'`
  if [ -z $XPROCESS ]; then
    echo 'Successfully started X Server'
  else
    echo 'Error:  Unable to start X Server!!'
  fi
fi







# Start X
# TODO:  Check to see if the xserver is already running and do not restart
cd mcs-pipeline/xserver
sudo nohup python3 run_startx.py 1>startx-out.txt 2>startx-err.txt &
sleep 20
