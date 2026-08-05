"""
ai_utils.py — 公共 AI API 调用

把 requests 调大模型的逻辑抽成独立函数，
LearningTool、FileTool 等都可以复用它。
"""

import logging
import requests
from config import API_KEY, BASE_URL, MODEL_NAME

logger = logging.getLogger(__name__)


def ask_ai(messages):
    """调用大模型 API 并返回回答文本"""
    logger.debug(f"调用API（简单模式），消息数：{len(messages)}")
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
    }
    try:
        resp = requests.post(BASE_URL, json=payload, headers=headers)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"] 
        logger.info(f"API调用成功，回复长度：{len(content)}")
        return content
    except requests.exceptions.RequestException as e:
        logger.error(f"API调用失败：{e}")
        raise


def ask_ai_with_tools(messages, tools=None, tool_choice="auto"):
    """调用大模型 API，支持 function calling

    Args:
        messages: 消息列表
        tools: 工具定义列表（OpenAI function calling 格式）
        tool_choice: "auto" 让模型自行决定是否调用工具

    Returns:
        dict: 完整的 message 对象（可能包含 tool_calls 字段）
    """
    logger.debug(f"调用API（工具模式），消息数：{len(messages)}，工具数：{len(tools) if tools else 0}")
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

    try:
        resp = requests.post(BASE_URL, json=payload, headers=headers)
        resp.raise_for_status()
        message = resp.json()["choices"][0]["message"]
        has_tool_calls = "tool_calls" in message
        logger.info(f"API调用成功，{'包含工具调用' if has_tool_calls else '普通回复'}")
        return message
    except requests.exceptions.RequestException as e:
        logger.error(f"API调用失败：{e}")
        raise
