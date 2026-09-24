from vision.roi import ROIState
from vision.temporal_filter import TemporalFilter

def test_initial_present_becomes_baseline_without_event():
    f=TemporalFilter(300,500);assert f.update(ROIState.PRESENT,0) is None;assert f.update(ROIState.PRESENT,300) is None;assert f.stable==ROIState.PRESENT

def test_debounce_and_single_transition():
    f=TemporalFilter(300,500);f.update(ROIState.ABSENT,0);f.update(ROIState.ABSENT,500);assert f.update(ROIState.PRESENT,600) is None;assert f.update(ROIState.PRESENT,899) is None;t=f.update(ROIState.PRESENT,900);assert t and t.current==ROIState.PRESENT;assert f.update(ROIState.PRESENT,2000) is None

def test_unknown_freezes_stable_state():
    f=TemporalFilter(100,100);f.update(ROIState.PRESENT,0);f.update(ROIState.PRESENT,100);f.update(ROIState.UNKNOWN,150,True);assert f.stable==ROIState.PRESENT
