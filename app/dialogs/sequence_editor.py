from PyQt6.QtWidgets import QDialog,QVBoxLayout,QListWidget,QAbstractItemView,QLabel,QDialogButtonBox
class SequenceEditor(QDialog):
    def __init__(self,rois,parent=None):
        super().__init__(parent);self.setWindowTitle("Process Sequence");l=QVBoxLayout(self);l.addWidget(QLabel("Drag required ROIs into the validated production order."));self.list=QListWidget();self.list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        for r in sorted((r for r in rois if r.sequence_enabled),key=lambda x:x.sequence_position):self.list.addItem(f"{r.id}|{r.display_name}")
        l.addWidget(self.list);b=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);b.accepted.connect(self.accept);b.rejected.connect(self.reject);l.addWidget(b)
    def ids(self):return [self.list.item(i).text().split('|',1)[0] for i in range(self.list.count())]
