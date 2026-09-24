from copy import deepcopy
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog,QHBoxLayout,QVBoxLayout,QPushButton,QTableWidget,QTableWidgetItem,QHeaderView,QMessageBox,QDialogButtonBox
from widgets.camera_view import CameraView
from app.dialogs.roi_settings import ROISettingsDialog
from app.dialogs.color_calibration import ColorCalibrationDialog
class ROIEditorDialog(QDialog):
    def __init__(self,rois,frame,parent=None):
        super().__init__(parent);self.rois=deepcopy(rois);self.frame=frame;self.setWindowTitle('ROI Setup — normalized image coordinates');self.resize(1450,850);root=QHBoxLayout(self);left=QVBoxLayout();tools=QHBoxLayout();self.rect=QPushButton('＋ Rectangle ROI');self.poly=QPushButton('⬡ Polygon ROI');self.rect.clicked.connect(lambda:self.mode(False));self.poly.clicked.connect(lambda:self.mode(True));tools.addWidget(self.rect);tools.addWidget(self.poly);left.addLayout(tools);self.view=CameraView();self.view.frame=frame;self.view.rois=self.rois;self.view.editing=True;self.view.roi_drawn.connect(self.add_drawn);left.addWidget(self.view,1);root.addLayout(left,3);side=QVBoxLayout();self.table=QTableWidget(0,5);self.table.setHorizontalHeaderLabels(['Name','Type','Expected','Order','Required']);self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);side.addWidget(self.table);buttons=(('Configure',self.configure),('Calibrate HSV',self.calibrate),('Duplicate',self.duplicate),('Delete',self.delete),('Move Up',lambda:self.move(-1)),('Move Down',lambda:self.move(1)))
        for text,fn in buttons:b=QPushButton(text);b.clicked.connect(fn);side.addWidget(b)
        box=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);box.accepted.connect(self.accept);box.rejected.connect(self.reject);side.addWidget(box);root.addLayout(side,2);self.refresh()
    def mode(self,poly):self.view.polygon_mode=poly;self.rect.setObjectName('' if poly else 'primary');self.poly.setObjectName('primary' if poly else '');self.rect.style().polish(self.rect);self.poly.style().polish(self.poly)
    def refresh(self):
        self.view.rois=self.rois;self.view.update();self.table.setRowCount(len(self.rois))
        for y,r in enumerate(self.rois):
            for x,v in enumerate((r.display_name,r.roi_type,r.detector,r.sequence_position,'Yes' if r.required else 'No')):self.table.setItem(y,x,QTableWidgetItem(str(v)))
    def selected(self):
        row=self.table.currentRow();return (row,self.rois[row]) if 0<=row<len(self.rois) else (None,None)
    def add_drawn(self,data):
        dlg=ROISettingsDialog(parent=self);dlg.order.setValue(len(self.rois)+1)
        if dlg.exec():self.rois.append(dlg.build(data['shape'],data['points']));self.refresh()
    def configure(self):
        row,r=self.selected()
        if not r:return
        d=ROISettingsDialog(r,self)
        if d.exec():d.build(r.shape,r.points);self.refresh()
    def calibrate(self):
        _,r=self.selected()
        if r and self.frame is not None:ColorCalibrationDialog(r,self.frame,self).exec();self.refresh()
    def duplicate(self):
        _,r=self.selected()
        if r:
            n=deepcopy(r);n.id+= '-copy';n.name+=' Copy';n.display_name+=' Copy';n.points=[[min(1,x+.02),min(1,y+.02)] for x,y in n.points];self.rois.append(n);self.refresh()
    def delete(self):
        row,r=self.selected()
        if r and QMessageBox.question(self,'Delete ROI',f'Delete {r.display_name}?')==QMessageBox.StandardButton.Yes:self.rois.pop(row);self.refresh()
    def move(self,d):
        row,r=self.selected();new=row+d if row is not None else -1
        if r and 0<=new<len(self.rois):self.rois[row],self.rois[new]=self.rois[new],self.rois[row];[setattr(x,'sequence_position',i+1) for i,x in enumerate(self.rois)];self.refresh();self.table.selectRow(new)
