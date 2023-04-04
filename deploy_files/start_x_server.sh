#!/bin/bash

# Common code to determine if the X server is running and start it if it is not.
if pgrep -x Xorg > /dev/null
then
  echo 'X Server is running'
else
  echo "Starting X Server"
  # FOR CORA - they modify /etc/X11/xorg.conf, so dont run xconfig
  # Need to redirect logs of background tasks or the script doesn't
  sudo /usr/bin/Xorg :4 -config /etc/X11/xorg.conf 1>startx-out.txt 2>startx-err.txt &
  echo "Sleeping for 20 seconds to wait for X server"
  sleep 20
  echo "Sleep finished"

  if pgrep -x Xorg > /dev/null
  then
    echo 'Successfully started X Server'
  else
    echo "Sleeping for another 20 seconds to wait for X server"
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
fi


echo "Starting jax env"
source /home/ubuntu/anaconda3/etc/profile.d/conda.sh
conda activate jax

# if pgrep -f "python server.py" > /dev/null
# then
#   echo 'Vision server is running'
# else
#   echo "Starting server.py"
#   cd /home/ubuntu/jax3dp3/experiments/multiprocess || exit
#   # Need to redirect logs of background tasks or the script doesn't
#   python server.py 1 >pyserver-out.txt 2>pyserver-err.txt &
#   echo "Sleeping for 20 seconds to wait for vision server"
#   sleep 20
# fi

# if pgrep -f "python physics_server.py" > /dev/null
# then
#   echo 'Physics server is running'
# else
#   echo "Starting physics_server.py"
#   cd /home/ubuntu/CoraAgent/src/MCS/Physics || exit
#   # Need to redirect logs of background tasks or the script doesn't
#   python physics_server.py 1 >physserver-out.txt 2>physserver-err.txt &
#   echo "Sleeping for 20 seconds to wait for physics server"
#   sleep 20
# fi


if pgrep -f "python ./run_physics_server.py" > /dev/null
then
  echo 'Physics server is running'
else
  echo "Starting run_physics_server.py"
  cd /home/ubuntu/jax3dp3/scripts || exit
  # Need to redirect logs of background tasks or the script doesn't
  python ./run_physics_server.py 1 >physserver-out.txt 2>physserver-err.txt &
  echo "Sleeping for 20 seconds to wait for physics server"
  sleep 20
fi
