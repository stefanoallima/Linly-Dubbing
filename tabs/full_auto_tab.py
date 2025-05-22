import os
import threading
import datetime
import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                               QScrollArea, QPushButton, QMessageBox, QSplitter,
                               QProgressBar, QTextEdit, QFileDialog)
from PySide6.QtCore import QTimer, Signal, QObject, Qt
import subprocess

from ui_components import VideoPlayer

# Try to import actual function modules
try:
    from tools.do_everything import do_everything
    from tools.utils import SUPPORT_VOICE
except ImportError:
    # Define temporary supported voice list
    SUPPORT_VOICE = ['zh-CN-XiaoxiaoNeural', 'zh-CN-YunxiNeural',
                     'en-US-JennyNeural', 'ja-JP-NanamiNeural']


# Create a signal class for thread communication
class WorkerSignals(QObject):
    finished = Signal(str, str)  # Completion signal: status, video path
    progress = Signal(int, str)  # Progress signal: percentage, status information
    log = Signal(str)  # Log signal: log text


class FullAutoTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Store current configuration
        self.config = self.load_config()

        # Create main horizontal layout with URL input on left, processing buttons and video player on right
        self.main_layout = QHBoxLayout(self)

        # Left configuration area - URL input only
        self.left_widget = QWidget()
        self.left_layout = QVBoxLayout(self.left_widget)

        # Add video URL input
        self.video_url_label = QLabel("Video URL")
        self.video_url = QLineEdit()
        self.video_url.setPlaceholderText("Enter YouTube or Bilibili video, playlist, or channel URL")
        self.video_url.setText("https://www.bilibili.com/video/BV1kr421M7vz/")

        # Select local video button
        self.select_video_button = QPushButton("Select Local Video")
        self.select_video_button.clicked.connect(self.select_local_video)

        self.left_layout.addWidget(self.video_url_label)
        self.left_layout.addWidget(self.video_url)

        # Local video selection layout
        local_video_layout = QHBoxLayout()
        local_video_layout.addWidget(self.select_video_button)
        self.left_layout.addLayout(local_video_layout)

        # Add configuration summary
        self.config_summary = QTextEdit()
        self.config_summary.setReadOnly(True)
        self.config_summary.setMaximumHeight(200)
        self.update_config_summary()

        self.config_summary_label = QLabel("Current Configuration:")
        self.left_layout.addWidget(self.config_summary_label)
        self.left_layout.addWidget(self.config_summary)

        # Right control and display area
        self.right_widget = QWidget()
        self.right_layout = QVBoxLayout(self.right_widget)

        # Execute button area
        self.button_layout = QHBoxLayout()

        # Execute button
        self.run_button = QPushButton("Process")
        self.run_button.clicked.connect(self.run_process)
        self.run_button.setMinimumHeight(50)
        self.run_button.setStyleSheet("background-color: #4CAF50; color: white;")

        # Stop button
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_process)
        self.stop_button.setMinimumHeight(50)
        self.stop_button.setEnabled(False)  # Initially disabled

        # Preview button
        self.preview_button = QPushButton("Preview Video")
        self.preview_button.clicked.connect(self.preview_video)
        self.preview_button.setMinimumHeight(50)
        self.preview_button.setEnabled(False)  # Initially disabled

        # Open containing folder button
        self.open_folder_button = QPushButton("Open Folder")
        self.open_folder_button.clicked.connect(self.open_folder)
        self.open_folder_button.setMinimumHeight(50)
        self.open_folder_button.setEnabled(False)  # Initially disabled

        # Add buttons to button layout
        self.button_layout.addWidget(self.run_button)
        self.button_layout.addWidget(self.stop_button)
        self.button_layout.addWidget(self.open_folder_button)
        self.button_layout.addWidget(self.preview_button)
        self.right_layout.addLayout(self.button_layout)

        # Progress bar
        self.progress_layout = QVBoxLayout()
        self.progress_label = QLabel("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_layout.addWidget(QLabel("Progress:"))
        self.progress_layout.addWidget(self.progress_bar)
        self.progress_layout.addWidget(self.progress_label)
        self.right_layout.addLayout(self.progress_layout)

        # Status display
        self.status_label = QLabel("Ready")
        self.right_layout.addWidget(QLabel("Status:"))
        self.right_layout.addWidget(self.status_label)

        # Create right vertical splitter, top for video player, bottom for log
        self.right_splitter = QSplitter(Qt.Vertical)

        # Video player container
        self.video_container = QWidget()
        self.video_layout = QVBoxLayout(self.video_container)
        self.video_layout.addWidget(QLabel("Video Preview:"))
        self.video_player = VideoPlayer("Synthesized Video")
        self.video_layout.addWidget(self.video_player)
        self.video_container.setLayout(self.video_layout)

        # Log container
        self.log_container = QWidget()
        self.log_layout = QVBoxLayout(self.log_container)
        self.log_layout.addWidget(QLabel("Processing Log:"))

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)  # Set to read-only
        self.log_text.setLineWrapMode(QTextEdit.WidgetWidth)  # Auto-wrap
        self.log_layout.addWidget(self.log_text)

        # Log control buttons
        self.log_button_layout = QHBoxLayout()
        self.clear_log_button = QPushButton("Clear Log")
        self.clear_log_button.clicked.connect(self.clear_log)
        self.save_log_button = QPushButton("Save Log")
        self.save_log_button.clicked.connect(self.save_log)
        self.log_button_layout.addWidget(self.clear_log_button)
        self.log_button_layout.addWidget(self.save_log_button)
        self.log_layout.addLayout(self.log_button_layout)

        self.log_container.setLayout(self.log_layout)

        # Add video and log areas to right splitter
        self.right_splitter.addWidget(self.video_container)
        self.right_splitter.addWidget(self.log_container)

        # Set initial splitter ratio (60% video, 40% log)
        self.right_splitter.setSizes([600, 400])

        # Add splitter to right layout
        self.right_layout.addWidget(self.right_splitter)

        # Add left and right areas to main layout
        # Use QSplitter to allow user to adjust left and right widths
        self.main_splitter = QSplitter()
        self.main_splitter.addWidget(self.left_widget)
        self.main_splitter.addWidget(self.right_widget)

        # Set initial splitter ratio (30% left, 70% right)
        self.main_splitter.setSizes([300, 700])

        self.main_layout.addWidget(self.main_splitter)
        self.setLayout(self.main_layout)

        # Processing thread
        self.worker_thread = None
        self.is_processing = False
        self.signals = WorkerSignals()
        self.signals.finished.connect(self.process_finished)
        self.signals.progress.connect(self.update_progress)
        self.signals.log.connect(self.append_log)

        # Store generated video path
        self.generated_video_path = None

        # Actual progress update
        self.current_progress = 0
        self.progress_steps = [
            "Downloading video...", "Voice separation...", "AI speech recognition...",
            "Subtitle translation...", "AI voice synthesis...", "Video synthesis..."
        ]
        self.current_step = 0

        # Initialize log
        self.append_log("System initialization complete, ready to process")

    def update_config_summary(self):
        """Update configuration summary display"""
        config = self.load_config()
        if config:
            summary_text = "● Output Directory: {}".format(config.get("video_folder", "videos"))
            summary_text += "● Resolution: {}".format(config.get("resolution", "1080p"))
            summary_text += "● Voice Separation: {}, Device: {}".format(
                config.get("model", "htdemucs_ft"),
                config.get("device", "auto")
            )
            summary_text += "● Speech Recognition: {}, Model: {}".format(
                config.get("asr_model", "WhisperX"),
                config.get("whisperx_size", "large")
            )
            summary_text += "● Translation Method: {}".format(config.get("translation_method", "LLM"))
            summary_text += "● TTS Method: {}, Language: {}".format(
                config.get("tts_method", "EdgeTTS"),
                config.get("target_language_tts", "Chinese")
            )
            summary_text += "● Add Subtitles: {}, Speed Factor: {}".format(
                "Yes" if config.get("add_subtitles", True) else "No",
                config.get("speed_factor", 1.00)
            )
            self.config_summary.setText(summary_text)
        else:
            self.config_summary.setText("No configuration found, using default settings")

    def select_local_video(self):
        """Select local video file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "", "Video Files (*.mp4 *.avi *.mkv *.mov *.flv)"
        )
        if file_path:
            self.video_url.setText(file_path)
            self.append_log(f"Selected local video file: {file_path}")

    def load_config(self):
        """Load configuration from file"""
        try:
            config_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(config_dir, "config.json")

            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return config
            else:
                return None
        except Exception as e:
            self.append_log(f"Failed to load configuration: {str(e)}")
            return None

    def update_config(self, new_config):
        """Update current configuration"""
        self.config = new_config
        self.update_config_summary()

    def update_progress(self, progress, status):
        """Update processing progress"""
        # Ensure progress bar matches status information
        self.current_progress = progress
        self.progress_bar.setValue(progress)
        self.progress_label.setText(status)
        self.append_log(f"Progress update: {progress}% - {status}")

    def process_thread(self):
        """异步处理线程"""
        config = self.load_config() or {}
        try:
            self.signals.log.emit("Starting process...")
            self.signals.progress.emit(0, "Initializing...")
            url = self.video_url.text()

            # Log important parameters
            self.signals.log.emit(f"Video folder: {config.get('video_folder', 'videos')}")
            self.signals.log.emit(f"Video URL: {url}")
            self.signals.log.emit(f"Resolution: {config.get('resolution', '1080p')}")

            # More detailed parameter logging
            self.signals.log.emit("-" * 50)
            self.signals.log.emit("Processing parameters:")
            self.signals.log.emit(f"Video count: {config.get('video_count', 5)}")
            self.signals.log.emit(f"Resolution: {config.get('resolution', '1080p')}")
            self.signals.log.emit(f"Voice separation model: {config.get('model', 'htdemucs_ft')}")
            self.signals.log.emit(f"Compute device: {config.get('device', 'auto')}")
            self.signals.log.emit(f"Shift count: {config.get('shifts', 5)}")
            self.signals.log.emit(f"ASR model: {config.get('asr_method', 'WhisperX')}")
            self.signals.log.emit(f"WhisperX model size: {config.get('whisperx_size', 'large')}")
            self.signals.log.emit(f"Translation method: {config.get('translation_method', 'LLM')}")
            self.signals.log.emit(f"TTS method: {config.get('tts_method', 'EdgeTTS')}")
            self.signals.log.emit("-" * 50)

            # 更新进度信息 - 设置步骤1：下载视频
            self.signals.progress.emit(5, f"{self.progress_steps[0]} (5%)")

            # 实际的处理调用
            result, video_path = do_everything(
                config.get('video_folder', 'videos'),  # 使用配置中的参数或默认值
                url,
                config.get('video_count', 5),
                config.get('resolution', '1080p'),
                config.get('model', 'htdemucs_ft'),
                config.get('device', 'auto'),
                config.get('shifts', 5),
                config.get('asr_model', 'WhisperX'),
                config.get('whisperx_size', 'large'),
                config.get('batch_size', 32),
                config.get('separate_speakers', True),
                config.get('min_speakers', None),
                config.get('max_speakers', None),
                config.get('translation_method', 'LLM'),
                config.get('target_language_translation', '简体中文'),
                config.get('tts_method', 'EdgeTTS'),
                config.get('target_language_tts', '中文'),
                config.get('edge_tts_voice', 'zh-CN-XiaoxiaoNeural'),
                config.get('add_subtitles', True),
                config.get('speed_factor', 1.00),
                config.get('frame_rate', 30),
                config.get('background_music', None),
                config.get('bg_music_volume', 0.5),
                config.get('video_volume', 1.0),
                config.get('output_resolution', '1080p'),
                config.get('max_workers', 1),
                config.get('max_retries', 3)
            )

            # 完成处理，设置100%进度
            self.signals.progress.emit(100, "Processing complete!")
            self.signals.log.emit(f"Processing complete: {result}")
            if video_path:
                self.signals.log.emit(f"Generated video path: {video_path}")

            # 处理完成，发送信号
            self.signals.finished.emit(result, video_path if video_path else "")

        except Exception as e:
            # 捕获并记录完整的堆栈跟踪信息
            import traceback
            stack_trace = traceback.format_exc()
            error_msg = f"Processing failed: {str(e)}\n\nStack trace:\n{stack_trace}"
            self.signals.log.emit(error_msg)
            self.signals.progress.emit(0, "Processing failed")
            self.signals.finished.emit(f"Processing failed: {str(e)}", "")

    def run_process(self):
        """开始处理"""
        if self.is_processing:
            return

        self.is_processing = True
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.preview_button.setEnabled(False)
        self.open_folder_button.setEnabled(False)
        self.status_label.setText("Processing...")

        # Reset progress
        self.current_progress = 0
        self.current_step = 0
        self.progress_bar.setValue(0)
        self.progress_label.setText("Preparing...")

        # Log process start
        self.append_log("-" * 50)
        self.append_log(f"Started processing - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.append_log(f"Video URL: {self.video_url.text()}")

        # Create and start processing thread
        self.worker_thread = threading.Thread(target=self.process_thread)
        self.worker_thread.daemon = True
        self.worker_thread.start()

    def stop_process(self):
        """Stop processing"""
        if not self.is_processing:
            return

        # In actual application, add logic to stop processing
        # TODO: Add code to interrupt processing thread

        self.is_processing = False
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Processing stopped")
        self.append_log("User manually stopped processing")

    def process_finished(self, result, video_path):
        """Process completion callback"""
        self.is_processing = False
        self.run_button.setEnabled(True)  # Re-enable one-click processing button
        self.stop_button.setEnabled(False)  # Disable stop processing button
        self.status_label.setText(result)

        # Store generated video path
        self.generated_video_path = video_path

        # 记录处理完成
        self.append_log(f"Processing completed - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.append_log(f"Result: {result}")

        # If video path exists, enable preview and open folder buttons, and load video
        if video_path and os.path.exists(video_path):
            self.preview_button.setEnabled(True)
            self.open_folder_button.setEnabled(True)
            self.video_player.set_video(video_path)
            self.append_log(f"Generated video path: {video_path}")
        else:
            self.append_log("No video generated or invalid video path")

    def preview_video(self):
        """Preview generated video"""
        if self.generated_video_path and os.path.exists(self.generated_video_path):
            # If video is already loaded, play directly
            # Otherwise reload the video
            if not hasattr(self.video_player,
                           'video_path') or self.video_player.video_path != self.generated_video_path:
                self.video_player.set_video(self.generated_video_path)

            # Play video
            self.video_player.play_pause()
            self.append_log(f"Previewing video: {self.generated_video_path}")

    def open_folder(self):
        """Open containing directory"""
        if self.generated_video_path and os.path.exists(self.generated_video_path):
            folder_path = os.path.dirname(self.generated_video_path)
            self.append_log(f"Opening folder: {folder_path}")

            # Open folder based on operating system
            if sys.platform == 'win32':
                os.startfile(folder_path)
            elif sys.platform == 'darwin':  # macOS
                subprocess.run(['open', folder_path])
            else:  # linux
                subprocess.run(['xdg-open', folder_path])

    def append_log(self, message):
        """Append log information"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        self.log_text.append(log_message)
        # Scroll to bottom
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def clear_log(self):
        """Clear log"""
        self.log_text.clear()
        self.append_log("Log cleared")

    def save_log(self):
        """Save log"""
        try:
            # Create log directory
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # Create log filename
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = os.path.join(log_dir, f"process_log_{timestamp}.txt")

            # Save log content
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(self.log_text.toPlainText())

            self.append_log(f"Log saved to: {log_file}")
        except Exception as e:
            self.append_log(f"Failed to save log: {str(e)}")