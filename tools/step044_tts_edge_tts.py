import os
from loguru import logger
import numpy as np
import torch
import time
from .utils import save_wav
import sys

import torchaudio
model = None



# Language codes for Chinese/English/Japanese/Cantonese/Korean
language_map = {
    'Chinese': 'zh-CN-XiaoxiaoNeural',
    'English': 'en-US-MichelleNeural',
    'Japanese': 'ja-JP-NanamiNeural',
    'Cantonese': 'zh-HK-HiuMaanNeural',
    'Korean': 'ko-KR-SunHiNeural'
}

def tts(text, output_path, target_language='English', voice = 'en-US-JennyNeural'):
    if os.path.exists(output_path):
        logger.info(f'TTS {text} already exists')
        return
    for retry in range(3):
        try:
            os.system(f'edge-tts --text "{text}" --write-media "{output_path.replace(".wav", ".mp3")}" --voice {voice}')
            logger.info(f'TTS {text} completed')
            break
        except Exception as e:
            logger.warning(f'TTS {text} failed')
            logger.warning(e)


if __name__ == '__main__':
    speaker_wav = r'videos/example_video/audio_vocals.wav'  # Example audio path
    while True:
        text = input('Enter text:')
        tts(text, f'playground/{text}.wav', target_language='Chinese')
        
