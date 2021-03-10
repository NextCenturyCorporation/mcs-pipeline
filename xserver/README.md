
This directory contains code that runs an Xorg X server that does not
do anything.

This is necessary when running on a remote server that does not have a
display or X server.

### Requirements

* Xorg install -- 'sudo apt install xserver-xorg'
* lspci -- Part of PCI tools, which determine what is in the PCI 
(Peripheral Component Interconnect) buses. 'sudo apt install pciutils'

### Usage

<pre>% cd xserver
% sudo python3 run_startx &</pre>

Sudo is necessary since the X server needs to be running as root.
The & is so the X server continues to run.
