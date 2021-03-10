
This directory contains code that runs an Xorg X server that does not do anything.

This is necessary when running on a remote server that does not have a display or X server.

Requirements:
* Xorg install -- 'sudo apt install xorg-server'
* lspci -- Part of PCI tools, which determine what is in the PCI (Peripheral 
Component Interconnect) buses.  'sudo apt install pcitools'
