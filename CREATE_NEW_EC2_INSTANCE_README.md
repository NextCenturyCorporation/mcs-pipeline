# Create a New AWS EC2 Instance

## TA2 Development (Non-TA1)

### Launch an EC2 Instance

1. Open the EC2 dashboard: https://console.aws.amazon.com/ec2
2. Click on "Instances"
3. Click on "Launch instances"
4. Under "Application and OS Images", select "Ubuntu Server 20.04" *(You can also try one of the Deep Learning AMIs, but this documentation is not tailored to them)*
5. Under "Instance Type", select p2.xlarge
6. Under "Key Pair", select your key pair (this won't matter once you image the machine)
7. Under "Configure Storage", increase size (I used 32 GB)
8. Click "Launch Instance"
9. Wait a few minutes for it to boot
10. Right-click on your instance in the list, click "Connect", and copy the example SSH command

### Install Xorg

```
sudo apt update --fix-missing
sudo apt install xserver-xorg
sudo apt install xorg
sudo apt install nvidia-driver-440
sudo reboot
```

### On Reboot

Whenever you reboot your EC2 instance, you'll need to kill the Xorg process that starts automatically and restart it manually. Before you do this, you'll need to set the nvidia xconfig to use an incorrect BusID (I've used `PCI:0:31:0` here), so Xorg fails to restart when you kill its process (it tries to restart itself automatically). Then you'll kill the Xorg process, set the nvidia xconfig to use the correct BusID (currently `PCI:0:30:0`), and restart Xorg. (Yes, this is hacky -- feedback welcome.) Please note that sometimes `kill` prints a "usage" message because it doesn't have anything to kill -- that's OK.

```
sudo nvidia-xconfig --use-display-device=None --virtual=1280x1024 --output-xconfig=/etc/X11/xorg.conf --busid=PCI:0:31:0
sudo kill $(ps -C Xorg | grep Xorg | awk '{print $1}')
sudo nvidia-xconfig --use-display-device=None --virtual=1280x1024 --output-xconfig=/etc/X11/xorg.conf --busid=PCI:0:30:0
sudo /usr/bin/Xorg :0 &
```

If you don't start Xorg correctly, you'll see `No protocol specified` and `xdpyinfo:  unable to open display ":0.0"` error messages when you start the MCS controller.

### Install Python, Pip, and Virtual Environment

You must install python and pip outside of the python virtual environment so our pipeline code can install the ray module, then use `update-alternatives` so ray can run the `python` command (and redirect it to `python3`).

```
sudo apt install python3 python3-pip
sudo update-alternatives --install /usr/bin/python python /usr/bin/python3 10
python --version
```

MCS currently doesn't run on python 3.10 (especially if you've upgraded to Ubuntu Server 22.04), so you may need to install 3.9:

```
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.9
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 2
sudo update-alternatives --set python3 /usr/bin/python3.9
sudo apt install python3.9-venv
python3 -m venv venv
```

Otherwise, install the default python 3 venv package:

```
sudo apt install python3-venv
python3 -m venv venv
```

### Download the MCS Unity Release

Update the version tag as needed.

```
mkdir unity_app; cd unity_app
wget https://github.com/NextCenturyCorporation/MCS/releases/download/0.5.6/MCS-AI2-THOR-Unity-App-v0.5.6-linux.zip
sudo apt install unzip
unzip MCS-AI2-THOR-Unity-App-v0.5.6-linux.zip
tar -xzvf MCS-AI2-THOR-Unity-App-v0.5.6_Data.tar.gz
chmod a+x MCS-AI2-THOR-Unity-App-v0.5.6.x86_64
```

### Install the MCS Python Library

```
cd ~
source venv/bin/activate
pip install --upgrade pip setuptools wheel
deactivate
```

If you don't want to access the source code, just pip-install the machine_common_sense library:

```
cd ~
source venv/bin/activate
pip install machine_common_sense
deactivate
```

Otherwise, to access the source code, git-clone the MCS repository:

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
python MCS/machine_common_sense/scripts/run_last_action.py --mcs_unity_build_file /home/ubuntu/unity_app/MCS-AI2-THOR-Unity-App-v0.5.6.x86_64 MCS/docs/source/scenes/gravity_support_ex_01.json --debug
ls gravity_support_ex_01
deactivate
```

The `gravity_support_ex_01` folder should have all of the debug files for the run.

### Setup to Run an MCS Pipeline

Install the AWS CLI and update the corresponding pip library **outside of your python virtual environment**:

```
sudo apt install awscli
deactivate
pip install awscli==1.20.9
pip install boto3==1.18.9
pip install botocore==1.21.9
pip list | grep 'awscli\|boto3\|botocore'
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
