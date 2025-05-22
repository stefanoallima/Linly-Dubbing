# -*- coding: utf-8 -*-
import json
import os
import shutil
import string
import subprocess
import time
import random
import traceback

from loguru import logger


def split_text(input_data,
               punctuations=['，', '；', '：', '。', '？', '！', '\n', '"']):
    """
    Split text into sentences based on punctuation marks
    
    Parameters:
        input_data: List of input text segments
        punctuations: List of punctuation marks to split on
    """

    # Function to check if a character is a punctuation mark
    def is_punctuation(char):
        return char in punctuations

    # Process each item in the input data
    output_data = []
    for item in input_data:
        start = item["start"]
        text = item["translation"]
        speaker = item.get("speaker", "SPEAKER_00")
        original_text = item["text"]
        sentence_start = 0

        # Calculate the duration for each character
        duration_per_char = (item["end"] - item["start"]) / len(text)
        for i, char in enumerate(text):
            # If the character is a punctuation, split the sentence
            if not is_punctuation(char) and i != len(text) - 1:
                continue
            if i - sentence_start < 5 and i != len(text) - 1:
                continue
            if i < len(text) - 1 and is_punctuation(text[i+1]):
                continue
            sentence = text[sentence_start:i+1]
            sentence_end = start + duration_per_char * len(sentence)

            # Append the new item
            output_data.append({
                "start": round(start, 3),
                "end": round(sentence_end, 3),
                "text": original_text,
                "translation": sentence,
                "speaker": speaker
            })

            # Update the start for the next sentence
            start = sentence_end
            sentence_start = i + 1

    return output_data
    
def format_timestamp(seconds):
    """Converts seconds to the SRT time format."""
    millisec = int((seconds - int(seconds)) * 1000)
    hours, seconds = divmod(int(seconds), 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millisec:03}"

def generate_srt(translation, srt_path, speed_up=1, max_line_char=30):
    translation = split_text(translation)
    with open(srt_path, 'w', encoding='utf-8') as f:
        for i, line in enumerate(translation):
            start = format_timestamp(line['start']/speed_up)
            end = format_timestamp(line['end']/speed_up)
            text = line['translation']
            line = len(text)//(max_line_char+1) + 1
            avg = min(round(len(text)/line), max_line_char)
            text = '\n'.join([text[i*avg:(i+1)*avg]
                             for i in range(line)])
            f.write(f'{i+1}\n')
            f.write(f'{start} --> {end}\n')
            f.write(f'{text}\n\n')


def get_aspect_ratio(video_path):
    command = ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
               '-show_entries', 'stream=width,height', '-of', 'json', video_path]
    result = subprocess.run(command, capture_output=True, text=True)
    dimensions = json.loads(result.stdout)['streams'][0]
    return dimensions['width'] / dimensions['height']


def convert_resolution(aspect_ratio, resolution='1080p'):
    if aspect_ratio < 1:
        width = int(resolution[:-1])
        height = int(width / aspect_ratio)
    else:
        height = int(resolution[:-1])
        width = int(height * aspect_ratio)
    # make sure width and height are divisible by 2
    width = width - width % 2
    height = height - height % 2
    
    # return f'{width}x{height}'
    return width, height
    
def synthesize_video(folder, subtitles=True, speed_up=1.00, fps=30, resolution='1080p', background_music=None, watermark_path=None, bgm_volume=0.5, video_volume=1.0):
    # if os.path.exists(os.path.join(folder, 'video.mp4')):
    #     logger.info(f'Video already synthesized in {folder}')
    #     return
    
    translation_path = os.path.join(folder, 'translation.json')
    input_audio = os.path.join(folder, 'audio_combined.wav')
    input_video = os.path.join(folder, 'download.mp4')
    
    if not os.path.exists(translation_path) or not os.path.exists(input_audio):
        return
    
    with open(translation_path, 'r', encoding='utf-8') as f:
        translation = json.load(f)
        
    srt_path = os.path.join(folder, 'subtitles.srt')
    final_video = os.path.join(folder, 'video.mp4')
    generate_srt(translation, srt_path, speed_up)
    srt_path = srt_path.replace('\\', '/')
    aspect_ratio = get_aspect_ratio(input_video)
    width, height = convert_resolution(aspect_ratio, resolution)
    resolution = f'{width}x{height}'
    font_size = int(width/128)
    outline = int(round(font_size/8))
    video_speed_filter = f"setpts=PTS/{speed_up}"
    audio_speed_filter = f"atempo={speed_up}"
    font_path = "./font/SimHei.ttf"
    subtitle_filter = f"subtitles={srt_path}:fontsdir={os.path.dirname(font_path)}:force_style='FontName=SimHei,FontSize={font_size},PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline={outline},WrapStyle=2'"
    # subtitle_filter = f"subtitles={srt_path}:force_style='FontName=Arial,FontSize={font_size},PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline={outline},WrapStyle=2'"

    filter_complex = f"[0:v]{video_speed_filter}[v];[1:a]{audio_speed_filter}[a]"
        
    # Add watermark if specified
    if watermark_path:
        watermark_filter = f";[2:v]scale=iw*0.15:ih*0.15[wm];[v][wm]overlay=W-w-10:H-h-10[v]"
        ffmpeg_command = [
            'ffmpeg',
            '-i', input_video,
            '-i', input_audio,
            '-i', watermark_path,
            '-filter_complex', filter_complex + watermark_filter,
            '-map', '[v]',
            '-map', '[a]',
            '-r', str(fps),
            '-s', resolution,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            final_video,
            '-y',
            '-threads', '2',
        ]
    else:
        ffmpeg_command = [
            'ffmpeg',
            '-i', input_video,
            '-i', input_audio,
            '-filter_complex', filter_complex,
            '-map', '[v]',
            '-map', '[a]',
            '-r', str(fps),
            '-s', resolution,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            final_video,
            '-y',
            '-threads', '2',
        ]
    subprocess.run(ffmpeg_command)
    time.sleep(1)

    # Apply background music if specified
    if background_music:
        final_video_with_bgm = final_video.replace('.mp4', '_bgm.mp4')
        ffmpeg_command_bgm = [
            'ffmpeg',
            '-i', final_video,                # Original video with audio
            '-i', background_music,           # Background music
            '-filter_complex', f'[0:a]volume={video_volume}[v0];[1:a]volume={bgm_volume}[v1];[v0][v1]amix=inputs=2:duration=first[a]',
            '-map', '0:v',                    # Use video from the original input
            '-map', '[a]',                    # Use the mixed audio
            '-c:v', 'copy',                       # Copy the original video codec
            '-c:a', 'aac',                    # Encode the audio as AAC
            final_video_with_bgm,
            '-y',
            '-threads', '2'
        ]
        subprocess.run(ffmpeg_command_bgm)
        os.remove(final_video)
        os.rename(final_video_with_bgm, final_video)
        time.sleep(1)
    # Subtitles are not critical, so we can use try-catch
    try:
        if subtitles:
            final_video_with_subtitles = final_video.replace('.mp4', '_subtitles.mp4')
            add_subtitles(final_video, srt_path, final_video_with_subtitles, subtitle_filter, 'ffmpeg')
            # os.remove(final_video)
            if os.path.exists(final_video):
                os.remove(final_video)
            os.rename(final_video_with_subtitles, final_video)
            time.sleep(1)
    except Exception as e:
        logger.info(f"An error occurred: {e}")
        traceback.format_exc()
def add_subtitles(video_path, srt_path, output_path, subtitle_filter=None, method='ffmpeg'):
    """Add subtitles to a video file.

    Parameters:
        video_path (str): Path to the input video file.
        srt_path (str): Path to the .srt subtitle file.
        output_path (str): Path to the output video file.
        subtitle_filter (str): Custom subtitle filter, defaults to None, using standard filter.
        method (str): Method to use ('moviepy' or 'ffmpeg'), defaults to 'ffmpeg'.

    Returns:
        bool: True if successful, False if failed.
    """
    try:
        # Ensure the temp directory exists
        temp_dir = "temp"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        # Generate a random string as the temporary file name
        # Generate random string as temporary filename
        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        temp_video_path = os.path.join(temp_dir, f"temp_video_{random_string}.mp4")

        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        temp_srt_path = os.path.join(temp_dir, f"temp_srt_{random_string}.srt")

        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        temp_output_path = os.path.join(temp_dir, f"temp_output_{random_string}.mp4")

        # Check if source files exist
        if not os.path.exists(video_path):
            logger.error(f"Input video file does not exist: {video_path}")
            return False

        if not os.path.exists(srt_path):
            logger.error(f"Subtitle file does not exist: {srt_path}")
            return False

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Start copying original files to temporary files
        shutil.copyfile(video_path, temp_video_path)
        shutil.copyfile(srt_path, temp_srt_path)

        # Use absolute paths to avoid path issues
        temp_video_path = os.path.abspath(temp_video_path)
        temp_srt_path = os.path.abspath(temp_srt_path)
        temp_output_path = os.path.abspath(temp_output_path)
        # Start checking if subtitle file exists
        if not os.path.exists(temp_srt_path):
            logger.error(f"Subtitle file does not exist: {temp_srt_path}")
            return False
        # Start checking if video file exists
        if not os.path.exists(temp_video_path):
            logger.error(f"Input video file does not exist: {temp_video_path}")
            return False

        if method == 'moviepy':
            from moviepy import VideoFileClip, TextClip, CompositeVideoClip
            from moviepy.video.tools.subtitles import SubtitlesClip

            # Use moviepy to add subtitles
            video = VideoFileClip(temp_video_path)
            generator = lambda txt: TextClip(txt, font='font/SimHei.ttf', fontsize=24, color='white')
            subtitles = SubtitlesClip(temp_srt_path, generator)
            final_video = video.copy()

            final_video = final_video.set_subtitles(subtitles)
            # Save video
            final_video.write_videofile(temp_output_path, fps=video.fps)

            # Copy back to original location
            if os.path.exists(temp_output_path):
                shutil.copyfile(temp_output_path, output_path)
                logger.info(f"Subtitles added successfully, output to: {output_path}")
                return True
            else:
                logger.error(f"Output file not generated: {temp_output_path}")
                return False

        elif method == 'ffmpeg':
            # Use ffmpeg to add subtitles
            try:
                # Get absolute path to font file
                font_dir = os.path.abspath("./font")

                # Build subtitle filter, using filename reference
                style = "FontName=SimHei,FontSize=15,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2,WrapStyle=2"
                filter_option = f"subtitles={temp_srt_path}:force_style='{style}'"

                # Build command
                command = [
                    'ffmpeg',
                    '-i', f"{temp_video_path}",
                    '-vf', f"{filter_option}",
                    '-c:a', 'copy',
                    f"{temp_output_path}",
                    '-y',
                    '-threads', '2',
                ]

                logger.info(f"Executing FFmpeg command: {' '.join(command)}")

                # Execute command
                result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stderr_output = result.stderr.decode('utf-8', errors='ignore')
                logger.debug(f"FFmpeg output: {stderr_output}")

                # Check if output file was successfully generated
                if os.path.exists(temp_output_path):
                    # Ensure output directory exists
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    shutil.copyfile(temp_output_path, output_path)
                    logger.info(f"Subtitles added successfully, output to: {output_path}")
                    return True
                else:
                    logger.error(f"FFmpeg executed successfully but output file not generated: {temp_output_path}")
                    return False

            except subprocess.CalledProcessError as e:
                logger.error(f"FFmpeg command execution failed: {e}")
                stderr_output = e.stderr.decode('utf-8', errors='ignore') if e.stderr else "No stderr output"
                logger.error(f"FFmpeg error output: {stderr_output}")
                return False

            except Exception as e:
                logger.error(f"Error adding subtitles: {str(e)}")
                import traceback
                logger.error(f"Error stack: {traceback.format_exc()}")
                return False
        else:
            logger.error(f"Unsupported method: {method}. Please use 'moviepy' or 'ffmpeg'")
            return False

    except Exception as e:
        logger.error(f"Error adding subtitles: {str(e)}")
        import traceback
        logger.debug(f"Error details: {traceback.format_exc()}")
        return False
    finally:
        # Clean up temporary files
        temp_files = [temp_video_path, temp_srt_path, temp_output_path]
        if method == 'ffmpeg':
            temp_files.append(os.path.join(temp_dir, "subtitles.srt"))

        for temp_file in temp_files:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    logger.debug(f"Unable to delete temporary file {temp_file}: {e}")

def synthesize_all_video_under_folder(folder, subtitles=True, speed_up=1.00, fps=30, background_music=None, bgm_volume=0.5, video_volume=1.0, resolution='1080p', watermark_path="f_logo.png"):
    watermark_path = None if not os.path.exists(watermark_path) else watermark_path
    output_video = None
    for root, dirs, files in os.walk(folder):
        if 'download.mp4' in files:
            output_video = synthesize_video(root, subtitles=subtitles,
                            speed_up=speed_up, fps=fps, resolution=resolution,
                            background_music=background_music,
                            watermark_path=watermark_path, bgm_volume=bgm_volume, video_volume=video_volume)
        # if 'download.mp4' in files and 'video.mp4' not in files:
        #     output_video = synthesize_video(root, subtitles=subtitles,
        #                      speed_up=speed_up, fps=fps, resolution=resolution,
        #                      background_music=background_music,
        #                      watermark_path=watermark_path, bgm_volume=bgm_volume, video_volume=video_volume)
        # elif 'video.mp4' in files:
        #     output_video = os.path.join(root, 'video.mp4')
        #     logger.info(f'Video already synthesized in {folder}')
    return f'Synthesized all videos under {folder}', output_video

if __name__ == '__main__':
    folder = r"videos/example_video"
    synthesize_all_video_under_folder(folder, 
                                      subtitles=True, 
                                      speed_up=1.00, 
                                      fps=30, 
                                      background_music=None, 
                                      bgm_volume=0.5, 
                                      video_volume=1.0, 
                                      resolution='1080p', 
                                      watermark_path="f_logo.png")