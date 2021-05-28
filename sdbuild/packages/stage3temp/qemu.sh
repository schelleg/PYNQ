# Set up some environment variables as /etc/environment
# isn't sourced in chroot

set -e
set -x

. /etc/environment
export HOME=/root
export BOARD=${PYNQ_BOARD}

# cpio not installed in the image?
#   apt-get hanging on focal inside QEMU
#   cpio exists on bionic (PYNQ v.26)
# apt-get install -y cpio

# TODO: Replace source install when possible - adds ~10 minutes to build
wget https://ftp.gnu.org/gnu/cpio/cpio-2.13.tar.gz
tar xvzf cpio-2.13.tar.gz
cd cpio-2.13
./configure
make
make install

cd ..
rm -rf cpio-2.13
