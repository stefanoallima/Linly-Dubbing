# -*- coding: utf-8 -*-
import json
import os
import translators as ts
from dotenv import load_dotenv
from loguru import logger
load_dotenv()

def translator_response(messages, to_language = 'zh-CN', translator_server = 'bing'):
    if 'Chinese' in to_language:
        to_language = 'zh-CN'
    elif 'English' in to_language:
        to_language = 'en'
    elif 'Dutch' in to_language:
        to_language = 'nl'
    translation = ''
    for retry in range(3):
        try:
            translation = ts.translate_text(query_text=messages, translator=translator_server, from_language='auto', to_language=to_language)
            break
        except Exception as e:
            logger.info(f'translation failed! {e}')
            print('translation failed!')
    return translation

if __name__ == '__main__':
    response = translator_response('Hello, how are you?', 'Simplified Chinese', 'bing')
    print(response)
    response = translator_response('Hello, how have you been recently?', 'English', 'google')
    print(response)