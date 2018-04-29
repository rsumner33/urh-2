from PyQt5.QtWidgets import QTableView

from urh.models.LabelValueTableModel import LabelValueTableModel
from urh.signalprocessing.ProtocoLabel import ProtocolLabel
from urh.ui.delegates.ComboBoxDelegate import ComboBoxDelegate


class LabelValueTableView(QTableView):
    edit_label_action_triggered = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegateForColumn(1, ComboBoxDelegate(ProtocolLabel.DISPLAY_TYPES, False, self))
        self.setEditTriggers(QTableView.AllEditTriggers)

    def create_context_menu(self):
        menu = QMenu()
        if self.model().rowCount() > 0:
            edit_label_action = menu.addAction(self.tr("Edit labels..."))
            edit_label_action.setIcon(QIcon.fromTheme("configure"))
            edit_label_action.triggered.connect(self.on_edit_label_action_triggered)
        return menu

    def contextMenuEvent(self, event: QContextMenuEvent):
        menu = self.create_context_menu()
        menu.exec_(self.mapToGlobal(event.pos()))

    def create_context_menu(self):
        menu = QMenu()
        if self.model().rowCount() > 0:
            edit_label_action = menu.addAction(self.tr("Edit labels..."))
            edit_label_action.setIcon(QIcon.fromTheme("configure"))
            edit_label_action.triggered.connect(self.on_edit_label_action_triggered)
        return menu

    def contextMenuEvent(self, event: QContextMenuEvent):
        menu = self.create_context_menu()
        menu.exec_(self.mapToGlobal(event.pos()))

    def model(self) -> LabelValueTableModel:
        return super().model()

    @pyqtSlot()
    def on_edit_label_action_triggered(self):
        self.edit_label_action_triggered.emit(-1)
