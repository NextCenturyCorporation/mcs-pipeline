#!/bin/bash

# Common code to determine if the X server is running and start it if it is not.
if pgrep -x Xorg > /dev/null
then
  echo 'X Server is running'
else
  echo "Starting X Server"
  # Note that switching from the p2.xlarge machines to g4dn.xlarge means using a Tesla T4 card,
  # instead of a K80. This is important because T4 doesn't support the --use-display-device=None
  # option that used to be specified here.

  # See "No Scanout Mode" here:
  # https://docs.nvidia.com/datacenter/tesla/tesla-release-notes-440-3301/index.html#known-issues

  sudo nvidia-xconfig --virtual=1280x1024 --output-xconfig=/etc/X11/xorg.conf --busid=PCI:0:30:0
  sudo /usr/bin/Xorg :0 1>startx-out.txt 2>startx-err.txt &
  echo "Sleeping for 20 seconds to wait for X server"
  sleep 20
  echo "Sleep finished"

  if pgrep -x Xorg > /dev/null
  then
    echo 'Successfully started X Server'
  else
    echo 'Error:  Unable to start X Server!!'
    exit 1
  fi
fi
