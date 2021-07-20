#!/bin/bash

set -x
set -e

. /etc/environment
export HOME=/root
export BOARD=${PYNQ_BOARD}

# Make sure its a v2.6.2 release
BOARD=${PYNQ_BOARD} PYNQ_JUPYTER_NOTEBOOKS=${PYNQ_JUPYTER_NOTEBOOKS} \
python3.6 -m pip install pynq==2.6.2

# install pynq_peripherals
pushd /root/pynq_peripherals
unzip PYNQ_peripherals-master.zip
cd PYNQ_peripherals-master
python3.6 -m pip install .
popd
rm -rf /root/pynq_peripherals

# get notebooks into jupyter home
# fix to make sure /dev/xlnk exists so pynq CLI completes
cd /home/xilinx/jupyter_notebooks
if [ ! -f /dev/xlnk ]; then
    touch /dev/xlnk
    pynq get-notebooks pynq_peripherals -p .
    rm /dev/xlnk
else
    pynq get-notebooks pynq_peripherals -p .
fi
