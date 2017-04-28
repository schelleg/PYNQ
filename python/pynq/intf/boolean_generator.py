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
from pyeda.inter import exprvar
from pyeda.inter import expr2truthtable
from pynq import Register
from .intf_const import INTF_MICROBLAZE_BIN, PYNQZ1_DIO_SPECIFICATION,CMD_READ_CFG_DIRECTION,MAILBOX_OFFSET,CMD_CONFIG_CFG, CMD_ARM_CFG, CMD_RUN, CMD_STOP,IOSWITCH_BG_SELECT
from .intf import request_intf, _INTF
from .trace_analyzer import TraceAnalyzer
from .waveform import Waveform

__author__ = "Yun Rock Qu"
__copyright__ = "Copyright 2017, Xilinx"
__email__ = "pynq_support@xilinx.com"


# IN_PINS = [['D0', 'D1', 'D2', 'D3'],
#            ['D5', 'D6', 'D7', 'D8'],
#            ['D10', 'D11', 'D12', 'D13'],
#            ['A1', 'A2', 'A3', 'A4'],
#            ['PB0', 'PB1', 'PB2', 'PB3']]
# OUT_PINS = ['D4', 'D9', 'A0', 'A5']
# LD_PINS = ['LD0', 'LD1', 'LD2', 'LD3', 'LD4', 'LD5']
# ARDUINO_CFG_PROGRAM = "arduino_intf.bin"


class BooleanGenerator:
    """Class for the Combinational Function Generator.

    This class can implement any combinational function on user IO pins. A
    typical function implemented for a bank of 5 pins can be 4-input and
    1-output. However, by connecting pins across different banks, users can
    implement more complex functions with more input/output pins.

    Attributes
    ----------
    if_id : int
        The interface ID (ARDUINO).
    intf : _INTF
        INTF instance used by Arduino_CFG class.
    expr : str
        The boolean expression in string format.
    led : bool
        Whether LED is used to indicate output.
    verbose : bool
        Whether to show verbose message to users.

    """

    def __init__(self, intf_microblaze, expr=None, intf_spec=PYNQZ1_DIO_SPECIFICATION, use_analyzer = True, num_analyzer_samples = 4096):
        """Return a new Arduino_CFG object.

        For ARDUINO, the available input pins are data pins (D0-D13, A0-A5),
        the onboard push buttons (PB0-PB3). The available output pins are
        D4, D9, A0, A5, and the onboard LEDs (LD0-LD5).

        Bank 0:
        input 0 - 3: D0 - D3; output: D4/LD0.

        Bank 1:
        input 0 - 3: D5 - D8; output: D9/LD1.

        Bank 2:
        input 0 - 3: D10 - D13; output: A0/LD2.

        Bank 3:
        input 0 - 3: A1 - A4; output: A5/LD3.

        Bank 4:
        input 0 - 3: PB0 - PB3; output: LD4

        The input boolean expression can be of the following formats:
        (1) `D0 & D1 | D2`, or
        (2) `D4 = D0 & D1 | D2`.

        If no input boolean expression is specified, the default function
        implemented is `D0 & D1 & D2 & D3`.

        Note
        ----
        When LED is used as the output indicator, an LED on indicates the
        corresponding output is logic high.

        Parameters
        ----------
        if_id : int
            The interface ID (ARDUINO).
        expr : str
            The boolean expression in a string.
        led : bool
            Whether LED is used to indicate output; defaults to true.
        verbose : bool
            Whether to show verbose message to users.

        """

        if isinstance(intf_microblaze, _INTF):
            self.intf = intf_microblaze
        elif isinstance(intf_microblaze, int):
            self.intf = request_intf(intf_microblaze, INTF_MICROBLAZE_BIN)
        else:
            raise TypeError("intf_microblaze has to be a intf._INTF or int type.")

        self.expr = expr
        self.intf_spec = intf_spec
        self.waveform = None
        self.output_pin = None
        self.input_pins = None


        if expr is not None:
            self.config(expr)

        if use_analyzer is not None:
            self.analyzer = TraceAnalyzer(self.intf, num_samples=num_analyzer_samples, trace_spec=intf_spec)
        else:
            self.analyzer = None


    def _config_ioswitch(self):

        # gather which pins are being used
        ioswitch_pins = [self.intf_spec['output_pin_map'][ins] for ins in self.input_pins]
        ioswitch_pins.append(self.intf_spec['output_pin_map'][self.output_pin])

        # send list to intf processor for handling
        self.intf.config_ioswitch(ioswitch_pins,IOSWITCH_BG_SELECT)


    def config(self, expr):
        """Configure the CFG with new boolean expression or LED indicator.

        Implements boolean function at specified IO pins with optional led
        output.

        Parameters
        ----------
        expr : str
            The new boolean expression.
        led : bool
            Show boolean function output on onboard LED, defaults to true

        Returns
        -------
        None

        """
        if not isinstance(expr, str):
            raise TypeError("Boolean expression has to be a string.")

        if "=" not in expr:
            raise ValueError("Boolean expression must have form OUTPUT_PIN = Expression")

        self.expr = expr

        # parse boolean expression into output & input string
        expr_out, expr_in = expr.split("=")
        expr_out = expr_out.strip()
        if expr_out in self.intf_spec['output_pin_map']:
            self.output_pin = expr_out
            output_pin_num = self.intf_spec['output_pin_map'][self.output_pin]
        else:
            raise ValueError(f"Invalid output pin {expr_out}.")

        # parse the used pins
        self.input_pins = re.sub("\W+", " ", expr_in).strip().split(' ')
        input_pins_with_dontcares = self.input_pins[:]


        print(f"input_pins {self.input_pins}")

        # need 5 inputs to a CFGLUT - any unspecified inputs will be don't cares
        for i in range(len(self.input_pins),5):
            expr_in = f'({expr_in} & X{i})|({expr_in} & ~X{i})'
            input_pins_with_dontcares.append(f'X{i}')

        print(f"{input_pins_with_dontcares} {expr_in} ")


        # map to truth table
        p0, p1, p2, p3, p4 = map(exprvar, input_pins_with_dontcares)
        expr_p = expr_in

        print(f"{p0} {p1} {p2} {p3} {p4} {expr_p}")

        # Replace pin names with p* in order
        for orig_name,p_name in zip(input_pins_with_dontcares, [f'p{i}' for i in range(5)]):
            expr_p = expr_p.replace(orig_name, p_name)

        truth_table = expr2truthtable(eval(expr_p))

        print(f'truth_table {truth_table}')

        # parse truth table to send
        truth_list = str(truth_table).split("\n")
        truth_num = 0
        for i in range(32, 0, -1):
            truth_num = (truth_num << 1) + int(truth_list[i][-1])

        # Set the IO Switch
        self._config_ioswitch()

        # Get current BG bit enables
        mailbox_addr = self.intf.addr_base + MAILBOX_OFFSET
        mailbox_regs = [Register(addr) for addr in range(mailbox_addr,mailbox_addr+4*64,4)]
        self.intf.write_command(CMD_READ_CFG_DIRECTION)
        print(f" pre enables {mailbox_regs[0][31:0]}")
        bg_bitenables = mailbox_regs[0]

        # generate the input select, the truth table, and bit enable
        for i in range(5):
            lsb=i*5
            msb=(i+1)*5-1
            if input_pins_with_dontcares[i] in self.input_pins:
                input_pin_ix = self.intf_spec['output_pin_map'][input_pins_with_dontcares[i]]
            else:
                input_pin_ix = 0x1f
            mailbox_regs[output_pin_num*2][msb:lsb] = input_pin_ix
        mailbox_regs[output_pin_num * 2 + 1][31:0] = truth_num
        mailbox_regs[48][31:0] = 0xffffffff & ~(1 << output_pin_num)
        #mailbox_regs[48] = bg_bitenables & ~(1 << output_pin_num)
        mailbox_regs[49][output_pin_num] = 1

        print("Config words")
        print(f"{mailbox_regs[output_pin_num*2]}")
        print(f"{mailbox_regs[output_pin_num * 2 + 1]}")
        print(f"{mailbox_regs[48]}")
        print(f"{bg_bitenables}")

        print(f"{mailbox_regs[49]}")



        # construct the command word
        self.intf.write_command(CMD_CONFIG_CFG)

        # configure the tracebuffer
        if self.analyzer is not None:
            self.analyzer.config()

    def arm(self):
        self.intf.write_command(CMD_ARM_CFG)

        if self.analyzer is not None:
            self.analyzer.arm()

    def run(self):
        self.intf.write_command(CMD_RUN)

    def stop(self):
        self.intf.write_command(CMD_STOP)

    def display(self):
        """Display the boolean logic generation in a Jupyter notebook.

        A wavedrom waveform is shown with all inputs and outputs displayed.

        """
        # setup waveform view - stimulus from input wires, response on output wires
        waveform_dict = {'signal': [
            ['stimulus'],
            ['response']],
            'foot': {'tick': 1},
            'head': {'tick': 1, 'text': f'Boolean Logic Generator ({self.expr})'}}

        # append four inputs and one output to waveform view (name and label are identical here)
        for name in self.input_pins:
            waveform_dict['signal'][0].append({'name': name, 'pin': name})

        for name in [self.output_pin]:
            waveform_dict['signal'][1].append({'name': name, 'pin': name})

        display_waveform = Waveform(waveform_dict, stimulus_name='stimulus',analysis_name='response')

        if self.analyzer is not None:
            analysis_group = self.analyzer.analyze()
            display_waveform.update('stimulus', analysis_group)
            display_waveform.update('response', analysis_group)
        else:
            print("Trace disabled, please enable, rerun FSM, and run display().")


        display_waveform.display()

