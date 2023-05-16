#!/bin/bash

set -e
set -x

source ../common/2022.1.sh
date > timestamps.log

export BUILDROOT=`pwd`
export PLNXPROJNAME=plnx
export PROJPATH_PARENT=$BUILDROOT/PYNQ/sdbuild
export PROJPATH=$PROJPATH_PARENT/$PLNXPROJNAME
export BSP=/opt/grahams/plnx_pynq/bsps/xilinx-zcu104-v2022.1-final.bsp



if [ ! -d "PYNQ" ]; then
    # git clone --recursive https://github.com/xilinx/PYNQ
    git clone --recursive https://github.com/schelleg/PYNQ -b plnx_20221_3.0.1
fi


pushd $PROJPATH_PARENT
petalinux-create -t project -n $PLNXPROJNAME -s $BSP
popd



#echo 'CONFIG_USER_LAYER_0="'$PROJPATH_PARENT/boot/meta-pynq'"' >> $PROJPATH/project-spec/configs/config
# echo "CONFIG_SUBSYSTEM_ROOTFS_EXT4=y" >> $PROJPATH/project-spec/configs/config

#echo 'CONFIG_SUBSYSTEM_SDROOT_DEV="/dev/mmcblk0p2"' >> $PROJPATH/project-spec/configs/config
# echo 'CONFIG_SUBSYSTEM_ETHERNET_MANUAL_SELECT=y' >> $PROJPATH/project-spec/configs/config

#echo 'CONFIG_SUBSYSTEM_DEVICETREE_FLAGS="-@"' >> $PROJPATH/project-spec/configs/config
#echo 'CONFIG_SUBSYSTEM_DTB_OVERLAY=y' >> $PROJPATH/project-spec/configs/config
#echo 'CONFIG_SUBSYSTEM_FPGA_MANAGER=y' >> $PROJPATH/project-spec/configs/config

#echo "CONFIG_python3-pynq"    >> $PROJPATH/project-spec/meta-user/conf/user-rootfsconfig
#echo "CONFIG_python3-pynq=y"  >> $PROJPATH/project-spec/configs/rootfs_config

echo "CONFIG_python3-pip"     >> $PROJPATH/project-spec/meta-user/conf/user-rootfsconfig
echo "CONFIG_python3-pip=y"   >> $PROJPATH/project-spec/configs/rootfs_config

# maybe don't need this since we have a BSP?
# echo "CONFIG_SUBSYSTEM_REMOVE_PL_DTB=y" >> $PROJPATH/project-spec/configs/config

# commenting out since using the ZCU104 PYNQ BSP (post BSP strip and repackage)
# clean meta-user contents with PYNQ contents
# cp -r $BUILDROOT/PYNQ/boards/ZCU104/petalinux_bsp/* $PROJPATH/project-spec/
# rm -rf $PROJPATH/components
# rm -rf $PROJPATH/hardware
# rm -rf $PROJPATH/pre-built

# get rid of the python3-pynq_2.5.1 recipes (just to make sure they are not found)
# rm -rf $PROJPATH/components/yocto/layers/meta-xilinx/meta-xilinx-pynq/recipes-devtool/python/python*

pushd $PROJPATH
petalinux-config --silentconfig
petalinux-build 
petalinux-package --boot --u-boot --fpga 
petalinux-package --wic
popd


BOARD=ZCU104
VERSION=PLNXv3.0.1
boardname=$(echo ${BOARD} | tr '[:upper:]' '[:lower:]' | tr - _)
timestamp=$(date +'%Y_%m_%d')
imagefile=${boardname}_${timestamp}_plnx.img
zipfile=${boardname}_${timestamp}.zip
mv $PROJPATH/images/linux/petalinux-sdimage.wic $imagefile
zip -j $zipfile $imagefile
mv $zipfile /group/xrlabs2/grahams/plnx/

date >> timestamps.log
cat timestamps.log



# Other features that could get added in for verification
# echo "CONFIG_python3-pip"     >> $PROJPATH/project-spec/meta-user/conf/user-rootfsconfig
# echo "CONFIG_python3-pip=y"   >> $PROJPATH/project-spec/configs/rootfs_config

# echo "CONFIG_python3-pytest"     >> $PROJPATH/project-spec/meta-user/conf/user-rootfsconfig
# echo "CONFIG_python3-pytest=y"   >> $PROJPATH/project-spec/configs/rootfs_config

# cat $PROJPATH/project-spec/configs/rootfs_config

