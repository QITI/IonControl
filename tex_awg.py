#!/usr/bin/env python
"""Module for communication with and translation of data with a tektronix AWG5000 series.

06.2018 Modified by Simon Hmupohl
"""
__version__ = "0.2.1"

from typing import Sequence, Union, Optional, Tuple, Iterable, cast, Callable, Any
import types
from collections import OrderedDict
import itertools
import re
import warnings

import pyvisa
from pyvisa.resources.messagebased import MessageBasedResource
import numpy as np


def _get_chunked(iterable, chunk_size):
    iterator = iter(iterable)

    while True:
        chunk = itertools.islice(iterator, chunk_size)

        try:
            first_element = next(chunk)
        except StopIteration:
            return

        yield itertools.chain((first_element, ), chunk)


class Waveform:
    """This class bundles all the stuff for binary formatting. It is hashable and therefore immutable."""
    real_t = types.SimpleNamespace(dtype=np.dtype([('channel', 'f'), ('marker', 'B')]),
                                   marker_1_mask=np.uint8(2 ** 6),
                                   marker_2_mask=np.uint8(2 ** 7))

    int_t = types.SimpleNamespace(dtype=np.uint16,
                                  marker_1_mask=np.uint16(2 ** 14),
                                  marker_2_mask=np.uint16(2 ** 15),
                                  channel_mask=np.uint16(2**14 - 1))

    def __init__(self,
                 channel: np.ndarray,
                 marker_1: Union[np.ndarray, int],
                 marker_2: Union[np.ndarray, int]):
        if channel.dtype != np.float32 and channel.dtype != np.uint16:
            raise TypeError('Channel must be uint16 or float32')

        if isinstance(marker_1, int):
            marker_1 = np.array([marker_1])

        if isinstance(marker_2, int):
            marker_2 = np.array([marker_2])

        def make_const(x):
            if isinstance(x, np.ndarray):
                x.flags.writeable = False
            return x

        self._channel = make_const(channel)
        self._marker_1 = make_const(marker_1)
        self._marker_2 = make_const(marker_2)
        self._binary = None

    @property
    def channel(self) -> np.ndarray:
        return self._channel

    @property
    def marker_1(self) -> np.ndarray:
        return self._marker_1

    @property
    def marker_2(self) -> np.ndarray:
        return self._marker_2

    @property
    def binary(self) -> np.ndarray:
        if self._binary is None:
            self._binary = self._to_binary()
            self._binary.flags.writeable = False
        return self._binary

    @classmethod
    def from_binary(cls, binary: np.ndarray):
        if binary.dtype == np.uint16:
            result = cls(channel=np.bitwise_and(binary, cls.int_t.channel_mask),
                         marker_1=np.bitwise_and(binary, cls.int_t.marker_1_mask),
                         marker_2=np.bitwise_and(binary, cls.int_t.marker_2_mask))
        else:
            binary = binary.astype(cls.real_t.dtype, copy=False)

            result = cls(channel=binary['channel'],
                         marker_1=np.bitwise_and(binary['marker'], cls.real_t.marker_1_mask),
                         marker_2=np.bitwise_and(binary['marker'], cls.real_t.marker_2_mask))
        binary.flags.writeable = False
        result._binary = binary
        return result

    def _to_binary(self) -> np.ndarray:
        if self.data_type == 'INT':
            result = np.bitwise_and(self.channel, self.int_t.channel_mask)
            result |= self.int_t.marker_1_mask * self.marker_1.astype(bool)
            result |= self.int_t.marker_2_mask * self.marker_2.astype(bool)
            return result
        else:
            result = np.empty(self.size, dtype=self.real_t.dtype)
            result['channel'][:] = self.channel
            result['marker'][:] = np.bitwise_or(self.real_t.marker_1_mask * self.marker_1.astype(bool),
                                                self.real_t.marker_2_mask * self.marker_2.astype(bool))
            return result

    @property
    def data_type(self) -> str:
        if self.channel.dtype == np.uint16:
            return 'INT'
        else:
            return 'REAL'

    @property
    def size(self) -> int:
        return max(self.channel.size, self.marker_1.size, self.marker_2.size)

    def __hash__(self):
        return hash((self.data_type, self.binary.tobytes()))

    def __eq__(self, other) -> bool:
        return type(self) == type(other) and np.all(self.binary == other.binary)


class SequenceEntry:
    """This class represents a row of the sequencing list."""
    __slots__ = ('entries', 'wait', 'loop_inf', 'loop_count', 'goto_ind', 'goto_state', 'jmp_type', 'jmp_ind')

    def __init__(self, entries,
                 wait: bool=False,
                 loop_inf: bool=None,
                 loop_count: int=None,
                 goto_ind: int=None,
                 goto_state: bool=None,
                 jmp_type: str=None,
                 jmp_ind: int=None):
        if entries is None:
            entries = []

        self.entries = entries
        self.wait = wait
        self.loop_inf = loop_inf
        self.loop_count = loop_count
        self.goto_ind = goto_ind
        self.goto_state = goto_state
        self.jmp_type = jmp_type
        self.jmp_ind = jmp_ind

    def __eq__(self, other):
        if not isinstance(other, SequenceEntry):
            return NotImplemented

        for attr in ('entries', 'wait', 'loop_inf', 'goto_state', 'jmp_type'):
            if getattr(self, attr) != getattr(other, attr):
                return False

        # Only compare indices if correct state / type
        if self.goto_state:
            if self.goto_ind != other.goto_ind:
                return False

        if self.jmp_type is not None and self.jmp_type.lower() in ('ind', 'index'):
            if self.jmp_ind != other.jmp_ind:
                return False

        return True

    def __repr__(self):
        return "SequenceEntry({attrs})".format(
            attrs=', '.join(
                '{key}={value}'.format(key=slot, value=getattr(self, slot))
                for slot in self.__slots__
                if getattr(self, slot) is not None
            )
        ).replace('\'', '')

    def __iter__(self):
        yield self.entries
        yield self.wait
        yield self.loop_inf
        yield self.loop_count
        yield self.goto_ind
        yield self.goto_state
        yield self.jmp_type
        yield self.jmp_ind

    def __len__(self):
        return 8


class CommandGroup:
    """Bundles commands and minimizes subsystem/prefix selections. Does not really increase speed."""
    def __init__(self):
        self.command_list = []
        self.current_prefix = ''

    def append(self, required_prefix, local_command):
        if required_prefix == self.current_prefix:
            command = local_command
        else:
            command = required_prefix + local_command
            self.current_prefix = required_prefix
        self.command_list.append(command)

    def build(self) -> str:
        return ';'.join(self.command_list)


class TekAwg:
    """Class which allows communication with a tektronix AWG5000 series (7000 series should work
     as well, but should be tested). It uses pyvisa as backend.

    Example:

        AWG_IP = '127.0.0.1'

        tek = TekAwg.connect_raw_visa_socket(AWG_IP, port=4567)
        awg.print_waveform_list()
        awg.close()
    """

    DEFAULT_RESOURCE_PROPERTIES = dict(read_termination='\n',
                                       query_delay=1e-3,
                                       timeout=10000)

    def __init__(self, instrument: MessageBasedResource):
        """Do nothing but setting private properties"""
        self._inst = instrument

        self._n_channels = None
        self._check_for_errors = True
        self._model = None

    @property
    def n_channels(self) -> int:
        if self._n_channels is None:
            self._n_channels = int(self.query('AWGControl:CONFigure:CNUMber?', expected_responses=1))
        return self._n_channels

    @property
    def model(self) -> str:
        if self._model is None:
            idn = self.query('*IDN?')
            manufacturer, model, *_ = idn.split(',')
            if manufacturer.upper() != 'TEKTRONIX':
                warnings.warn('Unexpected manufacturer: %s' % manufacturer)
            self._model = model
        return self._model

    @property
    def properties(self) -> dict:
        regex_5000 = re.compile(r'^AWG50\d\d[A-C]$')
        regex_7000 = re.compile(r'^AWG70\d\d[A-C]$')

        if regex_5000.match(self.model):
            # See AWG5000 data sheet & AWG software "Sequencer Mode" help page
            return {'MAX_SEQUENCE_LENGTH': 8000,
                    'MAX_NUMBER_WAVEFORMS': 16200,
                    'MAX_SEQUENCE_COUNTER': 65536,
                    'MIN_WAVEFORM_LENGTH': 250,
                    'WAVEFORM_GRANULARITY': 1}

        if regex_7000.match(self.model):
            # See AWG7000 data sheet & AWG software "Sequencer Mode" help page
            properties = {'MAX_SEQUENCE_LENGTH': 4000,
                          'MAX_NUMBER_WAVEFORMS': 16000,
                          'MAX_SEQUENCE_COUNTER': 65536,
                          'MIN_WAVEFORM_LENGTH': 960,
                          'WAVEFORM_GRANULARITY': 64}

            if self.model in ('AWG7000B', 'AWG7000C'):
                # See "Sequencer Mode" help page of AWG software
                properties['WAVEFORM_GRANULARITY'] = 4

            return properties

        else:
            raise RuntimeError('Properties not known for model "%s"' % self.model)

    @property
    def instrument(self) -> MessageBasedResource:
        return cast(MessageBasedResource, self._inst)

    @classmethod
    def connect_to_ip(cls, ip: str, backend='@ni'):
        """Connect to instrument via VXI-11 and set timeouts etc to meaningful values. The recommended way(by tektronix)
        is to use the raw socket."""
        address = 'TCPIP::{ip}::INSTR'.format(ip=ip)
        instrument = pyvisa.ResourceManager(backend).open_resource(address,
                                                                   **cls.DEFAULT_RESOURCE_PROPERTIES)
        return cls(cast(MessageBasedResource, instrument))

    @classmethod
    def connect_raw_visa_socket(cls, ip: str, port: int, backend=None):
        address = 'TCPIP0::{ip}::{port}::SOCKET'.format(ip=ip, port=port)
        instrument = pyvisa.ResourceManager(backend).open_resource(address,
                                                                   **cls.DEFAULT_RESOURCE_PROPERTIES)
        return cls(cast(MessageBasedResource, instrument))

    def close(self):
        self.instrument.close()

    def open(self):
        self.instrument.open()

    def wait_until_commands_executed(self):
        response = self.query('*OPC?')
        if response != '1':
            warnings.warn('Unexpected answer on "*OPC?": %s' % response)

    def write(self, message: str) -> None:
        """Sends text commands to the AWG5000 Series, no newline or return character required

            Args:
                message: str command to be sent to the AWG, multiple commands can be combined
                    with ";" as a separator

            Returns: Str, response from AWG when expected_response=True, else it returns None
            """
        self.instrument.write(message)

    def query(self, query: str, expected_responses: int=1) -> Union[str, Tuple[str]]:
        """Send query to AWG.

            Args:
                query: str command to be sent to the AWG, multiple queries can be combined
                    with ";" as a separator
                expected_responses: Method raises an exception if expected responses is not met by exception length.

            Returns: As many answers as requested.

            Raises:
                IOError: If not expected number of arguments"""
        assert expected_responses

        result = self.instrument.query(query)

        result = result.split(';')

        if len(result) != expected_responses:
            raise IOError('Got {} responses but expected  {}.'.format(len(result),
                                                                      expected_responses), result)

        if len(result) == 1:
            result, = result
        return result

    def query_chunked(self, cmd_iterable: Iterable[str],
                      converter: Callable[[str], Any]=lambda x: x,
                      chunk_size: int=1,
                      expected_responses: Optional[int]=None) -> Sequence[Any]:
        """

        Args:
            cmd_iterable: Iterable of queries to be send to the device.
            converter: Function that is applied to each answer
            chunk_size: Queries send at a time
            expected_responses: If not None number of answers that has to be received

        Returns:
            Sequence of answers

        Raises:
            IOError: expected responses not received
        """
        result = []
        for cmd_chunk in _get_chunked(cmd_iterable, chunk_size):
            result.extend(self.instrument.query_ascii_values(';'.join(cmd_chunk), converter=converter, separator=';'))

        if expected_responses is not None and expected_responses != len(result):
            raise IOError('Got {} responses but expected  {}.'.format(len(result),
                                                                      expected_responses), result)
        return result

    def write_chunked(self, cmd_iterable, chunk_size=1, block_after_each_chunk=False):
        for written_chunks, cmd_chunk in enumerate(_get_chunked(cmd_iterable, chunk_size)):
            self.instrument.write(';'.join(cmd_chunk))

            if block_after_each_chunk:
                self.wait_until_commands_executed()

    def get_error_queue(self):
        err_queue = []
        err_enum = np.uint8(int(self.instrument.query("*ESR?")))

        if err_enum:
            while True:
                answer = self.instrument.query("SYSTEM:ERR?")

                err_no, *_ = answer.split(',')
                if err_no == '0':
                    break
                else:
                    err_queue.append(answer)
        return err_queue

    def get_waveform_info(self) -> OrderedDict:
        waveform_names = self.get_waveform_names()

        result = OrderedDict()

        result['names'] = self.get_waveform_names()

        try:
            result['length'] = self.get_waveform_lengths(waveform_names)
        except IOError:
            pass

        try:
            result['type'] = self.get_waveform_types(waveform_names)
        except IOError:
            pass

        try:
            result['timestamp'] = self.get_waveform_types(waveform_names)
        except IOError:
            pass

        return result

    def print_waveform_list(self):
        """Prints a formatted list of all the current waveforms in active memory of the AWG.

            Returns: 0  if printed correctly
                     -1 if there was a connection issue

        """
        con_error = False

        # get list of waveforms, and count how many we have
        try:
            waveform_list = self.get_waveform_names()
            num_saved_waveforms = len(waveform_list)
        except IOError:
            return -1

        try:
            waveform_lengths = self.get_waveform_lengths(waveform_list)
        except IOError:
            waveform_lengths = ["" for _ in range(num_saved_waveforms)]
            con_error = True

        try:
            waveform_types = self.get_waveform_types(waveform_list)
        except IOError:
            waveform_types = ["" for _ in range(num_saved_waveforms)]
            con_error = True

        try:
            waveform_date = self.get_waveform_timestamps(waveform_list)
        except IOError:
            waveform_date = ["" for _ in range(0, num_saved_waveforms)]
            con_error = True

        print("\nList of waveforms in memory:")
        print("\nIndex \t Name\t\t\t\t Data Points \tType\t\tDate")
        for i in range(num_saved_waveforms):
            print('{0:<9}{1: <32}{2: <15}{3:<16}{4:<5}'.format(i+1,
                                                                waveform_list[i],
                                                                waveform_lengths[i],
                                                                waveform_types[i],
                                                                waveform_date[i]))

        if con_error:
            print("\nConnection Error, partial list printed only")
            return -1
        else:
            return 0

    def print_config(self):
        """Print the current configuration of the AWG"""
        print("\n\nCurrent Settings\n")
        print("Hardware ID:     ", self.get_serial())
        print("Run Mode:        ", self.get_run_mode())
        print("Run State:       ", self.get_run_state())
        print("Frequency:       ", self.get_freq())

        cur_waves = self.get_cur_waveform()
        cur_amp = self.get_amplitude()
        cur_offset = self.get_offset()
        chan_state = self.get_chan_state()
        print("\nChannel Settings")
        print ('%-15s%-15s%-15s%-15s%-15s' %
               ("Setting", "Channel 1", "Channel 2", "Channel 3", "Channel 4"))
        print ('%-15s%-15s%-15s%-15s%-15s' %
               ("Waveforms:", cur_waves[0], cur_waves[1], cur_waves[2], cur_waves[3]))
        print ('%-15s%-15s%-15s%-15s%-15s' %
               ("Amplitude (V):", cur_amp[0], cur_amp[1], cur_amp[2], cur_amp[3]))
        print ('%-15s%-15s%-15s%-15s%-15s' %
               ("Offset (V):", cur_offset[0], cur_offset[1], cur_offset[2], cur_offset[3]))
        print ('%-15s%-15s%-15s%-15s%-15s' %
               ("Channel State:", chan_state[0], chan_state[1], chan_state[2], chan_state[3]))

        seq_list = self.get_seq_list()
        print("\nCurrent Sequence:")
        print ('%-15s%-15s%-15s%-15s%-15s%-15s%-15s' %
               ("Index", "Channel 1", "Channel 2", "Channel 3",
                "Channel 4", "Loop Count", "Jump Target"))
        for i in range(len(seq_list)):
            loop_count = self.get_seq_element_loop_cnt(i+1)
            jump_trg = self.get_seq_element_jmp_ind(i+1)
            print ('%-15i%-15s%-15s%-15s%-15s%-15s%-15s' %
                   (i+1, seq_list[i].entries[0], seq_list[i].entries[1], seq_list[i].entries[2],
                    seq_list[i].entries[3], loop_count, jump_trg))

        print("")

    def get_waveform_names(self, waveform_indices: Union[Sequence[int], int, None]=None) -> Union[Sequence[str], str]:
        """Returns a list of all the currently saved waveforms on the AWG"""

        if waveform_indices is None:
            num_saved_waveforms = int(self.query("WLIST:SIZE?", 1))
            waveform_indices = range(num_saved_waveforms)
        elif isinstance(waveform_indices, int):
            return self.get_waveform_names([waveform_indices])[0]

        waveform_indices = list(waveform_indices)

        return self.query_chunked(
            map(':WLIST:NAME? {}'.format, waveform_indices), expected_responses=len(waveform_indices), chunk_size=16
        )

    def get_waveform_lengths(self, waveform_names: Union[Sequence[str], str]) -> Union[Sequence[int], int]:
        """Returns a list of lengths of all saved waveforms on the AWG"""
        if isinstance(waveform_names, str):
            return self.get_waveform_lengths([waveform_names])[0]
        else:
            waveform_names = self._parse_waveform_names(waveform_names)

        waveform_lengths = self.query_chunked(
            (':WLIST:WAV:LENG? %s' % waveform_name for waveform_name in waveform_names),
            converter=int, expected_responses=len(waveform_names), chunk_size=16
        )

        return waveform_lengths

    def get_waveform_types(self, waveform_names: Union[Sequence[str], str]) -> Union[Sequence[str], str]:
        """returns the type of waveform which is stored on the AWG, IE: the AWG saves waveforms
        as either Integer ("INT") or Floating Point ("REAL") representations.

            Args:
                waveform_list: A single waveform name, or list of names

            Returns: list of strings containing either "INT" or "REAL" for int or float

            Raises:
                IOError if fewer types were returned then asked for"""
        if isinstance(waveform_names, (str, int)):
            return self.get_waveform_types([waveform_names])[0]

        waveform_names = self._parse_waveform_names(waveform_names)

        return self.query_chunked(
            map(':WLIST:WAV:TYPE? {}'.format, waveform_names),
            expected_responses=len(waveform_names), chunk_size=16
        )

    def get_waveform_timestamps(self, waveform_names: Union[Sequence[str], str]) -> Union[Sequence[str], str]:
        """Returns the creation/edit timestamp of waveforms which are stored on the AWG,

            Args:
                waveform_list: A single waveform name, or list of names

            Returns: list of strings containing date of creation or last edit

            Raises:
                IOError if fewer types were returned then asked for"""
        if isinstance(waveform_names, (str, int)):
            return self.get_waveform_timestamps([waveform_names])[0]

        waveform_names = self._parse_waveform_names(waveform_names)

        return self.query_chunked(
            map(':WLIST:WAV:TST? {}'.format, waveform_names),
            expected_responses=len(waveform_names), chunk_size=16
        )

    def get_waveform_data(self, waveform_name: str, chunk_size=10*2**10) -> Waveform:
        """Get the raw waveform data from the AWG
            Args:
                waveform_name: Name of the waveform to get

            Returns: a string of binary containing the data from the AWG, header has been removed

            Raises:
                IOError if there was a timeout, most likely due to connection or incorrect name
        """
        waveform_name = self._parse_waveform_name(waveform_name)

        wf_length = self.get_waveform_lengths(waveform_name)
        data_type = self.get_waveform_types(waveform_name)
        if data_type == 'REAL':
            dtype = Waveform.real_t.dtype
        else:
            dtype = Waveform.int_t.dtype

        n_chunks = (wf_length + chunk_size - 1) // chunk_size

        waveform_data_cmd = 'WLISt:WAVeform:DATA? %s,{start}, {size}' % waveform_name

        waveform_data = []

        remaining_points = wf_length
        for chunk in range(n_chunks):
            cmd = waveform_data_cmd.format(start=chunk*chunk_size, size=min(chunk_size, remaining_points))

            received = self.instrument.query_binary_values(cmd, datatype='s', container=tuple,
                                                           header_fmt='ieee')

            waveform_data.extend(received)
            remaining_points -= chunk_size

        waveform_data = b''.join(waveform_data)

        return Waveform.from_binary(np.frombuffer(waveform_data, dtype=dtype))

    def new_waveform(self, waveform_name: str, waveform: Waveform, chunk_size=10*2**10):
        """

        Args:
            waveform_name:
            waveform:
            chunk_size: Default is 10KB

        Returns:

        """
        data_type = waveform.data_type
        wf_length = waveform.size
        data = waveform.binary

        waveform_name = '"%s"' % waveform_name.replace('"', '').strip()

        self.write('WLISt:WAVeform:NEW {name},{size},{data_type}'.format(name=waveform_name,
                                                                         size=wf_length,
                                                                         data_type=data_type))

        data_cmd = 'WLIST:WAVEFORM:DATA {name},{offset},{size},'

        try:
            n_chunks = (wf_length + chunk_size - 1) // chunk_size
            remaining_points = wf_length
            for chunk in range(n_chunks):
                self.instrument.write_binary_values(
                    data_cmd.format(name=waveform_name,
                                    offset=chunk * chunk_size,
                                    size=min(chunk_size, remaining_points)),
                    data[chunk*chunk_size:(chunk+1)*chunk_size].view('B'),
                    datatype='B'
                )
                remaining_points -= chunk_size
        except Exception as err:
            raise RuntimeError('Error while uploading %s. Waveform may be incomplete.' % waveform_name) from err

    def del_waveform(self, waveform_name):
        """Delete Specified Waveform"""
        self.write('WLISt:WAVeform:DELete %s' % self._parse_waveform_name(waveform_name))


    #######################   AWG SETTINGS  ############################

    def get_serial(self) -> str:
        """Returns the hardware serial number and ID as a string"""
        return self.query("*IDN?")

    def get_freq(self) -> float:
        """Returns the current sample rate of the AWG"""
        return float(self.query("FREQ?"))

    def set_freq(self, freq):
        """Sets the current sample rate of the AWG"""
        self.write("FREQ "+str(freq))

    def get_run_mode(self):
        """Gets the current running mode of the AWG: SEQ, CONT, TRIG, GAT"""
        return self.query("AWGCONTROL:RMODE?")

    def set_run_mode(self, mode):
        """Sets the run mode of the AWG, allowed modes are:
            continuous, triggered, gated, sequence"""
        if mode.lower() in ["continuous", "cont",
                            "triggered", "trig",
                            "gated", "gat",
                            "sequence", "seq"]:
            self.write("AWGCONTROL:RMODE %s" % mode)
        else:
            raise RuntimeError('Invalid mode', mode)

    def get_run_state(self):
        """Gets the current state of the AWG, possible states are:
        stopped, waiting for trigger, or running"""
        state = self.query("AWGControl:RSTate?")
        if state == "0":
            return "Stopped"
        elif state == "1":
            return "Waiting for Trigger"
        elif state == "2":
            return "Running"
        raise IOError("Not valid run state")

    def run(self):
        """Start running the AWG"""
        self.write("AWGControl:RUN")

    def stop(self):
        """Stop the AWG"""
        self.write("AWGCONTROL:STOP")

    def jump_to_sequence_element(self, element_index):
        self.write('AWGC:EVEN:SOFT %d' % element_index)

    def _parse_channel(self, channel: Optional[Union[int, str, Iterable[Union[int, str]]]]) -> Tuple[Sequence[str], bool]:
        """Convert channel argument to a list of valid channel indices as strings."""
        single_channel = False

        if channel is None:
            channel = range(1, 1 + self.n_channels)
        elif isinstance(channel, (int, str)):
            channel = [channel]
            single_channel = True
        channel = list(map(int, channel))
        if set(channel) - set(range(1, 1+self.n_channels)):
            raise RuntimeError('Invalid channel(s)', set(channel) - set(range(1, 1+self.n_channels)))
        return tuple(map(str, channel)), single_channel

    @staticmethod
    def _parse_waveform_name(waveform_name: str) -> str:
        return '"%s"' % waveform_name.strip('"')

    @classmethod
    def _parse_waveform_names(cls, waveform_names: Sequence[str]) -> Sequence[str]:
        return [cls._parse_waveform_name(waveform_name)
                for waveform_name in waveform_names]

    def _get_channel_property(self, query_template: str, converter: Callable, channel):
        parsed_channels, single_response = self._parse_channel(channel)

        query_iterable = (query_template.format(ch=ch) for ch in parsed_channels)

        result = self.query_chunked(query_iterable,
                                    expected_responses=len(parsed_channels),
                                    chunk_size=len(parsed_channels),
                                    converter=converter)
        if single_response:
            result, = result
        return result

    def _set_channel_property(self, cmd_template: str, channel, values, value_parser=lambda x: x):
        parsed_channels, _ = self._parse_channel(channel)
        if not isinstance(values, (list, tuple)):
            values = [values] * len(parsed_channels)

        if len(values) != len(parsed_channels):
            raise ValueError('Could not query "{}" as the argument number is wrong'.format(cmd_template),
                             channel, values)

        parsed_values = [value_parser(value) for value in values]
        cmd_iterable = (cmd_template.format(ch=ch, value=value) for ch, value in zip(parsed_channels, parsed_values))

        self.write_chunked(cmd_iterable, chunk_size=len(parsed_channels))

    @staticmethod
    def _bool_parser(state) -> int:
        if isinstance(state, str):
            if state.lower() in ('on', '1', 'true'):
                return 1
            elif state.lower() in ('off', '0', 'false'):
                return 0
            else:
                # catch other strings that might be unintended
                raise ValueError('Invalid bool state: %s' % state)
        return int(bool(state))

    def get_amplitude(self, channel=None) -> Union[float, Sequence[float]]:
        return self._get_channel_property(':SOURCE{ch}:VOLTAGE?', float, channel)

    def set_amplitude(self, amplitude, channel=None):
        self._set_channel_property(':SOURCE{ch}:VOLTAGE {value}', channel, amplitude)

    def get_offset(self, channel=None):
        return self._get_channel_property(':SOURCE{ch}:VOLTAGE:OFFSET?', float, channel)

    def set_offset(self, offset, channel=None):
        self._set_channel_property(':SOURCE{ch}:VOLTAGE:OFFSET {value}', channel=channel, values=offset)

    def get_marker_high(self, marker: int, channel=None):
        marker = int(marker)
        if marker not in (1, 2):
            raise ValueError('Marker must be in {1, 2}')

        template = ':SOURCE{ch}:MARKER%d:VOLTAGE:HIGH?' % marker
        return self._get_channel_property(template, channel=channel, converter=float)

    def set_marker_high(self, voltage, marker, channel=None):
        marker = int(marker)
        if marker not in (1, 2):
            raise ValueError('Marker must be in {1, 2}')

        template = ':SOURCE{ch}:MARKER%d:VOLTAGE:HIGH {value}' % marker
        return self._set_channel_property(template, channel=channel, values=voltage)

    def get_marker_low(self, marker: int, channel=None):
        marker = int(marker)
        if marker not in (1, 2):
            raise ValueError('Marker must be in {1, 2}')

        template = ':SOURCE{ch}:MARKER%d:VOLTAGE:LOW?' % marker
        return self._get_channel_property(template, channel=channel, converter=float)

    def set_marker_low(self, voltage, marker, channel=None):
        marker = int(marker)
        if marker not in (1, 2):
            raise ValueError('Marker must be in {1, 2}')

        template = ':SOURCE{ch}:MARKER%d:VOLTAGE:LOW {value}' % marker
        return self._set_channel_property(template, channel=channel, values=voltage)

    def get_chan_state(self, channel=None):
        return self._get_channel_property(':OUTPUT{ch}?', channel=channel, converter=lambda x: int(x) == 1)

    def set_chan_state(self, state, channel=None):
        """Set whether the channels are on or off, where 0 means off and 1 means on"""
        self._set_channel_property(':OUTPUT{ch} {value}', channel=channel, values=state, value_parser=self._bool_parser)

    def get_raw_state(self, channel=None) -> Sequence[bool]:
        return self._get_channel_property('AWGC:DOUT{ch}:STAT?', channel=channel, converter=lambda x: int(x) == 1)

    def set_raw_state(self, state, channel=None):
        self._set_channel_property('AWGC:DOUT{ch}:STAT {value}',
                                   channel=channel, values=state, value_parser=self._bool_parser)

    def get_trig_source(self):
        return self.query("TRIG:SOUR?")

    def set_trig_source(self, source):
        trig_sources = ["int", "internal", "ext", "external"]
        if source.lower() in trig_sources:
            self.write("TRIG:SOUR %s" % source)
        else:
            raise ValueError('Invalid trigger source', source)

    def get_trig_interval(self) -> float:
        return float(self.query("TRIG:TIM?"))

    def set_trig_interval(self, interval):
        assert float(interval) > 0
        self.write("TRIG:TIM %f" % float(interval))

    def trig(self):
        return self.write("*TRG")

    ###################  SEQUENCER ######################

    def get_cur_waveform(self, channel=None):
        template = ':SOURCE{ch}:WAV?'
        return self._get_channel_property(template, converter=str, channel=channel)

    def set_cur_waveform(self, waveform_name, channel=None):
        template = ':SOURCE{ch}:WAV \"{value}\"'
        self._set_channel_property(template, channel, waveform_name)

    def set_seq_element_entries(self, element_index: int,
                                waveform_name: Union[str, Sequence[str]], channel=None):
        template = 'SEQ:ELEM%d:WAV{ch} {value}' % element_index
        self._set_channel_property(template, channel=channel, values=waveform_name)

    def get_seq_element_entries(self, element_index, channel=None):
        template = 'SEQ:ELEM%d:WAV{ch}?' % element_index
        self._get_channel_property(template, channel=channel, converter=str)

    def get_seq_element_loop_cnt(self, element_index) -> int:
        return int(self.query('SEQuence:ELEMent'+str(element_index)+':LOOP:COUNt?'))

    def set_seq_element_loop_cnt(self, element_index, count):
        return self.write('SEQuence:ELEMent'+str(element_index)+':LOOP:COUNt '+str(count))

    def get_seq_element_loop_inf(self, element_index) -> bool:
        return int(self.query('SEQuence:ELEMent'+str(element_index)+':LOOP:INFinite?')) == 1

    def get_seq_length(self):
        return int(self.query('SEQ:LENGTH?'))

    def set_seq_length(self, length):
        if length > self.properties['MAX_SEQUENCE_LENGTH']:
            raise RuntimeError('Sequence length to large: %d > %d' % (length, self.properties['MAX_SEQUENCE_LENGTH']))
        self.write('SEQ:LENGTH '+str(length))

    def get_seq_element_jmp_ind(self, element_index):
        tar_type = self.get_seq_element_jmp_type(element_index)
        if tar_type == "IND":
            return self.query('SEQuence:ELEMent'+str(element_index)+':JTARget:INDex?')
        else:
            return tar_type

    def set_seq_element_jmp_ind(self, element_index, target):
        self.set_seq_element_jmp_type(element_index, "ind")
        self.write('SEQuence:ELEMent'+str(element_index)+':JTARget:INDex '+str(target))

    def get_seq_element_jmp_type(self, element_index):
        return self.query('SEQuence:ELEMent'+str(element_index)+':JTARget:TYPE?')

    def set_seq_element_jmp_type(self, element_index, tar_type):
        if tar_type.lower() in ["index", "ind", "next", "off"]:
            return self.write('SEQuence:ELEMent'+str(element_index)+':JTARget:TYPE '+str(tar_type))

    def get_seq_element_goto_state(self, element_index) -> bool:
        return int(self.query('SEQuence:ELEMent' + str(element_index) + ':GOTO:STAT?')) == 1

    def get_seq_element_goto_ind(self, element_index) -> int:
        return int(self.query('SEQuence:ELEMent' + str(element_index) + ':GOTO:IND?'))

    def get_seq_element_wait(self, element_index) -> bool:
        return self.query('SEQuence:ELEMent' + str(element_index) + ':TWA?') == 'ON'

    def get_seq_element(self, element_index):
        queries = [
            "WAV{ch}?".format(ch=ch) for ch in range(1, 1 + self.n_channels)
        ] + [
            'TWA?',
            'LOOP:INF?',
            'LOOP:COUN?',
            'GOTO:IND?',
            'GOTO:STAT?',
            'JTAR:TYPE?',
            'JTAR:IND?'
        ]
        base = ':SEQ:ELEM%d:' % element_index
        query = ';'.join(base + query for query in queries)

        *entries, wait, loop_inf, loop_count, goto_ind, goto_stat, jmp_type, jmp_ind = self.query(query, len(queries))

        return SequenceEntry(entries,
                             wait=wait == 'ON',
                             loop_inf=int(loop_inf) == 1,
                             loop_count=int(loop_count),
                             goto_ind=int(goto_ind),
                             goto_state=goto_stat == 'ON',
                             jmp_type=jmp_type,
                             jmp_ind=int(jmp_ind))

    def set_seq_element(self, element_index: int, seq_element: SequenceEntry, no_write=False):
        command_group = CommandGroup()

        if len(seq_element.entries) != self.n_channels:
            raise ValueError('Invalid channel count')

        base = ':SEQ:ELEM{pos}:'.format(pos=element_index)

        for ch, entry in enumerate(seq_element.entries):
            if entry is not None:
                if isinstance(entry, str):
                    entry = '"%s"' % entry.strip('"')
                command_group.append(base, 'WAV{ch} {entry}'.format(ch=ch + 1, entry=entry))

        if seq_element.wait is not None:
            command_group.append(base, 'TWA %d' % bool(seq_element.wait))

        if seq_element.loop_inf is not None:
            command_group.append(base + 'LOOP:', 'INF %d' % bool(seq_element.loop_inf))

        if seq_element.loop_count is not None:
            command_group.append(base + 'LOOP:', 'COUN %d' % seq_element.loop_count)

        if seq_element.jmp_ind is not None:
            command_group.append(base + 'JTAR:', 'IND %d' % seq_element.jmp_ind)

        if seq_element.jmp_type is not None:
            command_group.append(base + 'JTAR:', 'TYPE %s' % seq_element.jmp_type)

        if seq_element.goto_state is not None:
            command_group.append(base + 'GOTO:', 'STAT %d' % bool(seq_element.goto_state))

        if seq_element.goto_ind is not None:
            command_group.append(base + 'GOTO:', 'IND %d' % seq_element.goto_ind)

        cmd = command_group.build()
        if no_write:
            return cmd

        else:
            self.write(cmd)

    def get_seq_list(self):
        """Get the current list of waveforms in the sequencer"""
        return [self.get_seq_element(i)
                for i in range(1, 1+self.get_seq_length())]

    def set_seq_list(self, seq_list, position):
        """Set the sequence list"""

        if isinstance(position, int):
            position = itertools.count(position)

        position = list(itertools.islice(position, len(seq_list)))

        seq_len = self.get_seq_length()

        if max(position) > seq_len:
            raise ValueError('Invalid position')

        cmd = []
        for element_index, element in zip(position, seq_list):
            cmd.extend(self.set_seq_element(element_index=element_index, seq_element=element, no_write=True))
        self.write_chunked(cmd, 32)
