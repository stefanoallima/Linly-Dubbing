import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget
from PySide6.QtCore import Qt

# Please ensure correct module imports
try:
    # Import custom UI components
    from ui_components import (CustomSlider, FloatSlider, RadioButtonGroup,
                               AudioSelector, VideoPlayer)

    # Import feature tabs
    from tabs.full_auto_tab import FullAutoTab
    from tabs.settings_tab import SettingsTab
    from tabs.download_tab import DownloadTab
    from tabs.demucs_tab import DemucsTab
    from tabs.asr_tab import ASRTab
    from tabs.translation_tab import TranslationTab
    from tabs.tts_tab import TTSTab
    from tabs.video_tab import SynthesizeVideoTab
    from tabs.linly_talker_tab import LinlyTalkerTab

    # Try to import actual functionality modules
    try:
        from tools.step000_video_downloader import download_from_url
        from tools.step010_demucs_vr import separate_all_audio_under_folder
        from tools.step020_asr import transcribe_all_audio_under_folder
        from tools.step030_translation import translate_all_transcript_under_folder
        from tools.step040_tts import generate_all_wavs_under_folder
        from tools.step050_synthesize_video import synthesize_all_video_under_folder
        from tools.do_everything import do_everything
        from tools.utils import SUPPORT_VOICE
    except ImportError as e:
        print(f"Warning: Failed to import some tool modules: {e}")
        # Define temporary supported voice list
        SUPPORT_VOICE = ['zh-CN-XiaoxiaoNeural', 'zh-CN-YunxiNeural',
                         'en-US-JennyNeural', 'ja-JP-NanamiNeural']

except ImportError as e:
    print(f"Error: Failed to initialize application: {e}")
    sys.exit(1)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Linly-Dubbing - Intelligent Multi-language AI Dubbing/Translation Tool")
        self.resize(1024, 768)

        # Create tab widget
        self.tab_widget = QTabWidget()

        # Create tab instances
        self.full_auto_tab = FullAutoTab()
        self.settings_tab = SettingsTab()

        # Connect settings page configuration change signal to one-click automation page
        self.settings_tab.config_changed.connect(self.full_auto_tab.update_config)

        # Add tabs
        self.tab_widget.addTab(self.full_auto_tab, "One-Click Automation")
        self.tab_widget.addTab(self.settings_tab, "Settings")
        self.tab_widget.addTab(DownloadTab(), "Video Download")
        self.tab_widget.addTab(DemucsTab(), "Voice Separation")
        self.tab_widget.addTab(ASRTab(), "AI Speech Recognition")
        self.tab_widget.addTab(TranslationTab(), "Subtitle Translation")
        self.tab_widget.addTab(TTSTab(), "AI Voice Synthesis")
        self.tab_widget.addTab(SynthesizeVideoTab(), "Video Synthesis")
        self.tab_widget.addTab(LinlyTalkerTab(), "Linly-Talker Lip Sync (In Development)")

        # Set central widget
        self.setCentralWidget(self.tab_widget)


def main():
    # Set high DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # Set application style
    app.setStyle("Fusion")

    # Create main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()