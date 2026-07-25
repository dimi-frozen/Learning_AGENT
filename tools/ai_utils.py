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


def ask_ai_with_tools(messages, tools=None, tool_choice="auto"):
    """调用大模型 API，支持 function calling

    Args:
        messages: 消息列表
        tools: 工具定义列表（OpenAI function calling 格式）
        tool_choice: "auto" 让模型自行决定是否调用工具

    Returns:
        dict: 完整的 message 对象（可能包含 tool_calls 字段）
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice

    resp = requests.post(BASE_URL, json=payload, headers=headers)
    return resp.json()["choices"][0]["message"]
