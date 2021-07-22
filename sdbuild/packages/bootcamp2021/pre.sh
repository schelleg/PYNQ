#!/bin/bash

set -x
set -e

target=$1
script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Copy in PYNQ Peripherals
sudo mkdir -p $target/root/pynq_peripherals
sudo cp -f $script_dir/pre-built/PYNQ_peripherals-master.zip $target/root/pynq_peripherals/

# Copy in Wifi driver
sudo mkdir -p $target/lib/modules/5.4.0-xilinx-v2020.1/kernel/drivers/net/wireless
sudo cp -f $script_dir/pre-built/8821au.ko $target/lib/modules/5.4.0-xilinx-v2020.1/kernel/drivers/net/wireless/

# Overwrite Welcome notebook
sudo cp -f $script_dir/Welcome\ to\ Pynq.ipynb $target/home/xilinx/jupyter_notebooks/
sudo cp -f $script_dir/pb_github.png $target/home/xilinx/jupyter_notebooks/

# Append Wifi access to boot.py
sudo cp $script_dir/bootcamp_wifi.py $target/usr/local/bin
