"""Thread-safe-by-connection SQLite traceability repository."""
import json, sqlite3
from datetime import datetime, timezone
from pathlib import Path

class InspectionDatabase:
    def __init__(self,path="inspection_data/inspections.sqlite3"):
        Path(path).parent.mkdir(parents=True,exist_ok=True); self.path=str(path); self._init()
    def connect(self):
        c=sqlite3.connect(self.path); c.row_factory=sqlite3.Row; return c
    def _init(self):
        with self.connect() as c:
            c.executescript("""CREATE TABLE IF NOT EXISTS cycles(id INTEGER PRIMARY KEY AUTOINCREMENT, profile TEXT,start_time TEXT,end_time TEXT,duration REAL,result TEXT,failure_reason TEXT,expected_sequence TEXT,detected_sequence TEXT,image_path TEXT); CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,cycle_id INTEGER,event_time TEXT,roi_name TEXT,event_type TEXT,confidence REAL,occupancy REAL,FOREIGN KEY(cycle_id) REFERENCES cycles(id));""")
    def begin_cycle(self,profile,start,expected):
        with self.connect() as c:
            cur=c.execute("INSERT INTO cycles(profile,start_time,expected_sequence,result) VALUES(?,?,?,?)",(profile,start.isoformat(),json.dumps(expected),"RUNNING")); return cur.lastrowid
    def add_event(self,cycle_id,e):
        with self.connect() as c: c.execute("INSERT INTO events(cycle_id,event_time,roi_name,event_type,confidence,occupancy) VALUES(?,?,?,?,?,?)",(cycle_id,e.iso_time,e.roi_name,e.event_type,e.confidence,e.occupancy))
    def finish_cycle(self,cycle_id,result,reason,detected,image_path=None):
        now=datetime.now(timezone.utc)
        with self.connect() as c:
            row=c.execute("SELECT start_time FROM cycles WHERE id=?",(cycle_id,)).fetchone(); duration=(now-datetime.fromisoformat(row[0])).total_seconds() if row else 0
            c.execute("UPDATE cycles SET end_time=?,duration=?,result=?,failure_reason=?,detected_sequence=?,image_path=? WHERE id=?",(now.isoformat(),duration,result,reason,json.dumps(detected),image_path,cycle_id))
    def cycles(self,search="",result="ALL"):
        q="SELECT * FROM cycles WHERE (profile LIKE ? OR failure_reason LIKE ?)"; args=[f"%{search}%",f"%{search}%"]
        if result != "ALL": q+=" AND result=?"; args.append(result)
        q+=" ORDER BY id DESC"
        with self.connect() as c: return [dict(r) for r in c.execute(q,args)]
    def events(self,cycle_id):
        with self.connect() as c: return [dict(r) for r in c.execute("SELECT * FROM events WHERE cycle_id=? ORDER BY event_time",(cycle_id,))]
