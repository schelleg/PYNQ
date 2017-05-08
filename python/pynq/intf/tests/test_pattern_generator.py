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


from random import randint
from copy import deepcopy
import pytest
from pynq import Overlay
from pynq.intf import PatternGenerator
from pynq.intf.pattern_generator import wave_to_bitstring
from pynq.intf.intf_const import PYNQZ1_DIO_SPECIFICATION
from pynq.intf.intf_const import MAX_NUM_PATTERN_SAMPLES


__author__ = "Yun Rock Qu"
__copyright__ = "Copyright 2016, Xilinx"
__email__ = "pynq_support@xilinx.com"


ol = Overlay('interface.bit')
if_id = 3


@pytest.mark.run(order=49)
def test_pattern_generator_clk():
    """Test for the PatternGenerator class.

    The first test will test a set of loopback signals. Each lane is
    simulating a clock of a specific frequency.

    """
    num_samples = 128
    loopback1 = {'signal': [
        ['stimulus'],
        {},
        ['analysis']],
        'foot': {'tock': 1, 'text': 'Loopback Test'},
        'head': {'tick': 1, 'text': 'Loopback Test'}}

    pin_dict = PYNQZ1_DIO_SPECIFICATION['output_pin_map']
    interface_width = PYNQZ1_DIO_SPECIFICATION['interface_width']
    all_pins = [k for k in list(pin_dict.keys())[:interface_width]]
    for i in range(interface_width):
        wavelane1 = dict()
        wavelane2 = dict()
        wavelane1['name'] = f'clk{i}'
        wavelane2['name'] = f'clk{i}'
        wavelane1['pin'] = all_pins[i]
        wavelane2['pin'] = all_pins[i]
        loopback1['signal'][-1].append(wavelane2)
        if i % 4 == 0:
            wavelane1['wave'] = 'lh' * int(num_samples / 2)
        elif i % 4 == 1:
            wavelane1['wave'] = 'l.h.' * int(num_samples / 4)
        elif i % 4 == 2:
            wavelane1['wave'] = 'l...h...' * int(num_samples / 8)
        else:
            wavelane1['wave'] = 'l.......h.......' * int(num_samples / 16)
        loopback1['signal'][0].append(wavelane1)

    pg = PatternGenerator(if_id, loopback1,
                          stimulus_name='stimulus',
                          analysis_name='analysis',
                          use_analyzer=True,
                          num_analyzer_samples=num_samples)
    pg.config()
    assert 'src_buf' not in pg.intf.buffers, \
        'src_buf is not freed after use.'
    pg.arm()
    pg.run()
    pg.display()
    pg.stop()
    loopback2 = pg.waveform.waveform_dict

    list1 = list2 = list3 = list()
    for wavelane_group in loopback1['signal']:
        if wavelane_group and wavelane_group[0] == 'stimulus':
            list1 = wavelane_group[1:]

    for wavelane_group in loopback2['signal']:
        if wavelane_group and wavelane_group[0] == 'stimulus':
            list2 = wavelane_group[1:]
        elif wavelane_group and wavelane_group[0] == 'analysis':
            list3 = wavelane_group[1:]

    assert list1 == list2, \
        'Stimulus not equal in generated and captured patterns.'
    assert list2 == list3, \
        'Stimulus not equal to analysis in captured patterns.'

    pg0 = PatternGenerator(if_id, loopback1,
                          use_analyzer=False,
                          num_analyzer_samples=num_samples)
    exception_raised = False
    try:
        pg0.display()
    except ValueError:
        exception_raised = True
    assert exception_raised, 'Should raise exception for display().'

    pg.intf.reset_buffers()
    del pg, pg0


@pytest.mark.run(order=50)
def test_pattern_generator_wave():
    """Test for the PatternGenerator class.

    The test will examine 0 sample and more than the maximum number of samples.
    In these cases, exception should be raised.

    """
    for num_samples in [0, MAX_NUM_PATTERN_SAMPLES+1]:
        loopback1 = {'signal': [
            ['stimulus'],
            {},
            ['analysis']],
            'foot': {'tock': 1, 'text': 'Loopback Test'},
            'head': {'tick': 1, 'text': 'Loopback Test'}}
    
        pin_dict = PYNQZ1_DIO_SPECIFICATION['output_pin_map']
        interface_width = PYNQZ1_DIO_SPECIFICATION['interface_width']
        all_pins = [k for k in list(pin_dict.keys())[:interface_width]]
        for i in range(interface_width):
            wavelane1 = dict()
            wavelane2 = dict()
            wavelane1['name'] = f'signal{i}'
            wavelane2['name'] = f'signal{i}'
            wavelane1['pin'] = all_pins[i]
            wavelane2['pin'] = all_pins[i]
            loopback1['signal'][-1].append(wavelane2)
            if i % 2 == 0:
                wavelane1['wave'] = 'l' * num_samples
            else:
                wavelane1['wave'] = 'h' * num_samples
            loopback1['signal'][0].append(wavelane1)

        exception_raised = False
        pg = None
        try:
            pg = PatternGenerator(if_id, loopback1,
                                  use_analyzer=True,
                                  num_analyzer_samples=num_samples)
        except ValueError:
            exception_raised = True
        finally:
            if pg:
                pg.intf.reset_buffers()
                del pg
        assert exception_raised, 'Should raise exception if number of ' \
                                 'samples is out of range.'


@pytest.mark.run(order=51)
def test_pattern_generator_random():
    """Test for the PatternGenerator class.

    The test will examine 1 sample, and a maximum number of samples.
    For theses cases, random signals will be used.

    For all the tests, all the pins will be used to generate the pattern.

    """
    for num_samples in [1, MAX_NUM_PATTERN_SAMPLES]:
        loopback1 = {'signal': [
            ['stimulus'],
            {},
            ['analysis']],
            'foot': {'tock': 1, 'text': 'Loopback Test'},
            'head': {'tick': 1, 'text': 'Loopback Test'}}

        pin_dict = PYNQZ1_DIO_SPECIFICATION['output_pin_map']
        interface_width = PYNQZ1_DIO_SPECIFICATION['interface_width']
        all_pins = [k for k in list(pin_dict.keys())[:interface_width]]
        for i in range(interface_width):
            wavelane1 = dict()
            wavelane2 = dict()
            wavelane1['name'] = f'signal{i}'
            wavelane2['name'] = f'signal{i}'
            wavelane1['pin'] = all_pins[i]
            wavelane2['pin'] = all_pins[i]
            loopback1['signal'][-1].append(wavelane2)
            rand_list = [str(randint(0,1)) for _ in range(num_samples)]
            rand_str = ''.join(rand_list)
            wavelane1['wave'] = rand_str.replace('0','l').replace('1','h')
            loopback1['signal'][0].append(wavelane1)

        pg = PatternGenerator(if_id, loopback1,
                              use_analyzer=True,
                              num_analyzer_samples=num_samples)
        pg.config()
        pg.arm()
        pg.run()
        pg.display()
        pg.stop()
        loopback2 = pg.waveform.waveform_dict

        list1 = list2 = list3 = list()
        for wavelane_group in loopback1['signal']:
            if wavelane_group and wavelane_group[0] == 'stimulus':
                for i in wavelane_group[1:]:
                    temp = deepcopy(i)
                    temp['wave'] = wave_to_bitstring(i['wave'])
                    list1.append(temp)

        for wavelane_group in loopback2['signal']:
            if wavelane_group and wavelane_group[0] == 'stimulus':
                for i in wavelane_group[1:]:
                    temp = deepcopy(i)
                    temp['wave'] = wave_to_bitstring(i['wave'])
                    list2.append(temp)
            elif wavelane_group and wavelane_group[0] == 'analysis':
                for i in wavelane_group[1:]:
                    temp = deepcopy(i)
                    temp['wave'] = wave_to_bitstring(i['wave'])
                    list3.append(temp)

        assert list1 == list2, \
            'Stimulus not equal in generated and captured patterns.'
        assert list2 == list3, \
            'Stimulus not equal to analysis in captured patterns.'

        pg.intf.reset_buffers()
        del pg

    ol.reset()

