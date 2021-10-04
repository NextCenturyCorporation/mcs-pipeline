# Create a New AWS EC2 Instance

## TA2 Development (Non-TA1)

### Launch an EC2 Instance

1. Open the EC2 dashboard: https://console.aws.amazon.com/ec2
2. Click on "Instances"
3. Click on "Launch instances"
4. Under "Choose AMI", select "Ubuntu Server 20.04" *(You can also try one of the Deep Learning AMIs, but this documentation is not tailored to them.)*
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
wget https://github.com/NextCenturyCorporation/MCS/releases/download/0.4.5/MCS-AI2-THOR-Unity-App-v0.4.5-linux.zip
unzip MCS-AI2-THOR-Unity-App-v0.4.5-linux.zip
tar -xzvf MCS-AI2-THOR-Unity-App-v0.4.5_Data.tar.gz
chmod a+x MCS-AI2-THOR-Unity-App-v0.4.5.x86_64
```

### Install the MCS Python Library

```
cd ~
sudo apt install python3-venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
deactivate
```

If you don't want to access the source code, just pip-install the library:

```
source venv/bin/activate
pip install git+https://github.com/NextCenturyCorporation/MCS@master#egg=machine_common_sense
deactivate
```

If you want to access the source code, then git-clone the MCS repository:

```
cd ~
source venv/bin/activate
git clone https://github.com/NextCenturyCorporation/MCS.git
cd MCS
pip install -e .
deactivate
```

You can use a scene file from the source code to test your installation. For example:

```
cd ~
source venv/bin/activate
python MCS/scripts/run_last_action.py --mcs_unity_build_file /home/ubuntu/unity_app/MCS-AI2-THOR-Unity-App-v0.4.5.x86_64 MCS/docs/source/scenes/gravity_support_ex_01.json --debug
ls gravity_support_ex_01
deactivate
```

The `gravity_support_ex_01` folder should have all of the debug files for the run.

### Install Python and Pip

You must install python and pip outside of the python virtual environment so our pipeline code can install the ray module, then use `update-alternatives` so ray can run the `python` command (and redirect it to `python3`).

```
sudo apt install python3 python3-pip
sudo update-alternatives --install /usr/bin/python python /usr/bin/python3 10
```

### Setup to Run an MCS Evaluation

Install the AWS CLI and update the corresponding pip library outside of your python virtual environment:

```
sudo apt install awscli
pip3 install --upgrade awscli
```

Install ffmpeg to make output videos:

```
sudo apt install ffmpeg
```

### Other Setup

You can git-clone other repositories, like maybe mcs-pipeline:

```
cd ~
git clone https://github.com/NextCenturyCorporation/mcs-pipeline.git
```

## Create AMI

In the AWS EC2 Dashboard, under Instances, right-click your instance, then click "Images and templates" => "Create image". Give it a useful name and description, and then click the "Create image" button.

Leave your instance running while the image is being created! You can stop the instance after the AMI is created.

You should see your pending AMI in the AMIs tab on the EC2 Dashboard. You can use it once it becomes available.
