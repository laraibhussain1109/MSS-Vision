from PyQt6.QtWidgets import QListWidget
from datetime import datetime
class EventTimeline(QListWidget):
    def add_event(self,text): self.insertItem(0,f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]}   {text}")
