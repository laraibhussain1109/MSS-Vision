import json
from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLineEdit,QComboBox,QPushButton,QTableWidget,QTableWidgetItem,QFileDialog,QMessageBox,QHeaderView
from storage.export import export_cycles
class HistoryDialog(QDialog):
    def __init__(self,database,parent=None):
        super().__init__(parent);self.db=database;self.rows=[];self.setWindowTitle("Inspection History & Traceability");self.resize(1150,700);l=QVBoxLayout(self);top=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText("Search profile or failure reason…");self.filter=QComboBox();self.filter.addItems(["ALL","PASS","NG","RUNNING"]);go=QPushButton("Search");go.clicked.connect(self.refresh);export=QPushButton("EXPORT TO EXCEL");export.clicked.connect(self.export);top.addWidget(self.search);top.addWidget(self.filter);top.addWidget(go);top.addWidget(export);l.addLayout(top);self.table=QTableWidget(0,7);self.table.setHorizontalHeaderLabels(["Cycle","Date / Start","Duration","Required Sequence","Detected","Result","Failure Reason"]);self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.table.doubleClicked.connect(self.details);l.addWidget(self.table);self.refresh()
    def refresh(self):
        self.rows=self.db.cycles(self.search.text(),self.filter.currentText());self.table.setRowCount(len(self.rows))
        for y,r in enumerate(self.rows):
            vals=(r['id'],r['start_time'],f"{r['duration'] or 0:.2f}s",r['expected_sequence'],r['detected_sequence'],r['result'],r['failure_reason'])
            for x,v in enumerate(vals):self.table.setItem(y,x,QTableWidgetItem(str(v or '')))
    def details(self,index):
        r=self.rows[index.row()];events=self.db.events(r['id']);text=f"Profile: {r['profile']}\nResult: {r['result']}\nReason: {r['failure_reason'] or '—'}\nImage: {r['image_path'] or '—'}\n\nEVENT TIMELINE\n"+"\n".join(f"{e['event_time']}  {e['roi_name']} {e['event_type']}  occupancy={e['occupancy']:.3f}" for e in events);QMessageBox.information(self,f"Cycle {r['id']:06d}",text)
    def export(self):
        p,_=QFileDialog.getSaveFileName(self,"Export inspections","inspection_history.xlsx","Excel (*.xlsx)");
        if p:export_cycles(self.rows,p);QMessageBox.information(self,"Export complete",f"Saved {len(self.rows)} records to\n{p}")
