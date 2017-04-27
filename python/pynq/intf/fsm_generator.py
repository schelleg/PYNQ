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
from copy import deepcopy
from math import ceil, log
import numpy as np
import pygraphviz as pgv
from IPython.display import Image, display
from .intf_const import FSM_BRAM_ADDR_WIDTH
from .intf_const import FSM_MAX_STATE_BITS
from .intf_const import FSM_MAX_INPUT_BITS
from .intf_const import FSM_MAX_STATE_INPUT_BITS
from .intf_const import FSM_MAX_OUTPUT_BITS
from .intf_const import INTF_MICROBLAZE_BIN
from .intf_const import PYNQZ1_DIO_SPECIFICATION
from .intf_const import CMD_CONFIG_SMG,CMD_ARM_SMG,CMD_RUN,IOSWITCH_SMG_SELECT,CMD_STOP
from .intf import request_intf
from .trace_analyzer import TraceAnalyzer
from .waveform import Waveform


__author__ = "Yun Rock Qu"
__copyright__ = "Copyright 2017, Xilinx"
__email__ = "pynq_support@xilinx.com"




class FSMGenerator:
    """Class for Finite State Machine Generator.

    This class enables users to specify a Finite State Machine (FSM). Users
    have to provide a FSM in the following format.

    fsm_spec = {'inputs': [('reset','D0'), ('direction','D1')],
    'outputs': [('alpha','D3'), ('beta','D4'), ('gamma','D5')],
    'states': ('S0', 'S1', 'S2', 'S3', 'S4', 'S5'),
    'transitions': [['00', 'S0', 'S1', '000'],
                    ['01', 'S0', 'S5', '000'],
                    ['00', 'S1', 'S2', '001'],
                    ['01', 'S1', 'S0', '001'],
                    ['00', 'S2', 'S3', '010'],
                    ['01', 'S2', 'S1', '010'],
                    ['00', 'S3', 'S4', '011'],
                    ['01', 'S3', 'S2', '011'],
                    ['00', 'S4', 'S5', '100'],
                    ['01', 'S4', 'S3', '100'],
                    ['00', 'S5', 'S0', '101'],
                    ['01', 'S5', 'S4', '101'],
                    ['1-', '*',  'S0', '']]}

    The current implementation assumes Moore machine, so the output is decided
    by the current state. Hence, if a wildcard `*` is specified for the
    current state, users can just set the output to be empty.

    Attributes
    ----------
    if_id : int
        The interface ID (ARDUINO).
    intf : _INTF
        INTF instance used by Arduino_PG class.
    num_input_bits : int
        The number of input bits / pins.
    num_outputs : int
        The number of possible FSM outputs specified by users.
    num_output_bits : int
        The number of bits used for the FSM outputs.
    num_states : int
        The number of FSM states specified by users.
    num_state_bits : int
        The number of bits used for the FSM states.
    state_names : list
        List of state names specified by the users.
    transitions : int
        Transition list with all the wildcards replaced properly.
    input_pins : list
        List of input pins on Arduino header.
    output_pins : list
        List of output pins on Arduino header.
    running : bool
        Flag indicating whether the FSM is currently running.
    use_state_bits : bool
        Flag indicating whether the state bits are shown on output pins.
    analyzer : PatternAnalyzer
        Analyzer to analyze the raw capture from the pins.
    data_samples: numpy.ndarray
        The numpy array storing the response, each sample being 64 bits.
    waveform : Waveform
        The Waveform object used for Wavedrom display.

    """

    def __init__(self, if_id, fsm_spec=None,
                 intf_spec=PYNQZ1_DIO_SPECIFICATION, use_analyzer=True, use_state_bits=False, num_analyzer_samples=4096):
        """Initialize the FSM generator class.

        Users can specify the `fsm_spec` when instantiating the object, or
        provide this specification later, and call `parse_fsm_spec()`.

        The attribute `data_samples` will only be non-empty if analyzer is
        used, i.e., `use_analyzer` is set to True.

        If `use_state_bits` is set to True, the state bits will be shown as
        outputs. The last few outputs may get replaced by state bits,
        regardless of the specification users provide. For example, if 3
        bits are required for state codes (e.g. a state code 110), and the
        last 3 outputs from `fsm_spec` are: ('alpha','D2'), ('beta','D4'),
        and ('gamma','D19'), then pin `D2`, `D4`, and `D19` will show the
        state code (continuing the example above, `D2` = 1, `D4` = 1,
        `D19` = 0). Other outputs remain consistent with users' specification.

        The waveform instance will not get populated until the `fsm_spec` is
        parsed.

        Parameters
        ----------
        if_id : int
            The interface ID (ARDUINO).
        fsm_spec : dict
            The FSM specification, with inputs (list), outputs (list),
            states (list), and transitions (list).
        use_analyzer : bool
            Indicate whether to use the analyzer to capture the trace as well.
        use_state_bits : bool
            Whether to check the state bits in the final output pins.

        """

        self.if_id = if_id
        self.intf = request_intf(if_id, INTF_MICROBLAZE_BIN)
        self.intf_spec = intf_spec
        self.num_input_bits = 0
        self.num_outputs = 0
        self.num_output_bits = 0
        self.num_states = 0
        self.num_state_bits = 0
        self.state_names = list()
        self.transitions = list()
        self.input_pins = list()
        self.output_pins = list()
        self.running = False
        self.use_state_bits = use_state_bits
        self.data_samples = None
        self.waveform = None

        self._state_names2codes = dict()
        self._state_names2outputs = dict()
        self._expanded_transitions = list()
        self._encoded_transitions = list()
        self._bram_data = np.zeros(2 ** FSM_BRAM_ADDR_WIDTH, dtype=np.uint32)

        if use_analyzer:
            self.analyzer = TraceAnalyzer(if_id,num_samples=num_analyzer_samples, trace_spec=intf_spec)
        else:
            self.analyzer = None

        if fsm_spec:
            self.fsm_spec = self._parse_fsm_spec(fsm_spec, use_state_bits)
        else:
            self.fsm_spec = None

    def _parse_fsm_spec(self, fsm_spec_in, use_state_bits):
        """Parse a given FSM specification.

        This method can be called during initialization, or by users.

        If `use_state_bits` is set to True, this method will modify the
        given transition table; the last few outputs may get altered if
        there are not enough pins for both state bits and output bits.
        In that case, the last few output bits will reflect the current
        state code.

        Parameters
        ----------
        fsm_spec_in : dict
            The FSM specification, with inputs (list), outputs (list),
            states (list), and transitions (list).
        use_state_bits : bool
            Whether to check the state bits in the final output pins.

        Returns
        -------
        dict
            A modified dictionary if `use_state_bits` is set to True.

        """
        fsm_spec = deepcopy(fsm_spec_in)
        self.use_state_bits = use_state_bits

        # The key 'inputs', 'outputs', and 'states' are mandatory
        for key in ['inputs', 'outputs', 'states']:
            self._check_duplicate(fsm_spec, key)

        self.num_input_bits = len(fsm_spec['inputs'])
        self.num_outputs = len(set([i[3] for i in fsm_spec['transitions']
                                    if i[3]]))
        self.num_output_bits = len(fsm_spec['outputs'])
        self.num_states = len(fsm_spec['states'])
        self.num_state_bits = ceil(log(self.num_states, 2))
        self.input_pins = [i[1] for i in fsm_spec['inputs']]
        self.output_pins = [i[1] for i in fsm_spec['outputs']]

        self._check_num_bits(self.num_input_bits, 'inputs', FSM_MAX_INPUT_BITS)
        self._check_num_bits(self.num_output_bits, 'outputs', FSM_MAX_OUTPUT_BITS)
        self._check_num_bits(self.num_state_bits, 'states', FSM_MAX_STATE_BITS)
        self._check_num_bits(self.num_input_bits + self.num_state_bits,
                       'states and inputs', FSM_MAX_STATE_INPUT_BITS)
        self._check_moore(self.num_states, self.num_outputs)
        self._check_pins(fsm_spec, 'inputs')
        self._check_pins(fsm_spec, 'outputs')

        self.state_names = fsm_spec['states']
        self._state_names2codes = {
            state_name: format(i, '0{}b'.format(self.num_state_bits))
            for i, state_name in enumerate(fsm_spec['states'])}

        if self.use_state_bits:
            # Update outputs
            state_pins = list()
            total_pins_used = self.input_pins[:] + self.output_pins[:]
            num_pins_altered = 0
            for bit in range(self.num_state_bits):
                output_bit_name = 'state_bit' + str(bit)
                found_pin = False
                for pin in self.intf_spec['output_pin_map']:
                    if pin not in total_pins_used:
                        state_pins = [(output_bit_name, pin)] + state_pins
                        total_pins_used.append(pin)
                        found_pin = True
                        break
                if not found_pin:
                    num_pins_altered += 1
                    temp_tuple = fsm_spec['outputs'][-num_pins_altered]
                    fsm_spec['outputs'][-num_pins_altered] = (output_bit_name,
                                                              temp_tuple[1])
            fsm_spec['outputs'] += state_pins

            # Update transitions
            for index, row in enumerate(fsm_spec['transitions']):
                _, current_state, _, old_output = row
                if old_output:
                    current_state_code = self._state_names2codes[current_state]
                    new_output = ''.join(merge_to_length(
                                            list(old_output),
                                            list(current_state_code),
                                            20 - self.num_input_bits))
                    fsm_spec['transitions'][index][-1] = new_output

            # Update all the attributes related to outputs and transitions
            self.num_outputs = len(set([i[3] for i in fsm_spec['transitions']
                                        if i[3]]))
            self.num_output_bits = len(fsm_spec['outputs'])
            self.output_pins = [i[1] for i in fsm_spec['outputs']]

        self._state_names2outputs = {
            state_name: row[3] for row in fsm_spec['transitions']
            for state_name in fsm_spec['states'] if state_name == row[1]}
        self.transitions, self._expanded_transitions = \
            self._expand_all_transitions(fsm_spec['transitions'])
        self._encoded_transitions = [[i[0],
                                      self._state_names2codes[i[1]],
                                      self._state_names2codes[i[2]],
                                      i[3]]
                                     for i in self._expanded_transitions]
        self.input_pins = [i[1] for i in fsm_spec['inputs']]
        self.output_pins = [i[1] for i in fsm_spec['outputs']]
        self._check_pin_conflict(self.input_pins, self.output_pins)

        waveform_dict = {'signal': [
            ['analysis']],
            'foot': {'tock': 1},
            'head': {'tick': 1, 'text': 'Finite State Machine'}}
        for name, pin in (fsm_spec['inputs'] + fsm_spec['outputs']):
            waveform_dict['signal'][0].append({'name': name, 'pin': pin})
        self.waveform = Waveform(waveform_dict, analysis_name='analysis')

        return fsm_spec

    def _expand_all_transitions(self, transitions):
        """Expand all the state transitions, resolving wildcards.

        This method will resolve all the wildcards in inputs and states.
        For example: [['1-', '*', 'S0', '']] will be converted to
        [['10', 'S1', 'S0', ''],['11', 'S1', 'S0', '']], ...].

        This method is called internally during initialization of this class.

        Parameters
        ----------
        transitions: list
            List of lists, where each inner list specifies a state transition.

        Returns
        -------
        list,list
            First list has all the state wildcards '*' expanded; second list
            has the state wildcards '*' and input wildcards '-' both
            expanded.

        """
        # Expand the states first
        transitions_copy1 = deepcopy(transitions)
        for index, row in enumerate(transitions_copy1):
            if row[1] == '*':
                for state_name in self.state_names:
                    if row[2] != state_name:
                        new_row = deepcopy(transitions_copy1[index])
                        new_row[1] = state_name
                        new_row[3] = self._state_names2outputs[state_name]
                        transitions_copy1.append(new_row)
        transitions_copy1 = [row for row in transitions_copy1
                             if '*' not in row[1]]

        # Expand the input values
        transitions_copy2 = deepcopy(transitions_copy1)
        for index, row in enumerate(transitions_copy2):
            input_list = list(row[0])
            wildcard = '-'
            if wildcard in input_list:
                zero_list, one_list = self._replace_wildcard(input_list)
                if zero_list:
                    new_row = deepcopy(transitions_copy2[index])
                    transitions_copy2.append(self._expand_transition(new_row,
                                                               zero_list))
                    transitions_copy2.append(self._expand_transition(new_row,
                                                               one_list))
        expanded_transitions = list()
        for row in transitions_copy2:
            if '-' not in row[0] and row not in expanded_transitions:
                expanded_transitions.append(row)
        return transitions_copy1, expanded_transitions

    def _config_load_buffer(self):
        """Load the BRAM data into the main memory.

        This method prepares the data to be loaded into BRAM: it first loads
        the data into main memory as a numpy array, with all the values set
        to be default; then based on the transactions specified, it updates
        the memory with proper values.

        After this method is called, users can manually check the memory
        content to verify the memory is loaded with correct values.

        For the memory content to be loaded, it has the following format:
        Bits 31 - 13 : used for outputs.
        Bits 12 - 9  : used for inputs.
        Bits 8 - 5   : used for inputs or states.
        Bits 4 - 0   : used for states.

        """
        _, addr_offsets = self._get_bram_addr_offsets(self.num_states,
                                                self.num_input_bits)
        # Load default values into BRAM data
        for input_value, offset_addr in enumerate(addr_offsets):
            for state_name in self.state_names:
                output_value = int(''.join(list(
                            self._state_names2outputs[state_name])[::-1]), 2)
                next_state_code = current_state_code = \
                    int(self._state_names2codes[state_name], 2)
                self._bram_data[offset_addr + current_state_code] = \
                    (output_value << FSM_MAX_STATE_INPUT_BITS) + \
                    next_state_code

        # Update BRAM data based on state transitions
        for input_value, offset_addr in enumerate(addr_offsets):
            for transition in self._encoded_transitions:
                if input_value == int(transition[0], 2):
                    current_state_code, next_state_code, output_value = \
                        int(transition[1], 2),\
                        int(transition[2], 2),\
                        int(''.join(list(transition[3])[::-1]), 2)
                    self._bram_data[offset_addr + current_state_code] = \
                        (output_value << FSM_MAX_STATE_INPUT_BITS) + \
                        next_state_code


    def _config_ioswitch(self):

        # gather which pins are being used
        ioswitch_pins = [self.intf_spec['output_pin_map'][ins[1]] for ins in self.fsm_spec['inputs']]
        ioswitch_pins.extend([self.intf_spec['output_pin_map'][outs[1]] for outs in self.fsm_spec['outputs']])

        # send list to intf processor for handling
        self.intf.config_ioswitch(ioswitch_pins,IOSWITCH_SMG_SELECT)


    def config(self, frequency_mhz=10):
        """Configure the programmable FSM generator.

        This method will configure the FSM based on supplied configuration specification.
        The `data_samples` will get updated after the pattern is captured.
        Users can send the samples to PatternAnalyzer for additional
        analysis.

        Parameters
        ----------
        num_samples : int
            The number of samples to be captured on FSM outputs.
        frequency_mhz: float
            The frequency of the FSM and captured samples, in MHz.

        """
        # Set the FSM frequency
        self.intf.clk.fclk1_mhz = frequency_mhz

        self._config_ioswitch()

        # Load BRAM data into the main memory
        self._config_load_buffer()
        bram_data_addr = self.intf.allocate_buffer('bram_data_buf',
                                                   2 ** FSM_BRAM_ADDR_WIDTH,
                                                   data_type='unsigned int')

        for index, data in enumerate(self._bram_data):
            self.intf.buffers['bram_data_buf'][index] = data

        # Setup configurations
        config = list()
        index_offset, _ = self._get_bram_addr_offsets(self.num_states,
                                                self.num_input_bits)

        # Configuration for bit 8,7,6,5 (slvreg 0)
        config_shared_pins = 0x1f1f1f1f
        shared_input_bits = min(self.num_input_bits, 9 - index_offset)
        if 5 <= index_offset <= 8:
            for i in range(shared_input_bits):
                config_shared_pins = ((config_shared_pins << 8) +
                                      (0x80 + self.intf_spec['output_pin_map'][
                                          self.input_pins[i]])) & \
                                      0xffffffff
            for i in range(5, index_offset):
                config_shared_pins = ((config_shared_pins << 8) + 0x1f) & \
                    0xffffffff
        config.append(config_shared_pins)

        # Configuration for bit 12,11,10,9 (slvreg 1)
        config_input_pins = 0x1f1f1f1f
        if 9 <= index_offset <= 12:
            if self.num_input_bits > shared_input_bits:
                dedicated_input_bits = self.num_input_bits - shared_input_bits
                for i in range(dedicated_input_bits):
                    config_input_pins = ((config_input_pins << 8) +
                                         (0x80 + self.intf_spec['output_pin_map'][
                                             self.input_pins[
                                                 i + shared_input_bits]])) & \
                                        0xffffffff
        config.append(config_input_pins)

        # Configuration for bit 31 - 13 (slvreg 6,5,4,3,2)
        fully_used_reg, remaining_pins = divmod(self.num_output_bits, 4)
        assigned_output_pins = 0
        for j in range(fully_used_reg):
            config_output_pins = 0x0
            for i in range(3, -1, -1):
                config_output_pins = ((config_output_pins << 8) +
                                      self.intf_spec['output_pin_map'][
                    self.output_pins[i + assigned_output_pins]]) & \
                    0xffffffff
            assigned_output_pins += 4
            config.append(config_output_pins)

        for j in range(fully_used_reg, 5):
            config_output_pins = 0x0
            if j == fully_used_reg:
                for i in range(remaining_pins-1, -1, -1):
                    config_output_pins = ((config_output_pins << 8) +
                                          self.intf_spec['output_pin_map'][
                        self.output_pins[i + assigned_output_pins]]) & \
                        0xffffffff
                assigned_output_pins += remaining_pins
            config.append(config_output_pins)

        # Configuration for direction mask
        direction_mask = 0xfffff
        for pin in range(20):
            for pin_label in self.output_pins:
                if self.intf_spec['output_pin_map'][pin_label] == pin:
                    direction_mask &= (~(1 << pin))
        config.append(direction_mask)

        # Send BRAM data address
        config.append(bram_data_addr)

        # Wait for the interface processor to return control
        self.intf.write_control(config)
        self.intf.write_command(CMD_CONFIG_SMG)
        self.running = True

        # configure the tracebuffer
        if self.analyzer is not None:
            self.analyzer.config()

        # Free the BRAM buffer
        self.intf.free_buffer('bram_data_buf')

    def arm(self):
        self.intf.write_command(CMD_ARM_SMG)

        if self.analyzer is not None:
            self.analyzer.arm()

    def stop(self):
        """Stop the FSM pattern generator.

        Note this command will stop the pattern generation from FSM, so
        users will see all-zero samples captured unless the FSM is started
        again.

        This function should be called if a new `fsm_spec` is provided.

        """
        self.intf.write_command(CMD_STOP)


    def start(self):
        """Start generating patterns or capturing the trace only.

        If there are existing FSM running on Microblaze, this method will
        just capture the samples, instead of reloading the BRAM data. If users
        want to restart the FSM using a different `fsm_spec`, the `stop()`
        and `parse_fsm_spec()` methods should be called manually.

        If there is no FSM running, this method will call `start()` method
        internally.

        Parameters
        ----------
        num_samples : int
            The number of samples to be captured on FSM outputs.
        frequency_mhz: float
            The frequency of the FSM and captured samples, in MHz.

        """
        self.intf.write_command(CMD_RUN)


    def display_graph(self, file_name='fsm_spec.png'):
        """Display the state machine in Jupyter notebook.

        This method uses the installed package `pygraphviz`. References:
        http://pygraphviz.github.io/documentation/latest/pygraphviz.pdf

        A PNG file of the state machine will also be saved into the current
        working directory.

        Parameters
        ----------
        file_name : str
            The name / path of the picture for the FSM diagram.

        """
        with open('fsm_spec.dot', 'w') as f:
            f.write("digraph {\n" +
                    "    graph [fontsize=10 splines=true overlap=false]\n" +
                    "    edge  [fontsize=10 fontname=\"helvetica\"]\n" +
                    "    node  [fontsize=10 fontname=\"helvetica\"" +
                    " nodesep=2.0]\n" +
                    "    ratio=auto\n")
            for i in self._state_names2outputs:
                f.write(('    \"' + i + ' &#8260; ' +
                         self._state_names2outputs[i]) + '\"\n')
            for row in self.transitions:
                f.write(
                    '    \"' + row[1] + ' &#8260; ' +
                    self._state_names2outputs[row[1]] + '\" -> \"' +
                    row[2] + ' &#8260; ' +
                    self._state_names2outputs[row[2]] + "\" [label=\"" +
                    row[0] + "\" arrowhead = \"vee\"]\n")
            f.write("}")

        graph = pgv.AGraph('fsm_spec.dot')
        graph.layout(prog='dot')
        graph.draw(file_name)
        display(Image(filename=file_name))
        os.system("rm -rf fsm_spec.dot")

    def display(self):

        if self.analyzer is not None:
            analysis_group = self.analyzer.analyze()
            self.waveform.update('analysis', analysis_group)
        else:
            print("Trace disabled, please enable, rerun FSM, and run display().")

        self.waveform.display()


    def _check_pins(self, fsm_spec, key):
        """Check whether the pins specified are in a valid range.

        This method will raise an exception if `pin` is out of range.

        Parameters
        ----------
        fsm_spec : dict
            The dictionary where the check to be made.
        key : object
            The key to index the dictionary.

        """
        for i in fsm_spec[key]:
            if i[1] not in self.intf_spec['output_pin_map']:
                raise ValueError(f"{i[1]} not in output pin map - please check against fsm_spec")


    def _check_num_bits(self, num_bits, label, maximum):
        """Check whether the number of bits are still in a valid range.

        This method will raise an exception if `num_bits` is out of range.

        Parameters
        ----------
        num_bits : int
            The number of bits of a specific field.
        label : str
            The label of the field.
        maximum : int
            The maximum number of bits allowed in that field.

        """
        if num_bits > maximum:
            raise ValueError(f'{label} used more than the maximum number ' +
                             f'({maximum}) of bits allowed.')


    def _check_moore(self, num_states, num_outputs):
        """Check whether the specified state machine is a moore machine.

        This method will raise an exception if there are more state outputs
        than the number of states.

        Parameters
        ----------
        num_states : int
            The number of bits used for states.
        num_outputs : int
            The number of state outputs.

        """
        if num_states < num_outputs:
            raise ValueError("Specified FSM is not Moore: " +
                             "{} states but {} outputs.".format(num_states,
                                                                num_outputs))


    def _check_duplicate(self, fsm_spec, key):
        """Function to check duplicate entries in a nested dictionary.

        This method will check the entry indexed by key in a dictionary. An
        exception will be raised if there are duplicated entries.

        Parameters
        ----------
        fsm_spec : dict
            The dictionary where the check to be made.
        key : object
            The key to index the dictionary.

        """
        if key == 'inputs' or key == 'outputs':
            name_list = [pair[0] for pair in fsm_spec[key]]
            pin_list = [pair[1] for pair in fsm_spec[key]]
            if len(set(name_list)) < len(name_list):
                raise ValueError('Duplicate names in {}.'.format(key))
            if len(set(pin_list)) < len(pin_list):
                raise ValueError('Duplicate pins in {}.'.format(key))
        else:
            entries = [item for item in fsm_spec[key]]
            if len(set(entries)) < len(entries):
                raise ValueError('Duplicate entries in {}.'.format(key))


    def _check_pin_conflict(self, pins1, pins2):
        """Function to check whether there is conflict between input / output pins.

        This method will raise an exception if there are pins specified in both
        inputs and outputs.

        Parameters
        ----------
        pins1 : list
            The list of the first set of pins.
        pins2 : list
            The list of the second set of pins.

        """
        if not set(pins1).isdisjoint(pins2):
            raise ValueError('I/O pin conflicts: {} and {}.'.format(pins1, pins2))


    def _replace_wildcard(self, input_list):
        """Method to replace a wildcard `-` in the input values.

        This method will replace the wildcard `-` in the input list; the returned
        two lists have different values on the position of `-`.

        Example: ['0', '-', '1'] => (['0', '0', '1'], ['0', '1', '1'])

        Parameters
        ----------
        input_list : list
            A list of multiple values, possibly with `-` inside.

        Returns
        -------
        list,list
            Two lists differ by the location of `-`.

        """
        if '-' in input_list:
            first_occurrence = input_list.index('-')
            zero_list = input_list[:]
            zero_list[first_occurrence] = '0'
            one_list = input_list[:]
            one_list[first_occurrence] = '1'
            return zero_list, one_list
        else:
            return None, None


    def _expand_transition(self, transition, input_list):
        """Add new (partially) expanded state transition.

        Parameters
        ----------
        transition: list
            Specifies a state transition.
        input_list: list
            List of inputs, where each input is a string.

        Returns
        -------
        list
            New (partially) expanded state transition.

        """
        expanded_transition = list()
        expanded_transition.append(''.join(input_list))
        expanded_transition += transition[1:]
        return expanded_transition


    def _merge_to_length(self, a, b, length):
        """Merge 2 lists into a specific length.

        This method will merge 2 lists into a short list, replacing the last few
        items of the first list if necessary.

        For example, a = [1,2,3], b = [4,5,6,7], and length = 6. The result will
        be [1,2,4,5,6,7]. If length = 5, the result will be [1,4,5,6,7]. If length
        is greater or equal to 7, the result will be [1,2,3,4,5,6,7].

        Parameters
        ----------
        a : list
            A list of elements.
        b : list
            Another list of elements.
        length : int
            The length of the result list.

        Returns
        -------
        list
            A merged list of the specified length.

        """
        temp = b[:]
        for index, item in enumerate(a):
            if len(temp) < length:
                temp.insert(index, item)
            else:
                break
        return temp


    def _get_bram_addr_offsets(self, num_states, num_input_bits):
        """Get address offsets from given number of states and inputs.

        This method returns the index offset for input bits. For example, if less
        than 32 states are used, then the index offset will be 5. If the number
        of states used is greater than 32 but less than 64, then the index offset
        will be 6.

        This method also returns the address offsets for BRAM data. The returned
        list contains 2**`num_input_bits` offsets. The distance between 2 address
        offsets is 2**`index_offset`.

        Parameters
        ----------
        num_states : int
            The number of states in the state machine.
        num_input_bits : int
            The number of inputs in the state machine.

        Returns
        -------
        int, list
            A list of 2**`num_input_bits` offsets.

        """
        if num_states < 32:
            index_offset = 5
        else:
            index_offset = ceil(log(num_states, 2))
        return index_offset, \
            [i * 2 ** index_offset for i in range(2 ** num_input_bits)]
