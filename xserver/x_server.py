#
# Code from ai2thor-docker under Apache 2.0 license.
#
# https://github.com/allenai/ai2thor-docker
#
import atexit
import os
import platform
import re
import shlex
import subprocess
import tempfile
import threading
import time


def pci_records():
    records = []
    command = shlex.split('lspci -vmm')
    output = subprocess.check_output(command).decode()

    for devices in output.strip().split("\n\n"):
        record = {}
        records.append(record)
        for row in devices.split("\n"):
            key, value = row.split("\t")
            record[key.split(':')[0]] = value

    return records


def generate_xorg_conf(devices):
    xorg_conf = []

    device_section = """
Section "Device"
    Identifier     "Device{device_id}"
    Driver         "nvidia"
    VendorName     "NVIDIA Corporation"
    BusID          "{bus_id}"
EndSection
"""
    server_layout_section = """
Section "ServerLayout"
    Identifier     "Layout0"
    {screen_records}
EndSection
"""
    screen_section = """
Section "Screen"
    Identifier     "Screen{screen_id}"
    Device         "Device{device_id}"
    DefaultDepth    24
    Option         "AllowEmptyInitialConfiguration" "True"
    SubSection     "Display"
        Depth       24
        Virtual 1024 768
    EndSubSection
EndSection
"""
    screen_records = []
    for i, bus_id in enumerate(devices):
        xorg_conf.append(device_section.format(device_id=i, bus_id=bus_id))
        xorg_conf.append(screen_section.format(device_id=i, screen_id=i))
        screen_records.append(
            'Screen {screen_id} "Screen{screen_id}" 0 0'.format(screen_id=i))

    xorg_conf.append(
        server_layout_section.format(screen_records="\n    ".join(
            screen_records)))

    output = "\n".join(xorg_conf)
    return output


def _startx(display):
    if platform.system() != 'Linux':
        raise Exception("Can only run startx on linux")

    devices = []
    for r in pci_records():
        if r.get('Vendor', '') == 'NVIDIA Corporation' and \
                r['Class'] in ['VGA compatible controller', '3D controller']:
            bus_id = 'PCI:' + ':'.join(
                map(lambda x: str(int(x, 16)), re.split(r'[:\.]', r['Slot'])))
            devices.append(bus_id)

    if not devices:
        raise Exception("no nvidia cards found")

    try:
        fd, path = tempfile.mkstemp()
        with open(path, "w") as f:
            new_xorg_conf = generate_xorg_conf(devices)
            f.write(new_xorg_conf)
            print("-------------------------")
            print("---xorg conf ------------")
            print(new_xorg_conf)
            print("-------------------------")
        command = shlex.split(
            "Xorg -noreset +extension GLX +extension RANDR +extension " +
            "RENDER -config %s :%s" % (path, display))
        print(f"Command staring x: {command}", flush=True)
        proc = subprocess.Popen(command)
        atexit.register(lambda: proc.poll() is None and proc.kill())
        proc.wait()
    finally:
        os.close(fd)
        os.unlink(path)


def startx(display=0):
    if 'DISPLAY' in os.environ:
        print("Skipping Xorg server - DISPLAY is already running at %s"
              % os.environ['DISPLAY'])
        return

    xthread = threading.Thread(target=_startx, args=(display,))
    xthread.daemon = True
    xthread.start()
    # wait for server to start
    time.sleep(4)
