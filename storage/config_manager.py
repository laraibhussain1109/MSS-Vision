"""Versioned JSON profiles and last-profile preference."""
import json
from pathlib import Path
from vision.roi import ROIConfig

class ConfigManager:
    def __init__(self, root=None):
        self.root=Path(root or Path(__file__).resolve().parents[1]); self.profiles=self.root/"profiles"; self.profiles.mkdir(exist_ok=True)
        self.state_path=self.root/".station_state.json"
    def load(self,path):
        path=Path(path); data=json.loads(path.read_text(encoding="utf-8")); data["rois"]=[ROIConfig.from_dict(x) for x in data.get("rois",[])]; data["_path"]=str(path); return data
    def save(self,profile,path=None):
        destination=Path(path or profile.get("_path") or self.profiles/"profile.json")
        destination.parent.mkdir(parents=True,exist_ok=True)
        data={k:v for k,v in profile.items() if not k.startswith("_")}; data["rois"]=[r.to_dict() for r in profile.get("rois",[])]
        destination.write_text(json.dumps(data,indent=2),encoding="utf-8"); profile["_path"]=str(destination)
        self.state_path.write_text(json.dumps({"last_profile":str(destination)}),encoding="utf-8"); return destination
    def load_last(self):
        try:
            state=json.loads(self.state_path.read_text()); return self.load(state["last_profile"])
        except (OSError,KeyError,ValueError,json.JSONDecodeError):
            samples=sorted(self.profiles.glob("*.json")); return self.load(samples[0]) if samples else None
