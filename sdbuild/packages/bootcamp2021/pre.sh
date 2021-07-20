#!/bin/bash

set -x
set -e

target=$1
script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Copy in PYNQ Peripherals
sudo mkdir -p $target/root/pynq_peripherals
sudo cp -f $script_dir/pre-built/PYNQ_peripherals-master.zip $target/root/pynq_peripherals/
