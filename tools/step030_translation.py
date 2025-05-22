# -*- coding: utf-8 -*-
import json
import os
import re

from dotenv import load_dotenv
import time
from loguru import logger
from tools.step031_translation_openai import openai_response
from tools.step032_translation_llm import llm_response
from tools.step033_translation_translator import translator_response
from tools.step034_translation_ernie import ernie_response
from tools.step035_translation_qwen import qwen_response
from tools.step036_translation_ollama import ollama_response

load_dotenv()
import traceback

def get_necessary_info(info: dict):
    return {
        'title': info['title'],
        'uploader': info['uploader'],
        'description': info['description'],
        'upload_date': info['upload_date'],
        # 'categories': info['categories'],
        'tags': info['tags'],
    }

def ensure_transcript_length(transcript, max_length=4000):
    mid = len(transcript)//2
    before, after = transcript[:mid], transcript[mid:]
    length = max_length//2
    return before[:length] + after[-length:]

def split_text_into_sentences(para):
    # Split text into sentences using punctuation
    para = re.sub('([。！？\?])([^，。！？\?”’》])', r"\1\n\2", para)  # Single character sentence delimiters
    para = re.sub('(\.{6})([^，。！？\?”’》])', r"\1\n\2", para)  # English ellipsis
    para = re.sub('(\…{2})([^，。！？\?”’》])', r"\1\n\2", para)  # Chinese ellipsis
    para = re.sub('([。！？\?][”’])([^，。！？\?”’》])', r'\1\n\2', para)
    # Place newline after quotation marks following punctuation
    para = para.rstrip()  # Remove trailing newlines
    return para.split("\n")

def translation_postprocess(result):
    # Post-process translation results
    result = re.sub(r'\（[^)]*\）', '', result)  # Remove parentheses and content
    result = result.replace('...', '，')  # Replace ellipsis with comma
    result = re.sub(r'(?<=\d),(?=\d)', '', result)  # Remove commas between numbers
    result = result.replace('²', 'squared').replace(
        '————', ':').replace('——', ':').replace('°', 'degrees')  # Replace special characters with English equivalents
    result = result.replace("AI", 'artificial intelligence')
    result = result.replace('变压器', "Transformer")
    return result

def valid_translation(text, translation):
    # Check if translation text is enclosed in triple backticks
    
    if (translation.startswith('```') and translation.endswith('```')):
        translation = translation[3:-3]
        return True, translation_postprocess(translation)
    
    if (translation.startswith('“') and translation.endswith('”')) or (translation.startswith('"') and translation.endswith('"')):
        translation = translation[1:-1]
        return True, translation_postprocess(translation)
    
    if ('翻译' in translation or "译文" in translation or "Translation" in translation) and '：“' in translation and '”' in translation:
        translation = translation.split('：“')[-1].split('”')[0]
        return True, translation_postprocess(translation)
    
    if ('翻译' in translation or "译文" in translation or "Translation" in translation) and '："' in translation and '"' in translation:
        translation = translation.split('："')[-1].split('"')[0]
        return True, translation_postprocess(translation)

    if ('翻译' in translation or "译文" in translation or "Translation" in translation) and ':"' in translation and '"' in translation:
        translation = translation.split(':"')[-1].split('"')[0]
        return True, translation_postprocess(translation)
    
    if ('翻译' in translation or "译文" in translation or "Translation" in translation) and ': "' in translation and '"' in translation:
        translation = translation.split(': "')[-1].split('"')[0]
        return True, translation_postprocess(translation)
    

    if len(text) <= 10:
        if len(translation) > 15:
            return False, f'Only translate the following sentence and give me the result.'
    elif len(translation) > len(text)*0.75:
        return False, f'The translation is too long. Only translate the following sentence and give me the result.'
    
    forbidden = ['翻译', '译文', '这句', '\n', '简体中文', '中文', 'translate', 'Translate', 'translation', 'Translation']
    translation = translation.strip()
    for word in forbidden:
        if word in translation:
            return False, f"Don't include `{word}` in the translation. Only translate the following sentence and give me the result."
    
    return True, translation_postprocess(translation)


def split_sentences(translation, use_char_based_end=True):
    output_data = []
    for item in translation:
        start = item['start']
        text = item['text']
        speaker = item['speaker']
        translation_text = item['translation']

        # Check if translation text is empty
        if not translation_text or len(translation_text.strip()) == 0:
            # If translation is empty, use original time range and skip splitting
            output_data.append({
                "start": round(start, 3),
                "end": round(item['end'], 3),
                "text": text,
                "speaker": speaker,
                "translation": translation_text or "Not translated"  # Provide default value if empty string
            })
            continue

        sentences = split_text_into_sentences(translation_text)

        if use_char_based_end:
            # Avoid division by zero error
            duration_per_char = (item['end'] - item['start']) / max(1, len(translation_text))
        else:
            duration_per_char = 0

        # logger.info(f'Char duration: {duration_per_char}')
        for sentence in sentences:
            if use_char_based_end:
                sentence_end = start + duration_per_char * len(sentence)
            else:
                sentence_end = item['end']

            # Append the new item
            output_data.append({
                "start": round(start, 3),
                "end": round(sentence_end, 3),
                "text": text,
                "speaker": speaker,
                "translation": sentence
            })

            # Update the start for the next sentence
            if use_char_based_end:
                start = sentence_end

    return output_data

def summarize(info, transcript, target_language='English', method = 'LLM'):
    transcript = ' '.join(line['text'] for line in transcript)
    transcript = ensure_transcript_length(transcript, max_length=2000)
    info_message = f'Title: "{info["title"]}" Author: "{info["uploader"]}". ' 
    
    if method in ['Google Translate', 'Bing Translate']:
        full_description = f'{info_message}\n{transcript}\n{info_message}\n'
        translation = translator_response(full_description, target_language)
        return {
                'title': translator_response(info['title'], target_language),
                'author': info['uploader'],
                'summary': translation,
                'language': target_language
            }

    full_description = f'The following is the full content of the video:\n{info_message}\n{transcript}\n{info_message}\nAccording to the above content, detailedly Summarize the video in JSON format:\n```json\n{{"title": "", "summary": ""}}\n```'
    
    messages = [
        {'role': 'system',
            'content': f'You are a expert in the field of this video. Please detailedly summarize the video in JSON format.\n```json\n{{"title": "the title of the video", "summary", "the summary of the video"}}\n```'},
        {'role': 'user', 'content': full_description},
    ]
    retry_message=''
    success = False
    for retry in range(9):
        try:
            messages = [
                {'role': 'system', 'content': f'You are a expert in the field of this video. Please summarize the video in JSON format.\n```json\n{{"title": "the title of the video", "summary", "the summary of the video"}}\n```'},
                {'role': 'user', 'content': full_description+retry_message},
            ]
            if method == 'LLM':
                response = llm_response(messages)
            elif method == 'OpenAI':
                response = openai_response(messages)
            elif method == 'Ernie':
                system_content = messages[0]['content']
                user_messages = messages[1:]
                response = ernie_response(user_messages, system=system_content)
            elif method == '阿里云-通义千问':
                response = qwen_response(messages)
            elif method == 'Ollama':  # Adding support for Ollama
                response = ollama_response(messages)
            else:
                raise Exception('Invalid method')
            summary = response.replace('\n', '')
            if '视频标题' in summary:
                raise Exception("Contains '视频标题'")
            logger.info(summary)
            summary = re.findall(r'\{.*?\}', summary)[0]
            summary = json.loads(summary)
            summary = {
                'title': summary['title'].replace('title:', '').strip(),
                'summary': summary['summary'].replace('summary:', '').strip()
            }
            if summary['title'] == '' or summary['summary'] == '':
                raise Exception('Invalid summary')
            
            if 'title' in summary['title']:
                raise Exception('Invalid summary')
            success = True
            break
        except Exception as e:
            traceback.print_exc()
            retry_message += '\nSummarize the video in JSON format:\n```json\n{"title": "", "summary": ""}\n```'
            logger.warning(f'Summary failed\n{e}')
            time.sleep(1)
            
    if not success:
        raise Exception(f'Summary failed')
            
    messages = [
        {'role': 'system',
            'content': f'You are a native speaker of {target_language}. Please translate the title and summary into {target_language} in JSON format. ```json\n{{"title": "the {target_language} title of the video", "summary", "the {target_language} summary of the video", "tags": [list of tags in {target_language}]}}\n```.'},
        {'role': 'user',
            'content': f'The title of the video is "{summary["title"]}". The summary of the video is "{summary["summary"]}". Tags: {info["tags"]}.\nPlease translate the above title and summary and tags into {target_language} in JSON format. ```json\n{{"title": "", "summary", ""， "tags": []}}\n```. Remember to translate the title and the summary and tags into {target_language} in JSON.'},
    ]
    while True:
        try: 
            logger.info(summary)
            if target_language in summary['title'] or target_language in summary['summary']:
                raise Exception('Invalid translation')
            title = summary['title'].strip()
            if (title.startswith('"') and title.endswith('"')) or (title.startswith('“') and title.endswith('”')) or (title.startswith('‘') and title.endswith('’')) or (title.startswith("'") and title.endswith("'")) or (title.startswith('《') and title.endswith('》')):
                title = title[1:-1]
            result = {
                'title': title,
                'author': info['uploader'],
                'summary': summary['summary'],
                'tags': info['tags'],
                'language': target_language
            }
            return result
        except Exception as e:
            logger.warning(f'Translation failed\n{e}')
            time.sleep(1)

def _translate(summary, transcript, target_language='English', method='LLM'):

    info = f'This is a video called "{summary["title"]}". {summary["summary"]}.'
    full_translation = []
    if target_language == 'Simplified Chinese':
        fixed_message = [
            {'role': 'system', 'content': f'You are an expert in the field of this video.\n{info}\nTranslate the sentence into {target_language}. Below, I will ask you to act as a translator, your goal is to translate any language into {target_language}, please translate naturally, fluently and idiomatically, using beautiful and elegant expressions. Please translate "agent" in artificial intelligence as "intelligent body", and in reinforcement learning, it is `Q-Learning` instead of `Queue Learning`. Mathematical formulas are written in plain text, do not use latex. Ensure the translation is accurate and concise. Pay attention to faithfulness, expressiveness, and elegance.'},
            {'role': 'user', 'content': f'Use idiomatic {target_language} to translate: "Knowledge is power."'},
            {'role': 'assistant', 'content': 'Translation: "Knowledge is power."'},
            {'role': 'user', 'content': f'Use idiomatic {target_language} to translate: "To be or not to be, that is the question."'},
            {'role': 'assistant', 'content': 'Translation: "To be or not to be, that is the question."'}
        ]
    else:
        # For other languages, we keep the template general
        fixed_message = [
            {'role': 'system', 'content': f'You are a language expert specializing in translating content from various fields. The current task involves translating the transcript of a video titled "{summary["title"]}". The summary of the video is: {summary["summary"]}. Your goal is to translate the following sentences into {target_language}. Please ensure that the translations are accurate, maintain the original meaning and tone, and are expressed in a clear and fluent manner.'},
            {'role': 'user', 'content': 'Please translate the following text: "Original Text"'},
            {'role': 'assistant', 'content': 'Translated text: "Translated Text"'},
            {'role': 'user', 'content': 'Translate the following text: "Another Original Text"'},
            {'role': 'assistant', 'content': 'Translated text: "Another Translated Text"'}
        ]

    history = []
    
    for line in transcript:
        text = line['text']

        retry_message = 'Only translate the quoted sentence and give me the final translation.'
        if method == 'Google Translate':
            translation = translator_response(text, to_language = target_language, translator_server='google')
        elif method == 'Bing Translate':
            translation = translator_response(text, to_language = target_language, translator_server='bing')
        else:
            for retry in range(10):
                messages = fixed_message + \
                    history[-30:] + [{'role': 'user',
                                    'content': f'Translate:"{text}"'}]
                # print(messages)
                try:
                    if method == 'LLM':
                        response = llm_response(messages)
                    elif method == 'OpenAI':
                        response = openai_response(messages)
                    elif method == 'Ernie':
                        system_content = messages[0]['content']
                        user_messages = messages[1:]
                        response = ernie_response(user_messages, system=system_content)
                    elif method == 'Qwen':
                        response = qwen_response(messages)
                    elif method == 'Ollama':  # Adding support for Ollama
                        response = ollama_response(messages)
                    else:
                        raise Exception('Invalid method')
                    translation = response.replace('\n', '')
                    logger.info(f'Original text: {text}')
                    logger.info(f'Translation: {translation}')
                    success, translation = valid_translation(text, translation)
                    if not success:
                        retry_message += translation
                        raise Exception('Invalid translation')
                    break
                except Exception as e:
                    logger.error(e)
                    logger.warning('Translation failed')
                    time.sleep(1)
        full_translation.append(translation)
        history.append({'role': 'user', 'content': f'Translate:"{text}"'})
        history.append({'role': 'assistant', 'content': f'Translation: "{translation}"'})
        time.sleep(0.1)
        
    return full_translation

def translate(method, folder, target_language='English'):
    if os.path.exists(os.path.join(folder, 'translation.json')):
        logger.info(f'Translation already exists in {folder}')
        return True
    
    info_path = os.path.join(folder, 'download.info.json')
    # Not necessarily download.info.json
    if os.path.exists(info_path):
        with open(info_path, 'r', encoding='utf-8') as f:
            info = json.load(f)
        info = get_necessary_info(info)
    else:
        info = {
            'title': os.path.basename(folder),
            'uploader': 'Unknown',
            'description': 'Unknown',
            'upload_date': 'Unknown',
            'tags': []
        }
    transcript_path = os.path.join(folder, 'transcript.json')
    with open(transcript_path, 'r', encoding='utf-8') as f:
        transcript = json.load(f)
    
    summary_path = os.path.join(folder, 'summary.json')
    if os.path.exists(summary_path):
        summary = json.load(open(summary_path, 'r', encoding='utf-8'))
    else:
        summary = summarize(info, transcript, target_language, method)
        if summary is None:
            logger.error(f'Failed to summarize {folder}')
            return False
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

    translation_path = os.path.join(folder, 'translation.json')
    translation = _translate(summary, transcript, target_language, method)
    for i, line in enumerate(transcript):
        line['translation'] = translation[i]
    transcript = split_sentences(transcript)
    with open(translation_path, 'w', encoding='utf-8') as f:
        json.dump(transcript, f, indent=2, ensure_ascii=False)
    return summary, transcript

def translate_all_transcript_under_folder(folder, method, target_language):
    summary_json , translate_json = None, None
    for root, dirs, files in os.walk(folder):
        if 'transcript.json' in files and 'translation.json' not in files:
            summary_json , translate_json = translate(method, root, target_language)
        elif 'translation.json' in files:
            summary_json = json.load(open(os.path.join(root, 'summary.json'), 'r', encoding='utf-8'))
            translate_json = json.load(open(os.path.join(root, 'translation.json'), 'r', encoding='utf-8'))
    print(summary_json, translate_json)
    return f'Translated all videos under {folder}',summary_json , translate_json

if __name__ == '__main__':
    # translate_all_transcript_under_folder(r'videos', 'LLM' , 'Simplified Chinese')
    # translate_all_transcript_under_folder(r'videos', 'OpenAI' , 'Simplified Chinese')
    translate_all_transcript_under_folder(r'videos', 'ernie' , 'Simplified Chinese')