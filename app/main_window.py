"""Production HMI shell and station orchestration."""
from __future__ import annotations
import logging, time
from datetime import datetime
from pathlib import Path
import cv2
from PyQt6.QtCore import Qt,QThread,QTimer
from PyQt6.QtGui import QAction,QKeySequence
from PyQt6.QtWidgets import (QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QFrame,QLabel,QPushButton,QComboBox,QMessageBox,QFileDialog,QToolBar,QGroupBox,QScrollArea,QApplication)
from app.dialogs.camera_settings import CameraSettingsDialog
from app.dialogs.general_settings import GeneralSettingsDialog
from app.dialogs.history_dialog import HistoryDialog
from app.dialogs.roi_editor import ROIEditorDialog
from app.dialogs.sequence_editor import SequenceEditor
from process.sequence_engine import SequenceEngine,SequenceStatus
from process.cycle_manager import CycleManager
from process.event import ProcessEvent
from storage.config_manager import ConfigManager
from storage.database import InspectionDatabase
from vision.camera_worker import CameraWorker
from vision.vision_worker import VisionWorker
from vision.roi import ROIState
from widgets.camera_view import CameraView
from widgets.status_card import StatusCard
from widgets.sequence_widget import SequenceWidget
from widgets.event_timeline import EventTimeline

log=logging.getLogger(__name__)
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle('MSS Vision — Process Validation Station');self.resize(1600,940);self.config=ConfigManager();self.db=InspectionDatabase();self.profile=self.config.load_last();self.frame=None;self.results={};self.reference=None;self.camera=None;self.vision_thread=None;self.cycle=None
        if self.profile is None:self.profile={'version':1,'process_name':'New Process','cycle_mode':'manual','camera':{'source':0,'width':1280,'height':720,'fps':30},'rois':[],'timing':{'simultaneous_window_ms':300},'alignment':{'mode':'none'},'logging':{'save_pass_image':True,'save_ng_image':True},'simulation':False}
        self.build_ui();self.build_actions();self.apply_profile();QTimer.singleShot(300,self.start_camera)
        if not self.profile['rois']:QTimer.singleShot(800,self.first_run)
    def build_ui(self):
        root=QWidget();self.setCentralWidget(root);outer=QVBoxLayout(root);outer.setContentsMargins(16,12,16,12);header=QHBoxLayout();brand=QLabel('MSS  VISION');brand.setStyleSheet('font-size:25px;font-weight:900;color:#eaf0f2;letter-spacing:2px');sub=QLabel('PROCESS VALIDATION');sub.setStyleSheet('color:#17c6e3;font-weight:700');self.camera_badge=QLabel('●  CAMERA INITIALIZING');self.camera_badge.setStyleSheet('color:#f2b84b;font-weight:700');self.mode=QComboBox();self.mode.addItems(['OPERATOR MODE','ENGINEERING MODE']);self.mode.currentIndexChanged.connect(self.toggle_engineering);header.addWidget(brand);header.addWidget(sub);header.addStretch();header.addWidget(self.mode);header.addWidget(self.camera_badge);outer.addLayout(header)
        body=QHBoxLayout();left=QVBoxLayout();self.view=CameraView();left.addWidget(self.view,1);self.debug=QLabel('FPS: —   |   Alignment: NONE   |   Frame: —');self.debug.setStyleSheet('color:#7ddcf0');self.debug.hide();left.addWidget(self.debug);body.addLayout(left,7)
        side=QVBoxLayout();self.status=StatusCard();side.addWidget(self.status);process=QGroupBox('PROCESS STATUS');pl=QVBoxLayout(process);self.process_label=QLabel();self.step_label=QLabel();self.expected_label=QLabel();self.expected_label.setStyleSheet('font-size:20px;font-weight:800;color:#f2b84b');pl.addWidget(self.process_label);pl.addWidget(self.step_label);pl.addWidget(self.expected_label);self.sequence=SequenceWidget();pl.addWidget(self.sequence);side.addWidget(process);events=QGroupBox('EVENT TIMELINE');el=QVBoxLayout(events);self.timeline=EventTimeline();el.addWidget(self.timeline);side.addWidget(events,1);self.sim_box=QGroupBox('⚠ SIMULATION MODE');self.sim_layout=QVBoxLayout(self.sim_box);side.addWidget(self.sim_box);body.addLayout(side,3);outer.addLayout(body,1)
        footer=QHBoxLayout();self.buttons={}
        for text,slot,style in [('START INSPECTION',self.start_cycle,'primary'),('STOP',self.stop_cycle,''),('RESET CYCLE',self.reset_cycle,'danger'),('EDIT ROIs',self.edit_rois,''),('CAPTURE REFERENCE',self.capture_reference,''),('CAMERA',self.camera_settings,''),('SETTINGS',self.settings,''),('HISTORY',self.history,'')]:
            b=QPushButton(text);b.setObjectName(style);b.clicked.connect(slot);footer.addWidget(b);self.buttons[text]=b
        outer.addLayout(footer)
    def build_actions(self):
        menu=self.menuBar();profiles=menu.addMenu('&Profiles')
        for text,slot in [('New Profile',self.new_profile),('Load Profile…',self.load_profile),('Save Profile',self.save_profile),('Save Profile As…',lambda:self.save_profile(True)),('Load Reference Image…',self.load_reference),('Exit',self.close)]:a=profiles.addAction(text);a.triggered.connect(slot)
        tools=menu.addMenu('&Engineering');tools.addAction('Edit ROIs',self.edit_rois);tools.addAction('Edit Sequence',self.edit_sequence);tools.addAction('Camera Settings',self.camera_settings);tools.addAction('Station Settings',self.settings);tools.addAction('History',self.history)
        for key,slot in [('F5',self.start_cycle),('F6',self.stop_cycle),('F7',self.reset_cycle),('F8',self.edit_rois)]:a=QAction(self);a.setShortcut(QKeySequence(key));a.triggered.connect(slot);self.addAction(a)
    @property
    def rois(self):return self.profile.get('rois',[])
    def ordered(self):return sorted((r for r in self.rois if r.enabled and r.sequence_enabled),key=lambda r:r.sequence_position)
    def apply_profile(self):
        sequence=[r.id for r in self.ordered()];self.engine=SequenceEngine(sequence,self.profile.get('timing',{}).get('simultaneous_window_ms',300));self.cycle=CycleManager(self.engine,self.db);self.process_label.setText('CURRENT PROCESS\n'+self.profile.get('process_name','Unnamed'));self.view.set_rois(self.rois);self.refresh_state();self.build_simulation()
    def build_simulation(self):
        while self.sim_layout.count():
            item=self.sim_layout.takeAt(0);item.widget() and item.widget().deleteLater()
        enabled=self.profile.get('simulation',False);self.sim_box.setVisible(enabled)
        if enabled:
            label=QLabel('Manual events use the production sequence engine.');label.setStyleSheet('color:#f2b84b;font-weight:700');self.sim_layout.addWidget(label)
            for r in self.ordered():b=QPushButton('Trigger '+r.display_name);b.clicked.connect(lambda checked=False,x=r:self.handle_event(ProcessEvent(x.id,x.display_name,timestamp_ms=int(time.time()*1000))));self.sim_layout.addWidget(b)
    def start_camera(self):
        self.stop_workers();self.camera=CameraWorker(self.profile.get('camera',{}));self.camera.connection_changed.connect(self.camera_connection);self.vision_thread=QThread(self);self.vision=VisionWorker(self.rois);self.vision.moveToThread(self.vision_thread);self.camera.frame_ready.connect(self.vision.process);self.vision.processed.connect(self.on_processed);self.vision.insertion.connect(self.handle_event);self.vision_thread.start();self.camera.start()
    def stop_workers(self):
        if self.camera:self.camera.stop();self.camera=None
        if self.vision_thread:self.vision_thread.quit();self.vision_thread.wait(2000);self.vision_thread=None
    def camera_connection(self,ok,detail):
        self.camera_badge.setText(('●  CAMERA ONLINE  ' if ok else '●  CAMERA OFFLINE  ')+detail);self.camera_badge.setStyleSheet('color:'+('#19d66b' if ok else '#ff3b4f')+';font-weight:700')
        if not ok and self.engine.status not in (SequenceStatus.PASS,SequenceStatus.NG):
            self.status.set_status('CAMERA DISCONNECTED','Automatic reconnection is active.')
        elif ok and self.engine.status == SequenceStatus.IDLE:
            self.status.set_status('READY','Camera connected. Establishing safe ROI baseline.')
    def on_processed(self,frame,results):
        self.frame=frame;self.results=results;self.view.set_frame(frame,results)
        self.debug.setText(f"Frame: {frame.shape[1]}×{frame.shape[0]}   |   Alignment: {self.profile.get('alignment',{}).get('mode','none').upper()}   |   ROIs: {len(results)}")
        if self.profile.get('cycle_mode')=='automatic' and self.engine.status==SequenceStatus.IDLE and self.baseline_ready() and not self.present_ids():self.start_cycle()
    def baseline_ready(self):return bool(self.rois) and hasattr(self,'vision') and all(self.vision.filters[r.id].baselined for r in self.ordered())
    def present_ids(self):return {r.id for r in self.ordered() if self.results.get(r.id,{}).get('stable')=='PRESENT'}
    def start_cycle(self):
        if not self.ordered():QMessageBox.warning(self,'No sequence','Configure and order at least one ROI first.');return
        if not self.profile.get('simulation') and not self.baseline_ready():QMessageBox.warning(self,'Establishing baseline','Wait until every ROI has a stable initial state. Existing clips will not be treated as insertion events.');return
        result=self.cycle.start(self.profile.get('process_name',''),self.present_ids());self.timeline.clear();self.timeline.add_event('Cycle Started')
        if result.status==SequenceStatus.NG:self.finish_result(result)
        else:self.vision.enabled=True;self.status.set_status('IN PROCESS','Insert one component at a time in the configured order.');self.refresh_state()
    def handle_event(self,event):
        if self.engine.status!=SequenceStatus.RUNNING:return
        result=self.cycle.event(event);self.timeline.add_event(f'{event.roi_name} INSERTED  ({event.occupancy*100:.1f}%)');self.refresh_state()
        if result.status in (SequenceStatus.PASS,SequenceStatus.NG):self.finish_result(result,event.roi_id)
    def finish_result(self,result,wrong=None):
        self.vision.enabled=False;path=self.save_snapshot(result.status.value,wrong);self.cycle.finish(result,path);duration=(datetime.now(self.cycle.started_at.tzinfo)-self.cycle.started_at).total_seconds() if self.cycle.started_at else 0
        if result.status==SequenceStatus.PASS:self.status.set_status('PASS',f'PROCESS COMPLETE\nCycle time: {duration:.2f} seconds');self.timeline.add_event('PASS')
        else:self.status.set_status('NG',result.reason);self.timeline.add_event('NG — '+result.reason);self.view.wrong=wrong
        if self.profile.get('ui',{}).get('beep'):QApplication.beep()
    def save_snapshot(self,result,wrong=None):
        if self.frame is None or not self.profile.get('logging',{}).get('save_'+result.lower()+'_image',True):return None
        image=self.frame.copy();h,w=image.shape[:2]
        for r in self.rois:
            pts=r.pixel_polygon(w,h);color=(0,255,0) if result=='PASS' else (0,0,255) if r.id==wrong else (0,215,255);cv2.polylines(image,[pts],True,color,3);cv2.putText(image,r.display_name,tuple(pts[0]),cv2.FONT_HERSHEY_SIMPLEX,.7,color,2)
        cv2.rectangle(image,(0,0),(w,55),(10,120,20) if result=='PASS' else (30,20,160),-1);cv2.putText(image,f'PROCESS {result}  {self.engine.reason}',(15,38),cv2.FONT_HERSHEY_SIMPLEX,.8,(255,255,255),2)
        folder=Path('inspection_data')/result;folder.mkdir(parents=True,exist_ok=True);path=folder/(datetime.now().strftime('%Y-%m-%d_%H-%M-%S')+f'_CYCLE_{(self.cycle.cycle_id or 0):06d}_{result}.jpg');cv2.imwrite(str(path),image);return str(path)
    def stop_cycle(self):
        if hasattr(self,'vision'):self.vision.enabled=False
        self.status.set_status('PAUSED','Inspection stopped by operator.');self.timeline.add_event('Inspection Paused')
    def reset_cycle(self):
        if hasattr(self,'vision'):self.vision.enabled=False
        self.engine.reset();self.view.completed=set();self.view.wrong=None;self.timeline.clear()
        if self.present_ids():self.status.set_status('WAITING FOR PART RESET','Remove all required clips / replace component before starting a new cycle.')
        else:self.status.set_status('READY','Starting conditions valid. Press START INSPECTION.');self.refresh_state()
    def refresh_state(self):
        seq=self.ordered();step=self.engine.current_step;self.sequence.set_sequence([r.display_name for r in seq],step);self.view.completed=set(self.engine.detected_sequence);self.view.expected=self.engine.expected
        expected=next((r.display_name for r in seq if r.id==self.engine.expected),'—');self.step_label.setText(f'CURRENT STEP: {min(step+1,len(seq)) if seq else 0} / {len(seq)}');self.expected_label.setText('EXPECTED: '+expected)
    def toggle_engineering(self,index):self.view.engineering=bool(index);self.debug.setVisible(bool(index));self.view.update()
    def edit_rois(self):
        self.stop_cycle();source=self.reference if self.reference is not None else self.frame
        if source is None:QMessageBox.warning(self,'No image','Connect a camera or load a reference image first.');return
        d=ROIEditorDialog(self.rois,source,self)
        if d.exec():self.profile['rois']=d.rois;self.apply_profile();self.save_profile()
    def edit_sequence(self):
        d=SequenceEditor(self.rois,self)
        if d.exec():
            order=d.ids()
            for r in self.rois:
                if r.id in order:r.sequence_position=order.index(r.id)+1
            self.apply_profile();self.save_profile()
    def capture_reference(self):
        if self.frame is None:QMessageBox.warning(self,'No image','No live frame is available.');return
        self.reference=self.frame.copy();path=Path('profiles')/(Path(self.profile.get('_path','reference')).stem+'_reference.jpg');cv2.imwrite(str(path),self.reference);self.profile['reference_image']=str(path);self.save_profile();QMessageBox.information(self,'Reference captured',f'Saved reference image:\n{path}')
    def load_reference(self):
        p,_=QFileDialog.getOpenFileName(self,'Load reference image','','Images (*.png *.jpg *.jpeg *.bmp)');
        if p:
            img=cv2.imread(p)
            if img is None:QMessageBox.warning(self,'Invalid image','OpenCV could not read that image.')
            else:self.reference=img;self.profile['reference_image']=p
    def camera_settings(self):
        d=CameraSettingsDialog(self.profile.get('camera',{}),self)
        if d.exec():self.profile['camera']=d.result_settings();self.save_profile();self.start_camera()
    def settings(self):
        d=GeneralSettingsDialog(self.profile,self)
        if d.exec():d.apply();self.apply_profile();self.save_profile()
    def history(self):HistoryDialog(self.db,self).exec()
    def first_run(self):QMessageBox.information(self,'First-time station setup','Welcome to MSS Vision.\n\n1. Select Camera\n2. Capture or load a reference image\n3. Draw ROIs\n4. Calibrate HSV detection\n5. Arrange the sequence\n6. Save the profile\n7. Start inspection')
    def new_profile(self):
        if QMessageBox.question(self,'New profile','Create a blank machine profile?')==QMessageBox.StandardButton.Yes:self.profile={'version':1,'process_name':'New Process','cycle_mode':'manual','camera':{'source':0,'width':1280,'height':720,'fps':30},'rois':[],'timing':{'simultaneous_window_ms':300},'alignment':{'mode':'none'},'logging':{'save_pass_image':True,'save_ng_image':True},'simulation':False};self.apply_profile();self.first_run()
    def load_profile(self):
        p,_=QFileDialog.getOpenFileName(self,'Load profile','profiles','JSON (*.json)')
        if p:
            try:self.profile=self.config.load(p);self.apply_profile();self.start_camera()
            except Exception as e:QMessageBox.critical(self,'Invalid profile',str(e))
    def save_profile(self,save_as=False):
        path=None
        if save_as or not self.profile.get('_path'):
            path,_=QFileDialog.getSaveFileName(self,'Save profile','profiles/process_profile.json','JSON (*.json)')
            if not path:return
        try:self.config.save(self.profile,path)
        except Exception as e:QMessageBox.critical(self,'Save failed',str(e))
    def closeEvent(self,e):self.stop_workers();e.accept()
