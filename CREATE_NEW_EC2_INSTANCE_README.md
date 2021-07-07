# Create a New AWS EC2 Instance

## TA2 Development (Non-TA1)

### Launch an EC2 Instance

1. Open the EC2 dashboard: https://console.aws.amazon.com/ec2
2. Click on "Instances"
3. Click on "Launch instances"
4. Under "Choose AMI", select "Ubuntu Server 20.04"
5. Under "Choose Instance Type", select p2.xlarge
6. Click "Next", click "Next"
7. Under "Add Storage", increase size (I used 32 GB)
8. Click "Review and Launch", click "Launch"
9. Select a key pair and click "Launch Instances"
10. Connect to your new EC2 instance via SSH

### Install Xorg

```
sudo apt update --fix-missing
sudo apt install xserver-xorg
sudo apt install xorg
sudo apt install nvidia-driver-440
sudo reboot
```

### On Reboot

Whenever you reboot your EC2 instance, you'll need to kill the Xorg process that starts automatically and restart it manually. Before you do this, you'll need to set the nvidia xconfig to use an incorrect BusID (I've used `PCI:0:31:0` here), so Xorg fails to restart when you kill its process (it tries to restart itself automatically). Then you'll kill the Xorg process, set the nvidia xconfig to use the correct BusID (currently `PCI:0:30:0`), and restart Xorg. (Yes, this is hacky -- feedback welcome.)

```
sudo nvidia-xconfig --use-display-device=None --virtual=1280x1024 --output-xconfig=/etc/X11/xorg.conf --busid=PCI:0:31:0
sudo kill $(ps -C Xorg | grep Xorg | awk '{print $1}')
sudo nvidia-xconfig --use-display-device=None --virtual=1280x1024 --output-xconfig=/etc/X11/xorg.conf --busid=PCI:0:30:0
sudo /usr/bin/Xorg :0 &
```

If you don't start Xorg correctly, you'll see `No protocol specified` and `xdpyinfo:  unable to open display ":0.0"` error messages when you start the MCS controller.

### Download the MCS Unity Release

Update the version tag as needed.

```
mkdir unity_app; cd unity_app
wget https://github.com/NextCenturyCorporation/MCS/releases/download/0.4.3/MCS-AI2-THOR-Unity-App-v0.4.3-linux.zip
unzip MCS-AI2-THOR-Unity-App-v0.4.3-linux.zip
tar -xzvf MCS-AI2-THOR-Unity-App-v0.4.3_Data.tar.gz
chmod a+x MCS-AI2-THOR-Unity-App-v0.4.3.x86_64
```

### Install the MCS Python Library

```
cd ~
sudo apt install python3-venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
```

If you don't want to access the source code, just pip-install the library:

```
pip install git+https://github.com/NextCenturyCorporation/MCS@master#egg=machine_common_sense
```

If you want to access the source code, then git-clone the MCS repository:

```
git clone https://github.com/NextCenturyCorporation/MCS.git
cd MCS
pip install -e .
```

You can use a scene file from the source code to test your installation. For example:

```
python MCS/scripts/run_last_action.py --mcs_unity_build_file /home/ubuntu/unity_app/MCS-AI2-THOR-Unity-App-v0.4.3.x86_64 MCS/docs/source/scenes/gravity_support_ex_01.json --debug
ls gravity_support_ex_01
```

### Other Setup

You can git-clone other repositories, like maybe mcs-pipeline:

```
cd ~
git clone https://github.com/NextCenturyCorporation/mcs-pipeline.git
```

You can install other linux packages, like the AWS CLI:

```
sudo apt install awscli
```

Or maybe ffmpeg for making videos:

```
sudo apt install ffmpeg
```

