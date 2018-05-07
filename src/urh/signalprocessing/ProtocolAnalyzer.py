import array
import copy
import math
import random
from collections import defaultdict

import numpy as np
from PyQt5.QtCore import pyqtSlot, QObject, pyqtSignal, Qt

from urh import constants
from urh.cythonext import signalFunctions
from urh.cythonext.signalFunctions import Symbol
from urh.signalprocessing.ProtocoLabel import ProtocolLabel
from urh.signalprocessing.ProtocolBlock import ProtocolBlock
from urh.signalprocessing.Signal import Signal
from urh.signalprocessing.encoding import encoding
from urh.util import FileOperator


class color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class ProtocolAnalyzerSignals(QObject):
    protocol_updated = pyqtSignal()
    show_state_changed = pyqtSignal()
    data_sniffed = pyqtSignal(int)
    sniff_device_errors_changed = pyqtSignal(str)
    line_duplicated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)


class ProtocolAnalyzer(object):
    """
    The ProtocolAnalyzer is what you would refer to as "protocol".
    The data is stored in the blocks variable.
    This class offers serveral methods for protocol analysis.
    """

    def __init__(self, signal: Signal):
        # Erster Index gibt die Blocknummer an.
        # Letzter Index einer Zeile gibt Ende der Pause an.
        # Letztes Bit steht also an vorletzter Stelle
        self.bit_sample_pos = []
        """:type: list of [list of int]"""

        self._protocol_labels = []
        """:type: list of ProtocolLabel """

        self.bit_alignment_positions = []
        """:param bit_alignment_positions:
        Um die Hex ASCII Darstellungen an beliebigen stellen auszurichten """

        self.blocks = []
        """:type: list of ProtocolBlock """

        self.used_symbols = set()
        """:type: set of Symbol """

        self.signal = signal
        self.filename = self.signal.filename if self.signal is not None else ""

        self.__name = "Blank"  # Fallback if Signal has no Name

        self.show = Qt.Checked  # Show in Compare Frame?
        self.qt_signals = ProtocolAnalyzerSignals()

        self.decoder = encoding(["Non Return To Zero (NRZ)"]) # For Default Encoding of Protocol
        # Blocks

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k != "qt_signals" and k != "signal":
                setattr(result, k, copy.deepcopy(v, memo))
        result.signal = self.signal
        result.qt_signals = ProtocolAnalyzerSignals()
        return result

    @property
    def name(self):
        name = self.signal.name if self.signal is not None else self.__name
        return name

    @name.setter
    def name(self, val: str):
        if self.signal is None:
            self.__name = val
        else:
            self.signal.name = val

    @property
    def pauses(self):
        return [block.pause for block in self.blocks]

    @property
    def protocol_labels(self):
        return self._protocol_labels

    @protocol_labels.setter
    def protocol_labels(self, value):
        """

        :type value: list of ProtocolLabel
        """
        self._protocol_labels = value
        if self._protocol_labels:
            self._protocol_labels.sort()

    @property
    def plain_bits_str(self):
        return [str(block) for block in self.blocks]

    @property
    def plain_hex_str(self):
        return [block.plain_hex_str for block in self.blocks]

    @property
    def plain_ascii_str(self):
        return [block.plain_ascii_str for block in self.blocks]

    @property
    def decoded_proto_bits_str(self):
        """

        :rtype: list of str
        """
        return [block.decoded_bits_str for block in self.blocks]

    @property
    def decoded_hex_str(self):
        """

        :rtype: list of str
        """
        return [block.decoded_hex_str for block in self.blocks]

    @property
    def decoded_ascii_str(self):
        """

        :rtype: list of str
        """
        return [block.decoded_ascii_str for block in self.blocks]

    @property
    def num_blocks(self):
        return len([b for b in self.blocks if b])

    def clear_decoded_bits(self):
        [block.clear_decoded_bits() for block in self.blocks]

    def decoded_to_str_list(self, view_type):
        if view_type == 0:
            return self.decoded_proto_bits_str
        elif view_type == 1:
            return self.decoded_hex_str
        elif view_type == 2:
            return self.decoded_ascii_str

    def plain_to_string(self, view: int, show_pauses=True) -> str:
        """

        :param view: 0 - Bits ## 1 - Hex ## 2 - ASCII
        """
        time = constants.SETTINGS.value('show_pause_as_time', type=bool)
        if show_pauses and time and self.signal:
            srate = self.signal.sample_rate
        else:
            srate = None

        return '\n'.join(block.view_to_string(view, False, show_pauses,
                                              sample_rate=srate
                                              ) for block in self.blocks)

    def set_decoder_for_blocks(self, decoder: encoding, blocks=None):
        blocks = blocks if blocks is not None else self.blocks
        self.decoder = decoder
        for block in blocks:
            block.decoder = decoder

    def get_protocol_from_signal(self):
        signal = self.signal
        if signal is None:
            self.blocks = None
            return

        self.bit_sample_pos[:] = []

        if self.blocks is not None:
            self.blocks[:] = []
        else:
            self.blocks = []

        bit_len = signal.bit_len

        rel_symbol_len = self._read_symbol_len()
        self.used_symbols.clear()

        ppseq = signalFunctions.grab_pulse_lens(signal.qad,
                                                signal.qad_center,
                                                signal.tolerance,
                                                signal.modulation_type)

        bit_data, pauses = self._ppseq_to_bits(ppseq, bit_len, rel_symbol_len)


        i = 0
        for bits, pause in zip(bit_data, pauses):
            middle_bit_pos = self.bit_sample_pos[i][int(len(bits) / 2)]
            start, end = middle_bit_pos, middle_bit_pos + bit_len
            rssi = np.mean(np.abs(signal._fulldata[start:end]))
            block = ProtocolBlock(bits, pause, self.bit_alignment_positions,
                                  bit_len=bit_len, rssi=rssi, decoder=self.decoder)
            self.blocks.append(block)
            i += 1

        self.qt_signals.protocol_updated.emit()

    def _read_symbol_len(self):
        settings = constants.SETTINGS
        if 'rel_symbol_length' in settings.allKeys():
            rel_symbol_len = settings.value('rel_symbol_length', type=int) / 200
        else:
            rel_symbol_len = 0.1
        return rel_symbol_len

    def _ppseq_to_bits(self, ppseq, bit_len: int, rel_symbol_len: float):
        self.used_symbols.clear()
        self.bit_sample_pos[:] = []
        data_bits = []
        resulting_data_bits = []
        bit_sampl_pos = []
        pauses = []
        start = 0
        total_samples = 0

        pause_type = 42
        zero_pulse_type = 0
        one_pulse_type = 1

        there_was_data = False
        lower_bit_bound = 0.5 - rel_symbol_len
        upper_bit_bound = 0.5 + rel_symbol_len
        avail_symbol_names = constants.SYMBOL_NAMES

        if len(ppseq) > 0 and ppseq[0, 0] == pause_type:
            start = 1  # Starts with Pause
            total_samples = ppseq[0, 1]

        for i in range(start, len(ppseq)):
            cur_pulse_type = ppseq[i, 0]
            num_samples = ppseq[i, 1]
            num_bits_floated = num_samples / bit_len
            num_bits = int(num_bits_floated)
            decimal_place = num_bits_floated - num_bits

            if decimal_place > upper_bit_bound:
                num_bits += 1
            elif lower_bit_bound < decimal_place < upper_bit_bound and \
                    (not cur_pulse_type == pause_type or num_bits < 9):
                ptype = 1 if cur_pulse_type == one_pulse_type else 0
                if not there_was_data:
                    there_was_data = bool(ptype)

                symbol = self.__find_matching_symbol(num_bits, ptype)
                if symbol is None:
                    symbol = self.__create_symbol(num_bits, ptype,
                                                  num_samples,
                                                  avail_symbol_names)

                data_bits.append(symbol)
                bit_sampl_pos.append(total_samples)
                total_samples += num_samples
                continue

            if cur_pulse_type == pause_type:
                # OOK abdecken
                if num_bits < 9:
                    for k in range(num_bits):
                        data_bits.append(False)
                        bit_sampl_pos.append(total_samples + k * bit_len)

                elif not there_was_data:
                    # Ignore this pause, if there were no informations
                    # transmittted previously
                    del data_bits[:]
                    del bit_sampl_pos[:]

                else:
                    bit_sampl_pos.append(total_samples)
                    bit_sampl_pos.append(total_samples + num_samples)
                    self.bit_sample_pos.append(bit_sampl_pos[:])
                    del bit_sampl_pos[:]

                    resulting_data_bits.append(data_bits[:])
                    del data_bits[:]
                    pauses.append(num_samples)
                    there_was_data = False

            elif cur_pulse_type == zero_pulse_type:
                for k in range(num_bits):
                    data_bits.append(False)
                    bit_sampl_pos.append(total_samples + k * bit_len)

            elif cur_pulse_type == one_pulse_type:
                if not there_was_data:
                    there_was_data = num_bits > 0
                for k in range(num_bits):
                    data_bits.append(True)
                    bit_sampl_pos.append(total_samples + k * bit_len)

            total_samples += num_samples

        if there_was_data:
            resulting_data_bits.append(data_bits[:])
            self.bit_sample_pos.append(bit_sampl_pos[:] + [total_samples])
            pause = ppseq[-1, 1] if ppseq[-1, 0] == pause_type else 0
            pauses.append(pause)

        return resulting_data_bits, pauses

    def __find_matching_symbol(self, num_bits: int, pulsetype: int):
        for s in self.used_symbols:
            if s.nbits == num_bits and s.pulsetype == pulsetype:
                return s
        return None

    def __create_symbol(self, num_bits, ptype, num_samples, avail_symbol_names):
        name_index = len(self.used_symbols)
        if name_index > len(avail_symbol_names) - 1:
            name_index = len(avail_symbol_names) - 1
            print(
                "WARNING:"
                "Needed more symbols than names were available."
                "Symbols may be wrong labeled,"
                "consider extending the symbol alphabet.")

        symbol = Symbol(avail_symbol_names[name_index],
                        num_bits, ptype, num_samples)

        self.used_symbols.add(symbol)
        return symbol

    def add_bit_alignment(self, alignment):
        self.bit_alignment_positions.append(alignment)
        for block in self.blocks:
            block.bit_alignment_positions.append(alignment)

    def remove_bit_alignment(self, alignment):
        self.bit_alignment_positions.remove(alignment)
        for block in self.blocks:
            block.bit_alignment_positions.remove(alignment)

    def get_samplepos_of_bitseq(self, startblock: int, startindex: int,
                                endblock: int, endindex: int,
                                include_pause: bool):
        """
        Bestimmt an welcher Stelle (Samplemäßig) sich eine Bitsequenz befindet, die durch
        start und ende des Bitstrings gegeben ist

        :rtype: tuple[int,int]
        """
        lookup = self.bit_sample_pos

        if startblock > endblock:
            startblock, endblock = endblock, startblock

        if startindex >= len(lookup[startblock]) - 1:
            startindex = len(lookup[startblock]) - 1
            if not include_pause:
                startindex -= 1

        if endindex >= len(lookup[endblock]) - 1:
            endindex = len(lookup[endblock]) - 1
            if not include_pause:
                endindex -= 1

        start = lookup[startblock][startindex]
        end = lookup[endblock][endindex] - start

        return start, end

    def get_bitseq_from_selection(self, selection_start: int, selection_width: int, bitlen: int):
        """
        Holt Start und Endindex der Bitsequenz von der Selektion der Samples

        :param selection_start: Selektionsstart in Samples
        :param selection_width: Selektionsende in Samples
        :rtype: tuple[int,int,int,int]
        :return: Startblock, Startindex, Endblock, Endindex
        """
        start_block = -1
        start_index = -1
        end_block = -1
        end_index = -1

        if selection_start + selection_width < self.bit_sample_pos[0][0] or selection_width < bitlen:
            return start_block, start_index, end_block, end_index

        for j, block_sample_pos in enumerate(self.bit_sample_pos):
            if block_sample_pos[-2] < selection_start:
                continue
            elif start_block == -1:
                start_block = j
                for i, sample_pos in enumerate(block_sample_pos):
                    if sample_pos < selection_start:
                        continue
                    elif start_index == -1:
                        start_index = i
                        if block_sample_pos[-1] - selection_start < selection_width:
                            break
                    elif sample_pos - selection_start > selection_width:
                        end_block = j
                        end_index = i
                        return start_block, start_index, end_block, end_index
            elif block_sample_pos[-1] - selection_start < selection_width:
                continue
            else:
                end_block = j
                for i, sample_pos in enumerate(block_sample_pos):
                    if sample_pos - selection_start > selection_width:
                        end_index = i
                        return start_block, start_index, end_block, end_index

        last_block = len(self.bit_sample_pos) - 1
        last_index = len(self.bit_sample_pos[last_block]) - 1
        return start_block, start_index, last_block, last_index

    def delete_blocks(self, block_start: int, block_end: int, start: int, end: int, view: int, decoded: bool,
                      blockranges_for_groups=None):
        removable_block_indices = []

        for i in range(block_start, block_end + 1):
            try:
                self.blocks[i].clear_decoded_bits()
                bs, be = self.convert_range(start, end, view, 0, decoded, block_indx=i)
                del self.blocks[i][bs:be + 1]
                if len(self.blocks[i]) == 0:
                    removable_block_indices.append(i)
            except IndexError:
                continue

        # Refblocks der Labels updaten
        for i in removable_block_indices:
            labels_before = [p for p in self.protocol_labels
                             if p.refblock < i < p.refblock + p.nfuzzed]
            labels_after = [p for p in self.protocol_labels if p.refblock > i]
            for label in labels_after:
                label.refblock -= 1

            for label in labels_before:
                label.nfuzzed -= 1

        # Remove Empty Blocks and Pause after empty Blocks
        for i in reversed(removable_block_indices):
            del self.blocks[i]

    def convert_index(self, index: int, from_view: int, to_view: int, decoded: bool, block_indx=-1) -> tuple:
        """
        Konvertiert einen Index aus der einen Sicht (z.B. Bit) in eine andere (z.B. Hex)

        :param block_indx: Wenn -1, wird der Block mit der maximalen Länge ausgewählt
        :return:
        """
        if len(self.blocks) == 0:
            return (0, 0)

        if block_indx == -1:
            block_indx = self.blocks.index(max(self.blocks, key=len)) # Longest Block

        if block_indx >= len(self.blocks):
            block_indx = len(self.blocks) - 1

        return self.blocks[block_indx].convert_index(index, from_view, to_view, decoded)

    def convert_range(self, index1: int, index2: int, from_view: int,
                      to_view: int, decoded: bool, block_indx=-1):
        start = self.convert_index(index1, from_view, to_view, decoded, block_indx=block_indx)[0]
        end = self.convert_index(index2, from_view, to_view, decoded, block_indx=block_indx)[1]

        return int(start), int(math.ceil(end))

    def copy_data(self):
        """

        :rtype: list of ProtocolBlock, list of ProtocolLabel
        """
        return copy.deepcopy(self.blocks), copy.deepcopy(self.protocol_labels)

    def revert_to(self, orig_blocks, orig_labels):
        """
        Revert to previous state

        :param orig_blocks: blocks to be restored
        :type orig_blocks: list of ProtocolBlock
        :param orig_labels: labels to be restored
        :type orig_labels: list of ProtocolLabel
        """
        self.blocks = orig_blocks
        """:type: list of ProtocolBlock """
        self.protocol_labels = orig_labels

    def find_differences(self, refindex: int, view: int):
        """
        Sucht alle Unterschiede zwischen den Protokollblöcken, bezogen auf einen Referenzblock

        :param refindex: Index des Referenzblocks
        :rtype: dict[int, set[int]]
        """
        differences = defaultdict(set)

        if refindex >= len(self.blocks):
            return differences

        if view == 0:
            proto = self.decoded_proto_bits_str
        elif view == 1:
            proto = self.decoded_hex_str
        elif view == 2:
            proto = self.decoded_ascii_str
        else:
            return differences

        refblock = proto[refindex]
        len_refblock = len(refblock)


        for i, block in enumerate(proto):
            if i == refindex:
                continue

            diff_cols = set()

            for j, value in enumerate(block):
                if j >= len_refblock:
                    break

                if value != refblock[j]:
                    diff_cols.add(j)

            len_block = len(block)
            if len_block != len_refblock:
                len_diff = abs(len_refblock - len_block)
                start = len_refblock
                if len_refblock > len_block:
                    start = len_block
                end = start + len_diff
                for k in range(start, end):
                    diff_cols.add(k)

            differences[i] = diff_cols

        return differences

    @staticmethod
    def from_file(filename: str):
        """
        :rtype: int, list of ProtocolGroup, set of Symbol
        """
        view_type, groups, symbols = FileOperator.read_protocol(filename)
        return view_type, groups, symbols

    def destroy(self):
        self.bit_alignment_positions = None
        self.protocol_labels = None
        self.bit_sample_pos = None
        self.blocks = None

    def estimate_frequency_for_one(self, sample_rate: float, nbits=42) -> float:
        """
        Calculates the frequency of at most nbits logical ones and returns the mean of these frequencies

        :param nbits:
        :return:
        """
        return self.__estimate_frequency_for_bit(True, sample_rate, nbits)

    def estimate_frequency_for_zero(self, sample_rate: float, nbits=42) -> float:
        """
        Calculates the frequency of at most nbits logical zeros and returns the mean of these frequencies

        :param nbits:
        :return:
        """
        return self.__estimate_frequency_for_bit(False, sample_rate, nbits)

    def __estimate_frequency_for_bit(self, bit: bool, sample_rate: float, nbits: int) -> float:
        if nbits == 0:
            return 0

        assert self.signal is not None
        freqs = []
        for i, block in enumerate(self.blocks):
            for j, block_bit in enumerate(block.plain_bits):
                if block_bit == bit:
                    start, nsamples = self.get_samplepos_of_bitseq(i, j, i, j + 1, False)
                    freq = self.signal.estimate_frequency(start, start + nsamples, sample_rate)
                    freqs.append(freq)
                    if len(freqs) == nbits:
                        return np.mean(freqs)
        if freqs:
            return np.mean(freqs)
        else:
            return 0


    def __str__(self):
        return "ProtoAnalyzer " + self.name

    def set_labels(self, val):
        self._protocol_labels = val
