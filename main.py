"""MSS Vision process validation station entry point."""
import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from app.main_window import MainWindow
from app.theme import DARK_THEME

def configure_logging():
    Path('logs').mkdir(exist_ok=True);handler=RotatingFileHandler('logs/mss_vision.log',maxBytes=2_000_000,backupCount=5,encoding='utf-8');logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(name)s: %(message)s',handlers=[handler,logging.StreamHandler()])
def main():
    configure_logging();app=QApplication(sys.argv);app.setApplicationName('MSS Vision');app.setStyleSheet(DARK_THEME);window=MainWindow();window.show();return app.exec()
if __name__=='__main__':raise SystemExit(main())
