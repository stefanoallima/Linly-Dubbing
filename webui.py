import gradio as gr
from tools.step000_video_downloader import download_from_url
from tools.step010_demucs_vr import separate_all_audio_under_folder
from tools.step020_asr import transcribe_all_audio_under_folder
from tools.step030_translation import translate_all_transcript_under_folder
from tools.step040_tts import generate_all_wavs_under_folder
from tools.step050_synthesize_video import synthesize_all_video_under_folder
from tools.do_everything import do_everything
from tools.utils import SUPPORT_VOICE

# One-click Automation Interface
full_auto_interface = gr.Interface(
    fn=do_everything,
    inputs=[
        gr.Textbox(label='Output Folder', value='videos'),
        gr.Group([
            gr.Textbox(label='Video URL', placeholder='Enter YouTube or Bilibili video, playlist, or channel URL',
                       value='https://www.bilibili.com/video/BV1kr421M7vz/'),
            gr.File(label='Or Upload Video File', file_types=['video'])
        ]),
        gr.Slider(minimum=1, maximum=100, step=1, label='Number of Videos to Download', value=5),
        gr.Radio(['4320p', '2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p'], label='Resolution', value='1080p'),

        gr.Radio(['htdemucs', 'htdemucs_ft', 'htdemucs_6s', 'hdemucs_mmi', 'mdx', 'mdx_extra', 'mdx_q', 'mdx_extra_q', 'SIG'], label='Model', value='htdemucs_ft'),
        gr.Radio(['auto', 'cuda', 'cpu'], label='Compute Device', value='auto'),
        gr.Slider(minimum=0, maximum=10, step=1, label='Number of Shifts', value=5),

        gr.Dropdown(['WhisperX', 'FunASR'], label='ASR Model Selection', value='WhisperX'),
        gr.Radio(['large', 'medium', 'small', 'base', 'tiny'], label='WhisperX Model Size', value='large'),
        gr.Slider(minimum=1, maximum=128, step=1, label='Batch Size', value=32),
        gr.Checkbox(label='Separate Multiple Speakers', value=True),
        gr.Radio([None, 1, 2, 3, 4, 5, 6, 7, 8, 9], label='Minimum Speakers', value=None),
        gr.Radio([None, 1, 2, 3, 4, 5, 6, 7, 8, 9], label='Maximum Speakers', value=None),

        gr.Dropdown(['OpenAI', 'LLM', 'Google Translate', 'Bing Translate', 'Ernie'], label='Translation Method', value='LLM'),
        gr.Dropdown(['Chinese (Simplified)', 'Chinese (Traditional)', 'English', 'Cantonese', 'Japanese', 'Korean'], label='Target Language', value='English'),

        gr.Dropdown(['xtts', 'cosyvoice', 'EdgeTTS'], label='AI Voice Generation Method', value='xtts'),
        gr.Dropdown(['Chinese', 'English', 'Cantonese', 'Japanese', 'Korean', 'Spanish', 'French'], label='Target Language', value='English'),
        gr.Dropdown(SUPPORT_VOICE, value='en-US-JennyNeural', label='EdgeTTS Voice Selection'),

        gr.Checkbox(label='Add Subtitles', value=True),
        gr.Slider(minimum=0.5, maximum=2, step=0.05, label='Speed Multiplier', value=1.00),
        gr.Slider(minimum=1, maximum=60, step=1, label='Frame Rate', value=30),
        gr.Audio(label='Background Music', sources=['upload']),
        gr.Slider(minimum=0, maximum=1, step=0.05, label='Background Music Volume', value=0.5),
        gr.Slider(minimum=0, maximum=1, step=0.05, label='Video Volume', value=1.0),
        gr.Radio(['4320p', '2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p'], label='Resolution', value='1080p'),

        gr.Slider(minimum=1, maximum=100, step=1, label='Max Workers', value=1),
        gr.Slider(minimum=1, maximum=10, step=1, label='Max Retries', value=3),
    ],
    outputs=[gr.Text(label='Synthesis Status'), gr.Video(label='Synthesized Video Sample Result')],
    allow_flagging='never',
)


# Download Video Interface
download_interface = gr.Interface(
    fn=download_from_url,
    inputs=[
        gr.Textbox(label='Video URL', placeholder='Enter YouTube or Bilibili video, playlist, or channel URL',
                   value='https://www.bilibili.com/video/BV1kr421M7vz/'),
        gr.Textbox(label='Output Folder', value='videos'),
        gr.Radio(['4320p', '2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p'], label='Resolution', value='1080p'),
        gr.Slider(minimum=1, maximum=100, step=1, label='Number of Videos to Download', value=5),
        # gr.Checkbox(label='Single Video', value=False),
    ],
    outputs=[
        gr.Textbox(label='Download Status'), 
        gr.Video(label='Sample Video'), 
        gr.Json(label='Download Info')
    ],
    allow_flagging='never',
)

# Voice Separation Interface
demucs_interface = gr.Interface(
    fn=separate_all_audio_under_folder,
    inputs=[
        gr.Textbox(label='Video Folder', value='videos'),
        gr.Radio(['htdemucs', 'htdemucs_ft', 'htdemucs_6s', 'hdemucs_mmi', 'mdx', 'mdx_extra', 'mdx_q', 'mdx_extra_q', 'SIG'], label='Model', value='htdemucs_ft'),
        gr.Radio(['auto', 'cuda', 'cpu'], label='Compute Device', value='auto'),
        gr.Checkbox(label='Show Progress Bar', value=True),
        gr.Slider(minimum=0, maximum=10, step=1, label='Number of Shifts', value=5),
    ],
    outputs=[
        gr.Text(label='Separation Status'), 
        gr.Audio(label='Vocal Audio'), 
        gr.Audio(label='Instrumental Audio')
    ],
    allow_flagging='never',
)

# ASR (Automatic Speech Recognition) Interface
asr_inference = gr.Interface(
    fn=transcribe_all_audio_under_folder,
    inputs=[
        gr.Textbox(label='Video Folder', value='videos'),
        gr.Dropdown(['WhisperX', 'FunASR'], label='ASR Model', value='WhisperX'),
        gr.Radio(['large', 'medium', 'small', 'base', 'tiny'], label='WhisperX Model Size', value='large'),
        gr.Radio(['auto', 'cuda', 'cpu'], label='Compute Device', value='auto'),
        gr.Slider(minimum=1, maximum=128, step=1, label='Batch Size', value=32),
        gr.Checkbox(label='Separate Multiple Speakers', value=True),
        gr.Radio([None, 1, 2, 3, 4, 5, 6, 7, 8, 9], label='Min Speakers', value=None),
        gr.Radio([None, 1, 2, 3, 4, 5, 6, 7, 8, 9], label='Max Speakers', value=None),
    ],
    outputs=[
        gr.Text(label='ASR Status'), 
        gr.Json(label='Recognition Results')
    ],
    allow_flagging='never',
)

# Translation Interface
translation_interface = gr.Interface(
    fn=translate_all_transcript_under_folder,
    inputs=[
        gr.Textbox(label='Video Folder', value='videos'),
        gr.Dropdown(['OpenAI', 'LLM', 'Google Translate', 'Bing Translate', 'Ernie'], label='Translation Method', value='LLM'),
        gr.Dropdown(['Chinese (Simplified)', 'Chinese (Traditional)', 'English', 'Cantonese', 'Japanese', 'Korean'], label='Target Language', value='English'),
    ],
    outputs=[
        gr.Text(label='Translation Status'), 
        gr.Json(label='Summary Results'), 
        gr.Json(label='Translation Results')
    ],
    allow_flagging='never',
)

# TTS (Text-to-Speech) Interface
tts_interface = gr.Interface(
    fn=generate_all_wavs_under_folder,
    inputs=[
        gr.Textbox(label='Video Folder', value='videos'),
        gr.Dropdown(['xtts', 'cosyvoice', 'EdgeTTS'], label='TTS Method', value='xtts'),
        gr.Dropdown(['Chinese', 'English', 'Cantonese', 'Japanese', 'Korean', 'Spanish', 'French'], label='Target Language', value='English'),
        gr.Dropdown(SUPPORT_VOICE, value='en-US-JennyNeural', label='EdgeTTS Voice'),
    ],
    outputs=[
        gr.Text(label='Synthesis Status'), 
        gr.Audio(label='Synthesized Speech'), 
        gr.Audio(label='Original Audio')
    ],
    allow_flagging='never',
)

# Video Synthesis Interface
synthesize_video_interface = gr.Interface(
    fn=synthesize_all_video_under_folder,
    inputs=[
        gr.Textbox(label='Video Folder', value='videos'),
        gr.Checkbox(label='Add Subtitles', value=True),
        gr.Slider(minimum=0.5, maximum=2, step=0.05, label='Speed Multiplier', value=1.00),
        gr.Slider(minimum=1, maximum=60, step=1, label='Frame Rate', value=30),
        gr.Audio(label='Background Music', sources=['upload'], type='filepath'),
        gr.Slider(minimum=0, maximum=1, step=0.05, label='Music Volume', value=0.5),
        gr.Slider(minimum=0, maximum=1, step=0.05, label='Video Volume', value=1.0),
        gr.Radio(['4320p', '2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p'], label='Resolution', value='1080p'),
    ],
    outputs=[
        gr.Text(label='Synthesis Status'), 
        gr.Video(label='Synthesized Video')
    ],
    allow_flagging='never',
)

linly_talker_interface = gr.Interface(
    fn=lambda: None,
    inputs=[
        gr.Textbox(label='Video Folder', value='videos'),
        gr.Dropdown(['Wav2Lip', 'Wav2Lipv2','SadTalker'], label='AI Dubbing Method', value='Wav2Lip'),
    ],      
    outputs=[
        gr.Markdown(value="Under development. Please stay tuned. Reference: [Linly-Talker GitHub](https://github.com/Kedreamix/Linly-Talker)"),
        gr.Text(label='Synthesis Status'),
        gr.Video(label='Synthesized Video')
    ],
)

my_theme = gr.themes.Soft()
# Main Application Interface
app = gr.TabbedInterface(
    theme=my_theme,
    interface_list=[
        full_auto_interface,
        download_interface,
        demucs_interface,
        asr_inference,
        translation_interface,
        tts_interface,
        synthesize_video_interface,
        linly_talker_interface
    ],
    tab_names=[
        'One-Click Automation', 
        'Download Video', 'Voice Separation', 'Speech Recognition', 'Subtitle Translation', 'TTS', 'Video Synthesis',
        'Linly-Talker (In Development)'],
    title='Linly-Dubbing - AI Video Dubbing & Translation Tool'
)

if __name__ == '__main__':
    app.launch(
        server_name="127.0.0.1", 
        server_port=6006,
        share=True,
        inbrowser=True
    )