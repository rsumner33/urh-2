from PyQt5.QtWidgets import QTableView, QMenu

from urh.models.PLabelTableModel import PLabelTableModel


class ProtocolLabelTableView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.delete_action = QAction("Delete selected labels", self)
        self.delete_action.setShortcut(QKeySequence.Delete)
        self.delete_action.setIcon(QIcon.fromTheme("edit-delete"))
        self.delete_action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        self.delete_action.triggered.connect(self.delete_selected_rows)
        self.addAction(self.delete_action)

    def model(self) -> PLabelTableModel:
        return super().model()

    def create_context_menu(self):
        menu = QMenu()
        pos = event.pos()
        row = self.rowAt(pos.y())
        if row != -1:
            delAction = menu.addAction("Delete Protocol Label")
            action = menu.exec_(self.mapToGlobal(pos))
            if action == delAction:
                lbl = self.model().proto_analyzer.protocol_labels[row]
                self.model().remove_label(lbl)


