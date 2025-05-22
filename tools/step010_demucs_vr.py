import shutil
from demucs.api import Separator
import os
from loguru import logger
import time
from .utils import save_wav, normalize_wav
import torch
import gc

# Global variables
auto_device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
separator = None
model_loaded = False  # Added flag to track if model is loaded
current_model_config = {}  # Added variable to store current model configuration


def init_demucs():
    """
    Initialize Demucs model.
    If model is already initialized, return directly without reloading.
    """
    global separator, model_loaded
    if not model_loaded:
        separator = load_model()
        model_loaded = True
    else:
        logger.info("Demucs model already loaded, skipping initialization")


def load_model(model_name: str = "htdemucs_ft", device: str = 'auto', progress: bool = True,
               shifts: int = 5) -> Separator:
    """
    Load Demucs model.
    If model with same configuration is already loaded, return existing model without reloading.
    """
    global separator, model_loaded, current_model_config

    if separator is not None:
        # Check if model needs to be reloaded (different configuration)
        requested_config = {
            'model_name': model_name,
            'device': 'auto' if device == 'auto' else device,
            'shifts': shifts
        }

        if current_model_config == requested_config:
            logger.info(f'Demucs model loaded with same configuration, reusing existing model')
            return separator
        else:
            logger.info(f'Demucs model configuration changed, need to reload')
            # Release existing model resources
            release_model()

    logger.info(f'Loading Demucs model: {model_name}')
    t_start = time.time()

    device_to_use = auto_device if device == 'auto' else device
    separator = Separator(model_name, device=device_to_use, progress=progress, shifts=shifts)

    # Store current model configuration
    current_model_config = {
        'model_name': model_name,
        'device': 'auto' if device == 'auto' else device,
        'shifts': shifts
    }

    model_loaded = True
    t_end = time.time()
    logger.info(f'Demucs model loaded successfully, took {t_end - t_start:.2f} seconds')

    return separator


def release_model():
    """
    Release model resources to prevent memory leaks
    """
    global separator, model_loaded, current_model_config

    if separator is not None:
        logger.info('Releasing Demucs model resources...')
        # Remove reference
        separator = None
        # Force garbage collection
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        model_loaded = False
        current_model_config = {}
        logger.info('Demucs model resources released')


def separate_audio(folder: str, model_name: str = "htdemucs_ft", device: str = 'auto', progress: bool = True,
                   shifts: int = 5) -> None:
    """
    Separate audio file
    """
    global separator
    audio_path = os.path.join(folder, 'audio.wav')
    if not os.path.exists(audio_path):
        return None, None
    vocal_output_path = os.path.join(folder, 'audio_vocals.wav')
    instruments_output_path = os.path.join(folder, 'audio_instruments.wav')

    if os.path.exists(vocal_output_path) and os.path.exists(instruments_output_path):
        logger.info(f'Audio already separated: {folder}')
        return vocal_output_path, instruments_output_path

    logger.info(f'Separating audio: {folder}')

    try:
        # 确保模型已加载并且配置正确
        if not model_loaded or current_model_config.get('model_name') != model_name or \
                (current_model_config.get('device') == 'auto') != (device == 'auto') or \
                current_model_config.get('shifts') != shifts:
            load_model(model_name, device, progress, shifts)

        t_start = time.time()

        try:
            origin, separated = separator.separate_audio_file(audio_path)
        except Exception as e:
            logger.error(f'Audio separation failed: {e}')
            # Try to reload model once when error occurs
            release_model()
            load_model(model_name, device, progress, shifts)
            logger.info(f'Model reloaded, retrying separation...')
            origin, separated = separator.separate_audio_file(audio_path)

        t_end = time.time()
        logger.info(f'Audio separation completed, took {t_end - t_start:.2f} seconds')

        vocals = separated['vocals'].numpy().T
        instruments = None
        for k, v in separated.items():
            if k == 'vocals':
                continue
            if instruments is None:
                instruments = v
            else:
                instruments += v
        instruments = instruments.numpy().T

        save_wav(vocals, vocal_output_path, sample_rate=44100)
        logger.info(f'Vocals saved: {vocal_output_path}')

        save_wav(instruments, instruments_output_path, sample_rate=44100)
        logger.info(f'Instruments saved: {instruments_output_path}')

        return vocal_output_path, instruments_output_path

    except Exception as e:
        logger.error(f'Audio separation failed: {str(e)}')
        # Release model resources and re-raise exception
        release_model()
        raise


def extract_audio_from_video(folder: str) -> bool:
    """
    Extract audio from video
    """
    video_path = os.path.join(folder, 'download.mp4')
    if not os.path.exists(video_path):
        return False
    audio_path = os.path.join(folder, 'audio.wav')
    if os.path.exists(audio_path):
        logger.info(f'Audio already extracted: {folder}')
        return True
    logger.info(f'Extracting audio from video: {folder}')

    os.system(
        f'ffmpeg -loglevel error -i "{video_path}" -vn -acodec pcm_s16le -ar 44100 -ac 2 "{audio_path}"')

    time.sleep(1)
    logger.info(f'音频提取完成: {folder}')
    return True


def separate_all_audio_under_folder(root_folder: str, model_name: str = "htdemucs_ft", device: str = 'auto',
                                    progress: bool = True, shifts: int = 5) -> None:
    """
    Separate all audio files under folder
    """
    global separator
    vocal_output_path, instruments_output_path = None, None

    try:
        for subdir, dirs, files in os.walk(root_folder):
            if 'download.mp4' not in files:
                continue
            if 'audio.wav' not in files:
                extract_audio_from_video(subdir)
            if 'audio_vocals.wav' not in files:
                vocal_output_path, instruments_output_path = separate_audio(subdir, model_name, device, progress,
                                                                            shifts)
            elif 'audio_vocals.wav' in files and 'audio_instruments.wav' in files:
                vocal_output_path = os.path.join(subdir, 'audio_vocals.wav')
                instruments_output_path = os.path.join(subdir, 'audio_instruments.wav')
                logger.info(f'Audio already separated: {subdir}')

        logger.info(f'All audio separation completed: {root_folder}')
        return f'All audio separation completed: {root_folder}', vocal_output_path, instruments_output_path

    except Exception as e:
        logger.error(f'分离音频过程中出错: {str(e)}')
        # 出现任何错误，释放模型资源
        release_model()
        raise


if __name__ == '__main__':
    folder = r"videos"
    separate_all_audio_under_folder(folder, shifts=0)