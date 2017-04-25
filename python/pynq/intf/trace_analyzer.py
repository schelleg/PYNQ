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

import os
import re
import numpy as np
from .intf_const import INTF_MICROBLAZE_BIN
from .intf import request_intf

__author__ = "Yun Rock Qu"
__copyright__ = "Copyright 2017, Xilinx"
__email__ = "pynq_support@xilinx.com"


def _bitstring_to_wave(bitstring):
    """Function to convert a pattern consisting of `0`, `1` into a sequence
    of `l`, `h`, and dots.

    For example, if the bit string is "010011000111", then the result will be
    "lhl.h.l..h..".

    Returns
    -------
    str
        New wave tokens with valid tokens and dots.

    """
    substitution_map = {'0': 'l', '1': 'h', '.': '.'}

    def insert_dots(match):
        return substitution_map[match.group()[0]] + \
            '.' * (len(match.group()) - 1)

    bit_regex = re.compile(r'[0][0]*|[1][1]*')
    return re.sub(bit_regex, insert_dots, bitstring)


class TraceAnalyzer:
    """Class for the Trace Analyzer.

    This class can capture digital IO patterns / stimulus on all the pins.
    When a pin is specified as input, the response can be captured.

    Attributes
    ----------
    if_id : int
        The interface ID (ARDUINO).

    """

    def __init__(self, if_id, num_samples=4096, trace_spec=None):
        """Return a new Arduino_PG object.

        Parameters
        ----------
        if_id : int
            The interface ID (ARDUINO).

        """
        self.intf = request_intf(if_id, INTF_MICROBLAZE_BIN)
        self.trace_spec = trace_spec
        self.num_samples = num_samples

    def config(self):

        # Get width in bytes and send to allocator held with intf Microblaze
        trace_width = round(self.trace_spec['monitor_width']/8)
        buffer_phy_addr = self.intf.allocate_buffer('trace_buf', self.num_samples,
                                             data_type=f"i{trace_width}")

        self.intf.write_control([buffer_phy_addr])
        self.intf.write_command(CMD_CONFIG_TRACE)

    def arm(self):
        self.intf.write_command(CMD_ARM_TRACE)

    def run(self):
        self.intf.write_command(CMD_RUN)

    def stop(self):
        self.intf.write_command(CMD_STOP)

    def analyze(self, trace_spec=None):
        """Analyze the captured pattern.

        This function will process the captured pattern and put the pattern
        into a Wavedrom compatible format.

        Each bit of the 20-bit patterns, from LSB to MSB, corresponds to:
        D0, D1, ..., D18 (A4), D19 (A5), respectively.

        The data output is of format:

        [{'name': '', 'pin': 'D1', 'wave': '1...0.....'},
         {'name': '', 'pin': 'D2', 'wave': '0.1..01.01'}]

        Note the all the lanes should have the same number of samples.

        Parameters
        ----------
        samples : numpy.ndarray
            A numpy array consisting of all the samples.

        Returns
        -------
        list
            A list of dictionaries, each dictionary consisting the pin number,
            and the waveform pattern in string format.

        """

        if trace_spec is not None:
            self.trace_spec = trace_spec

        if self.trace_spec is None:
            raise TypeError("Cannot Use Trace Analyzer without a valid trace_spec.")


        trace_width = round(self.trace_spec['monitor_width'] / 8)
        samples = self.intf.ndarray_from_buffer(
            'trace_buf', self.num_samples * trace_width, dtype=f'i{trace_width}')

        num_samples = len(samples)
        temp_samples = np.zeros(num_samples, dtype='>i8')
        np.copyto(temp_samples, samples)
        temp_bytes = np.frombuffer(temp_samples, dtype=np.uint8)
        bit_array = np.unpackbits(temp_bytes)
        temp_lanes = bit_array.reshape(num_samples,
                                       self.trace_spec['monitor_width']).T[::-1]
        wavelanes = list()
        for pin_label in trace_spec['input_pin_map']:
            output_lane = temp_lanes[trace_spec['output_pin_map'][pin_label]]
            input_lane = temp_lanes[trace_spec['input_pin_map'][pin_label]]
            tri_lane = temp_lanes[trace_spec['tri_pin_map'][pin_label]]
            cond_list = [tri_lane == 0, tri_lane == 1]
            choice_list = [output_lane, input_lane]
            temp_lane = np.select(cond_list, choice_list)
            bitstring = ''.join(temp_lane.astype(str).tolist())
            wave = _bitstring_to_wave(bitstring)
            wavelanes.append({'name': '', 'pin': pin_label, 'wave': wave})

        return wavelanes
