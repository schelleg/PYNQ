SRC_URI += " file://pynq.cfg"
SRC_URI += " file://greengrass.cfg"
SRC_URI += " file://wifi.cfg"
SRC_URI += " file://usb_serial.cfg"
SRC_URI += " file://gpio-xilinx.patch"
SRC_URI += " file://docker.cfg
FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"
