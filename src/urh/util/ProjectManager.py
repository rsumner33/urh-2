import os
import xml.etree.ElementTree as ET

from PyQt5.QtCore import QDir, Qt, QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

from urh import constants
from urh.controller.ProjectDialogController import ProjectDialogController
from urh.signalprocessing.Modulator import Modulator
from urh.signalprocessing.ProtocoLabel import ProtocolLabel
from urh.signalprocessing.ProtocolAnalyzer import ProtocolAnalyzer
from urh.signalprocessing.Signal import Signal
from urh.util import FileOperator, util


class ProjectManager(QObject):
    AUTOSAVE_INTERVAL_MINUTES = 5
    sample_rate_changed = pyqtSignal(float)

    def __init__(self, maincontroller):
        super().__init__()
        self.maincontroller = maincontroller
        self.__sample_rate = 1e6
        self.bandwidth = 1e6
        self.frequency = 43392e4
        self.gain = 20
        self.device = "USRP"
        self.project_path = ""
        self.project_file = None

    @property
    def sample_rate(self):
        return self.__sample_rate

    @sample_rate.setter
    def sample_rate(self, val: float):
        if val != self.sample_rate:
            self.__sample_rate = val
            self.sample_rate_changed.emit(val)

    def set_recording_parameters(self, freq, sample_rate, bandwidth, gain, device):
        self.frequency = float(freq)
        self.sample_rate = float(sample_rate)
        self.bandwidth = float(bandwidth)
        self.gain = int(gain)
        self.device = device

    def read_recording_parameters(self):
        if self.project_file is None:
            return
        tree = ET.parse(self.project_file)
        root = tree.getroot()

        try:
            self.frequency = float(root.attrib["frequency"])
        except KeyError:
            self.frequency = 433.92e6
        try:
            self.sample_rate = float(root.attrib["sample_rate"])
        except KeyError:
            self.sample_rate = 1e6
        try:
            self.bandwidth = float(root.attrib["bandwidth"])
        except KeyError:
            self.bandwidth = 1e6
        try:
            self.gain = int(root.attrib["gain"])
        except KeyError:
            self.gain = 20

    def set_project_folder(self, path, ask_for_new_project=True):
        if path != self.project_path:
            self.maincontroller.close_all()
        self.project_path = path
        self.project_file = os.path.join(self.project_path, constants.PROJECT_FILE)
        if not os.path.isfile(self.project_file):
            if ask_for_new_project:
                reply = QMessageBox.question(self.maincontroller, "Project File",
                                             "Do you want to create a Project File for this folder?\n"
                                             "If you chose No, you can do it later via File->Convert Folder to Project.",
                                             QMessageBox.Yes | QMessageBox.No)

                if reply == QMessageBox.Yes:
                    dialog = ProjectDialogController(new_project=False, parent=self.maincontroller)
                    dialog.set_path(path)
                    dialog.finished.connect(self.on_dialog_finished)
                    dialog.exec_()

                else:
                    self.project_file = None

            if self.project_file is not None:
                root = ET.Element("UniversalRadioHackerProject")
                tree = ET.ElementTree(root)
                tree.write(self.project_file)
        else:
            self.read_recording_parameters()
            self.maincontroller.add_files(self.read_opened_filenames())
            self.read_compare_frame_groups() # Labels are read out here
            cfc = self.maincontroller.compare_frame_controller
            cfc.load_decodings()
            cfc.fill_decoding_combobox()

            for group_id, decoding_index in self.read_decodings().items():
                cfc.groups[group_id].decoding = cfc.decodings[decoding_index]

            #cfc.ui.cbDecoding.setCurrentIndex(index)
            cfc.refresh_protocol_labels()
            cfc.updateUI()
            modulators = self.read_modulators_from_project_file()
            self.maincontroller.generator_tab_controller.modulators = modulators if modulators else [
                Modulator("Modulation")]
            self.maincontroller.generator_tab_controller.refresh_modulators()

        if len(self.project_path) > 0 and self.project_file is None:
            self.maincontroller.ui.actionConvert_Folder_to_Project.setEnabled(True)
        else:
            self.maincontroller.ui.actionConvert_Folder_to_Project.setEnabled(False)

        self.maincontroller.adjustForCurrentFile(path)
        self.maincontroller.filemodel.setRootPath(path)
        self.maincontroller.ui.fileTree.setRootIndex(
            self.maincontroller.file_proxy_model.mapFromSource(self.maincontroller.filemodel.index(path)))
        self.maincontroller.ui.fileTree.setToolTip(path)
        self.maincontroller.ui.splitter.setSizes([1, 1])
        self.maincontroller.setWindowTitle("Universal Radio Hacker [" + path + "]")

    def convert_folder_to_project(self):
        self.project_file = os.path.join(self.project_path, constants.PROJECT_FILE)
        dialog = ProjectDialogController(new_project=False, parent=self.maincontroller)
        dialog.set_path(self.project_path)
        dialog.finished.connect(self.on_dialog_finished)
        dialog.exec_()

        if self.project_file is not None:
            root = ET.Element("UniversalRadioHackerProject")
            tree = ET.ElementTree(root)
            tree.write(self.project_file)
            self.maincontroller.ui.actionConvert_Folder_to_Project.setEnabled(False)

    def write_signal_information_to_project_file(self, signal: Signal, tree=None):
        if self.project_file is None or signal is None or len(signal.filename) == 0:
            return

        if tree is None:
            tree = ET.parse(self.project_file)

        root = tree.getroot()

        existing_filenames = {}

        for signal_tag in root.iter("signal"):
            existing_filenames[signal_tag.attrib["filename"]] = signal_tag

        if os.path.relpath(signal.filename, self.project_path) in existing_filenames.keys():
            signal_tag = existing_filenames[os.path.relpath(signal.filename, self.project_path)]
        else:
            # Neuen Tag anlegen
            signal_tag = ET.SubElement(root, "signal")

        signal_tag.set("name", signal.name)
        signal_tag.set("filename", os.path.relpath(signal.filename, self.project_path))
        signal_tag.set("bit_length", str(signal.bit_len))
        signal_tag.set("zero_treshold", str(signal.qad_center))
        signal_tag.set("tolerance", str(signal.tolerance))
        signal_tag.set("noise_treshold", str(signal.noise_treshold))
        signal_tag.set("noise_minimum", str(signal.noise_min_plot))
        signal_tag.set("noise_maximum", str(signal.noise_max_plot))
        signal_tag.set("auto_detect_on_modulation_changed", str(signal.auto_detect_on_modulation_changed))
        signal_tag.set("modulation_type", str(signal.modulation_type))
        signal_tag.set("sample_rate", str(signal.sample_rate))

        tree.write(self.project_file)

    def write_modulators_to_project_file(self, tree=None):
        """
        :type modulators: list of Modulator
        :return:
        """
        if self.project_file is None or not self.modulators:
            return

        if tree is None:
            tree = ET.parse(self.project_file)

        root = tree.getroot()
        # Clear Modulations
        for mod_tag in root.findall("modulator"):
            root.remove(mod_tag)

        for mod in modulators:
            mod_tag = ET.SubElement(root, "modulator")
            mod_tag.set("name", mod.name)
            mod_tag.set("carrier_freq_hz", str(mod.carrier_freq_hz))
            mod_tag.set("carrier_phase_deg", str(mod.carrier_phase_deg))
            mod_tag.set("carrier_amplitude", str(mod.carrier_amplitude))
            mod_tag.set("modulation_type", str(mod.modulation_type))
            mod_tag.set("sample_rate", str(mod.sample_rate))
            mod_tag.set("param_for_one", str(mod.param_for_one))
            mod_tag.set("param_for_zero", str(mod.param_for_zero))

        tree.write(self.project_file)

    def read_modulators_from_project_file(self):
        """
        :rtype: list of Modulator
        """
        return self.read_modulators_from_file(self.project_file)

    def read_modulators_from_file(self, filename: str):
        if not filename:
            return []

        tree = ET.parse(filename)
        root = tree.getroot()

        result = []
        for mod_tag in root.iter("modulator"):
            mod = Modulator(mod_tag.attrib["name"])
            mod.carrier_freq_hz = float(mod_tag.attrib["carrier_freq_hz"])
            mod.carrier_amplitude = float(mod_tag.attrib["carrier_amplitude"])
            mod.carrier_phase_deg = float(mod_tag.attrib["carrier_phase_deg"])
            mod.modulation_type = int(mod_tag.attrib["modulation_type"])
            mod.sample_rate = float(mod_tag.attrib["sample_rate"])
            mod.param_for_one = float(mod_tag.attrib["param_for_one"])
            mod.param_for_zero = float(mod_tag.attrib["param_for_zero"])
            result.append(mod)

        return result

    def saveProject(self):
        if self.project_file is None or not os.path.isfile(self.project_file):
            return

        #self.write_labels(self.maincontroller.compare_frame_controller.proto_analyzer)
        self.write_modulators_to_project_file(self.maincontroller.generator_tab_controller.modulators)

        tree = ET.parse(self.project_file)
        root = tree.getroot()
        root.set("frequency", str(self.frequency))
        root.set("sample_rate", str(self.sample_rate))
        root.set("bandwidth", str(self.bandwidth))
        root.set("gain", str(self.gain))

        for open_file in root.findall('open_file'):
            root.remove(open_file)

        open_files = []
        for i, sf in enumerate(self.maincontroller.signal_tab_controller.signal_frames):
            self.write_signal_information_to_project_file(sf.signal, tree=tree)
            try:
                pf = self.maincontroller.signal_protocol_dict[sf]
                filename = pf.filename

                if filename in FileOperator.archives.keys():
                    open_filename = FileOperator.archives[filename]
                else:
                    open_filename = filename

                if not open_filename or open_filename in open_files:
                    continue
                open_files.append(open_filename)

                file_tag = ET.SubElement(root, "open_file")
                file_tag.set("name", os.path.relpath(open_filename, self.project_path))
                file_tag.set("position", str(i))
            except Exception:
                pass

        for group_tag in root.findall("group"):
            root.remove(group_tag)

        cfc = self.maincontroller.compare_frame_controller
        for i, group in enumerate(cfc.groups):
            group_tag = ET.SubElement(root, "group")
            group_tag.set("name", str(group.name))
            group_tag.set("id", str(i))

            try:
                decoding_index = cfc.decodings.index(group.decoding)
            except ValueError:
                decoding_index = 0
            group_tag.set("decoding_index", str(decoding_index))

            for proto_frame in cfc.protocols[i]:
                if proto_frame.filename:
                    proto_tag = ET.SubElement(group_tag, "cf_protocol")
                    proto_tag.set("filename", os.path.relpath(proto_frame.filename, self.project_path))
                    show = "1" if proto_frame.show else "0"
                    proto_tag.set("show", show)

            for label in group_tag.findall('label'):
                group_tag.remove(label)

            for plabel in group.labels:
                label_tag = ET.SubElement(group_tag, "label")
                label_tag.set("name", plabel.name)
                label_tag.set("start", str(plabel.start))
                label_tag.set("end", str(plabel.end - 1))
                label_tag.set("refblock", str(plabel.refblock))
                label_tag.set("refbits", plabel.reference_bits)
                label_tag.set("display_type_index", str(plabel.display_type_index))

                restrictive = "1" if plabel.restrictive else "0"
                apply_decoding = "1" if plabel.apply_decoding else "0"

                label_tag.set("color_index", str(plabel.color_index))
                label_tag.set("restrictive", restrictive)
                label_tag.set("apply_decoding", apply_decoding)


        tree.write(self.project_file)

    def read_decodings(self) -> dict:
        if self.project_file is None:
            return

        tree = ET.parse(self.project_file)
        root = tree.getroot()
        decodings = {}
        for group_tag in root.iter("group"):
            id = group_tag.attrib["id"]
            try:
                decodings[int(id)] = int(group_tag.attrib["decoding_index"])
            except KeyError:
                decodings[int(id)] = 0

        return decodings


    def read_project_file_for_signal(self, signal: Signal):
        if self.project_file is None or len(signal.filename) == 0:
            return False

        tree = ET.parse(self.project_file)
        root = tree.getroot()
        for sig_tag in root.iter("signal"):
            if sig_tag.attrib["filename"] == os.path.relpath(signal.filename,
                                                             self.project_path):
                signal.name = sig_tag.attrib["name"]
                signal.qad_center = float(sig_tag.attrib["zero_treshold"])
                signal.tolerance = int(sig_tag.attrib["tolerance"])
                signal.auto_detect_on_modulation_changed = False if \
                sig_tag.attrib[
                                                                        "auto_detect_on_modulation_changed"] == 'False' else True

                signal.noise_treshold = float(sig_tag.attrib["noise_treshold"])
                try:
                    signal.sample_rate = float(sig_tag.attrib["sample_rate"])
                except KeyError:
                    pass  # For old project files

                signal.bit_len = int(sig_tag.attrib["bit_length"])
                signal.modulation_type = int(sig_tag.attrib["modulation_type"])
                break
        return True

    def read_opened_filenames(self):
        if self.project_file is not None:
            tree = ET.parse(self.project_file)
            root = tree.getroot()
            fileNames = []

            for ftag in root.findall("open_file"):
                pos = int(ftag.attrib["position"])
                filename = os.path.join(self.project_path, ftag.attrib["name"])
                fileNames.insert(pos, filename)

            fileNames = FileOperator.uncompress_archives(fileNames, QDir.tempPath())
            return fileNames
        return []

    def read_compare_frame_groups(self):
        if self.project_file is None:
            return

        tree = ET.parse(self.project_file)
        root = tree.getroot()

        proto_tree_model = self.maincontroller.compare_frame_controller.proto_tree_model
        tree_root = proto_tree_model.rootItem
        pfi = proto_tree_model.protocol_tree_items
        proto_frame_items = [item for item in pfi[0]]
        """:type: list of ProtocolTreeItem """

        for group_tag in root.iter("group"):
            name = group_tag.attrib["name"]
            id = group_tag.attrib["id"]

            if id == "0":
                tree_root.child(0).setData(name)
            else:
                tree_root.addGroup(name=name)

            group = tree_root.child(int(id))

            for proto_tag in group_tag.iter("cf_protocol"):
                filename = os.path.join(self.project_path, proto_tag.attrib["filename"])
                show = proto_tag.attrib["show"]
                try:
                    proto_frame_item = next((p for p in proto_frame_items if p.protocol.filename == filename))
                except StopIteration:
                    proto_frame_item = None

                if proto_frame_item is not None:
                    group.appendChild(proto_frame_item)
                    proto_frame_item.show_in_compare_frame = Qt.Checked if show == "1" else Qt.Unchecked

            group = proto_tree_model.groups[int(id)]

            for label_tag in group_tag.iter("label"):
                name = label_tag.attrib["name"]
                start = int(label_tag.attrib["start"])
                end = int(label_tag.attrib["end"])
                refblock = int(label_tag.attrib["refblock"])
                color_index = int(label_tag.attrib["color_index"])
                restrictive = int(label_tag.attrib["restrictive"]) == 1

                proto_label = ProtocolLabel(name, start, end, refblock, 0, color_index, restrictive)
                proto_label.reference_bits = label_tag.attrib["refbits"]
                proto_label.display_type_index = int(label_tag.attrib["display_type_index"])
                proto_label.apply_decoding = int(label_tag.attrib["apply_decoding"]) == 1

                group.add_label(proto_label)

            self.maincontroller.compare_frame_controller.expand_group_node(int(id))

        self.maincontroller.compare_frame_controller.refresh()

    def from_dialog(self, dialog: ProjectDialogController):
        if dialog.commited:
            self.set_project_folder(dialog.path, ask_for_new_project=False)
            self.frequency = dialog.freq
            self.sample_rate = dialog.sample_rate

    def on_dialog_finished(self):
        if self.sender().commited:
            self.frequency = self.sender().freq
            self.sample_rate = self.sender().sample_rate
        else:
            self.project_file = None
