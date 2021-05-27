export HOME=/root

set -x
set -e


# cat > requirements.txt <<EOT
# numpy
# pybind11
# EOT

python3 -m pip install pip==21.0.1
# python3 -m pip install -r requirements.txt
# rm requirements.txt
