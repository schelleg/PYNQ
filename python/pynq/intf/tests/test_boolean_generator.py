#   Copyright (c) 2016, Xilinx, Inc.
#   All rights reserved.
#
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are met:
#
#   1.  Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#
#   2.  Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#   3.  Neither the name of the copyright holder nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#   AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
#   THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
#   PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
#   CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
#   EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
#   PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
#   OR BUSINESS INTERRUPTION). HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
#   WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
#   OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#   ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from random import sample
import pytest
from pynq import Overlay
from pynq.tests.util import user_answer_yes
from pynq.intf import request_intf
from pynq.intf import BooleanGenerator
from pynq.intf.intf_const import PYNQZ1_DIO_SPECIFICATION


__author__ = "Yun Rock Qu"
__copyright__ = "Copyright 2016, Xilinx"
__email__ = "pynq_support@xilinx.com"


ol = Overlay('interface.bit')


@pytest.mark.run(order=45)
def test_bool_func_1():
    """Test for the BooleanGenerator class.

    The first test will test configurations when all 5 pins of a LUT are 
    specified.

    """
    if_id = 3
    pin_dict = PYNQZ1_DIO_SPECIFICATION['output_pin_map']
    first_6_pins = [k for k in sorted(pin_dict.keys())[:6]]
    out_pin = first_6_pins[0]
    in_pins = first_6_pins[1:6]
    or_expr = out_pin + '=' + ('|'.join(in_pins))
    bool_generator = BooleanGenerator(if_id, expr=or_expr)
    bool_generator.arm()
    bool_generator.run()
    print(f'\nConnect all of {in_pins} to GND ...')
    assert user_answer_yes(f"{out_pin} outputs logic low?"), \
        "Boolean configurator fails to show logic low."
    print(f'Connect any of {in_pins} to 3V3 ...')
    assert user_answer_yes(f"{out_pin} outputs logic high?"), \
        "Boolean configurator fails to show logic high."
    del bool_generator


@pytest.mark.run(order=46)
def test_bool_func_2():
    """Test for the BooleanGenerator class.

    The second test will test the configurations when only part of the 
    LUT pins are used. Multiple instances will be tested.
    
    For simplicity, pins D0 - D4 will be used as input pins, while D5 - D9
    will be selected as output pins.

    """
    if_id = 3
    pin_dict = PYNQZ1_DIO_SPECIFICATION['output_pin_map']
    microblaze_intf = request_intf(3)
    first_10_pins = [k for k in sorted(pin_dict.keys())[:10]]
    out_pins = first_10_pins[0:5]
    in_pins = first_10_pins[5:10]
    fx = list()
    for i in range(5):
        fx.append(out_pins[i] + '=' + ('&'.join(sample(in_pins,i+1))))

    print(f'\nConnect randomly {in_pins} to 3V3 or GND.')
    bgs = [BooleanGenerator(microblaze_intf, f) for f in fx]

    # Arm all the boolean generator and run them
    for bg in bgs:
        bg.arm()
    microblaze_intf.run()

    for index in range(len(fx)):
        assert user_answer_yes(f"{fx[index]} correct?"), \
            f"Boolean generator fails to show {fx[index]}."

    # Delete all the boolean generator
    microblaze_intf.stop()
    for bg in bgs:
        del bg
