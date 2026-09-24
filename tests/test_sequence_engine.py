from process.event import ProcessEvent
from process.sequence_engine import SequenceEngine,SequenceStatus

def event(name,t):return ProcessEvent(name,name,timestamp_ms=t)
def run(names,times=None,window=300):
    e=SequenceEngine(['A','B','C'],window);e.start();result=None
    for n,t in zip(names,times or range(0,len(names)*1000,1000)):result=e.handle_event(event(n,t))
    return result,e

def test_correct_sequence_passes(): assert run(['A','B','C'])[0].status==SequenceStatus.PASS
def test_b_first_ng(): assert run(['B'])[0].status==SequenceStatus.NG
def test_c_first_ng(): assert run(['C'])[0].status==SequenceStatus.NG
def test_a_then_c_ng(): assert run(['A','C'])[0].status==SequenceStatus.NG
def test_ng_latches_and_cannot_become_pass():
    result,e=run(['A','C']);assert result.status==SequenceStatus.NG;assert e.handle_event(event('B',5000)).status==SequenceStatus.NG
def test_simultaneous_insertions_ng():
    result,_=run(['A','B'],[1000,1210]);assert result.status==SequenceStatus.NG;assert 'MULTIPLE' in result.reason
def test_start_rejects_existing_present():
    e=SequenceEngine(['A','B','C']);assert e.start({'B'}).status==SequenceStatus.NG
