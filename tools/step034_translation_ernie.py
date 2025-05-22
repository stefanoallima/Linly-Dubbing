# -*- coding: utf-8 -*-
import os, json
import requests
from dotenv import load_dotenv
from loguru import logger
load_dotenv()

access_token = None

def get_access_token(api_key, secret_key):
    """
    Get access_token using API Key and Secret Key.
    :param api_key: Application API Key
    :param secret_key: Application Secret Key
    :return: access_token
    """
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
    
    response = requests.post(url, headers={'Content-Type': 'application/json'})
    if response.status_code == 200:
        logger.info("Successfully obtained access_token")
        return response.json().get("access_token")
    else:
        logger.error("Failed to obtain access_token")
        raise Exception("Failed to obtain access_token")

def ernie_response(messages, system=''):
    global access_token
    api_key = os.getenv('BAIDU_API_KEY')
    secret_key = os.getenv('BAIDU_SECRET_KEY')
    if access_token is None:
        access_token = get_access_token(api_key, secret_key)
    model_name = 'yi_34b_chat'
    model_name = 'ernie-speed-128k'
    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/{model_name}?access_token=" + access_token
    payload = json.dumps({
        "messages": messages,
        "system": system
    })
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, data=payload)
        
    if response.status_code == 200:
        response_json = response.json()
        return response_json.get('result')
    else:
        logger.error(f"Request to Baidu API failed, status code: {response.status_code}")
        raise Exception("Request to Baidu API failed")

if __name__ == '__main__':
    # test_message = [{"role": "user", "content": "Hello, introduce yourself"}]
    test_message = [
        {'role': 'user', 'content': 'The following is the full content of the video:\nTitle: "(English without subtitles) Ali is in Venice sending greetings" Author: "Village head fishing in Canada". \nHello guys, how are you? I\'m in Venice now with my partner. We\'re in Venice looking around the amazing streets. I love it. It\'s perfect. Look at that. So nice. I can\'t wait to show you the pizza guys.\nTitle: "(English without subtitles) Ali is in Venice sending greetings" Author: "Village head fishing in Canada". \nAccording to the above content, please summarize the video in JSON format:\n```json\n{"title": "", "summary": ""}\n```'}
        ]
    response = ernie_response(test_message, system='You are an expert in the field of this video. Please summarize the video in JSON format.\n```json\n{"title": "the title of the video", "summary", "the summary of the video"}\n```')
    print(response)