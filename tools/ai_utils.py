"""
ai_utils.py — 公共 AI API 调用

把 requests 调大模型的逻辑抽成独立函数，
LearningTool、FileTool 等都可以复用它。
"""

import requests
from config import API_KEY, BASE_URL, MODEL_NAME


def ask_ai(messages):
    """调用大模型 API 并返回回答文本"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
    }
    resp = requests.post(BASE_URL, json=payload, headers=headers)
    return resp.json()["choices"][0]["message"]["content"]
