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
rm -rf /home/xilinx/jupyter_notebooks/*.dat

# install extra requirements for apps/ notebooks
apt update
apt install -y flac
apt install -y portaudio19-dev
python3.6 -m pip install jupyterplot
python3.6 -m pip install pyaudio
python3.6 -m pip install SpeechRecognition
python3.6 -m pip install gtts

# Append to boot.py the bootcamp Wifi ssid/password
cat /usr/local/bin/bootcamp_wifi.py >> /boot/boot.py
