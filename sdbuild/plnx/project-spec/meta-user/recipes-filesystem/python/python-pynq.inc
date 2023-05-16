SUMMARY = "Xilinx PYNQ Library"
HOMEPAGE = "http://pynq.io"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=b42e39ad2ddbad7e8ad47f3eee6feff5"

SRC_URI[sha256sum] = "9c8833212ad91bbb8e95fb0bc76ee4f8deefff0780d02ea90845ea73afd54451"

RDEPENDS:${PN} += "\
${PYTHON_PN}-core \
${PYTHON_PN}-asyncio \
${PYTHON_PN}-cffi \
${PYTHON_PN}-json \
${PYTHON_PN}-math \
${PYTHON_PN}-mmap \
${PYTHON_PN}-multiprocessing \
${PYTHON_PN}-numpy \
${PYTHON_PN}-pycparser \
${PYTHON_PN}-resource \
${PYTHON_PN}-setuptools \
${PYTHON_PN}-threading \
${PYTHON_PN}-xml \
${PYTHON_PN}-distutils \
${PYTHON_PN}-modules \
python3-jupyter \
python3-pydantic \
python3-dataclasses \
python3-pynqmetadata \
python3-pynqutils \
lmsensors-libsensors \
libdrm \
"

DEPENDS += " libdrm boost"

PYNQ_ARCH_arm = "armv7l"
PYNQ_ARCH_aarch64 = "aarch64"
CMA_ARCH_arm = "32"
CMA_ARCH_aarch64 = "64"

SRC_URI = "gitsm://${THISDIR}/../../../../../;usehead=1;protocol=file"
SRCREV = "${AUTOREV}"


FILESEXTRAPATHS:prepend := "${THISDIR}:"
S = "${WORKDIR}/git"
INSANE_SKIP_${PN} = "staticdev"
BBCLASSEXTEND = "native nativesdk"

do_compile:prepend() {
install -d "${D}/home/root/notebooks"
export PYNQ_JUPYTER_NOTEBOOKS="${D}/home/root/notebooks"
export PYNQ_BUILD_ARCH="${PYNQ_ARCH_${TARGET_ARCH}}"
export PYNQ_BUILD_ROOT="${STAGING_DIR_TARGET}"
 (cd ${S}/sdbuild/packages/libsds/libcma && CMA_ARCH=${CMA_ARCH_${TARGET_ARCH}} make install DESTDIR=${STAGING_DIR_TARGET})

}

do_install:prepend() {
install -d "${D}/home/root/notebooks"
export PYNQ_JUPYTER_NOTEBOOKS="${D}/home/root/notebooks"
export PYNQ_BUILD_ARCH="${PYNQ_ARCH_${TARGET_ARCH}}"
export PYNQ_BUILD_ROOT="${STAGING_DIR_TARGET}"
}

do_install:append() {
 install -d ${D}${INIT_D_DIR}
 (cd ${S}/sdbuild/packages/libsds/libcma && CMA_ARCH=${CMA_ARCH_${TARGET_ARCH}} make install DESTDIR=${D})
 # rm -rf ${D}/home/root/notebooks
 rm -rf ${D}/home/root/notebooks_*
}

SOLIBS = ".so"
FILES_SOLIBSDEV = ""
FILES:${PN} += "/usr/lib/libcma.so"
FILES:${PN} += "/home/root/notebooks"
FILES:${PN}-notebooks = "/home/root/notebooks"
PACKAGES += "${PN}-notebooks"
