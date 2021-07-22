#
# Bootcamp Wifi - this is specific to bootcamp2021
#                 and may not be valid after the event
#
from pynq.lib import Wifi

try:
    Wifi().connect('svvsd-iot','PYNQ21')
except:
    print("unable to connect to St. Vrain wifi.")

