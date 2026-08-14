"""
ai_utils.py — 公共 AI API 调用

把 requests 调大模型的逻辑抽成独立函数，
LearningTool、FileTool 等都可以复用它。
"""

import json
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
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        logger.info(f"API调用成功，回复长度：{len(content)}")
        return content
    except requests.exceptions.RequestException as e:
        logger.error(f"API网络请求失败：{e}")
        raise
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"API响应解析失败：{e}，响应内容：{resp.text[:200]}")
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
        data = resp.json()
        message = data["choices"][0]["message"]
        has_tool_calls = "tool_calls" in message
        logger.info(f"API调用成功，{'包含工具调用' if has_tool_calls else '普通回复'}")
        return message
    except requests.exceptions.RequestException as e:
        logger.error(f"API网络请求失败：{e}")
        raise
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"API响应解析失败：{e}，响应内容：{resp.text[:200]}")
        raise


def ask_ai_with_tools_stream(messages, tools=None, tool_choice="auto", on_content=None):
    """流式调用大模型 API，支持 function calling

    与 ask_ai_with_tools 的区别：
    - 请求带 stream=true，回复内容一块一块到达
    - 每收到一段文字就调用 on_content(text)（用于实时显示）
    - 工具调用参数是碎片到达的，函数内部负责拼接，返回时已是完整结构

    Args:
        messages: 消息列表
        tools: 工具定义列表（OpenAI function calling 格式）
        tool_choice: "auto" 让模型自行决定是否调用工具
        on_content: 可选回调，每收到一段文字就调用 on_content(text)

    Returns:
        dict: 完整的 message 对象（content 为拼接全文，或含完整的 tool_calls）
    """
    logger.debug(f"调用API（流式工具模式），消息数：{len(messages)}，工具数：{len(tools) if tools else 0}")
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": True,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice

    try:
        resp = requests.post(BASE_URL, json=payload, headers=headers, stream=True)
        resp.raise_for_status()# 主动校验 HTTP 状态码
    except requests.exceptions.RequestException as e:
        logger.error(f"API网络请求失败：{e}")
        raise

    # 工具调用碎片桶：index -> {"id": ..., "name": ..., "arguments": ...}
    tool_calls_buckets = {} # 存储工具调用碎片桶
    content_parts = [] # 存储拼接的文字块

    try:
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            chunk = json.loads(data)
            choices = chunk.get("choices", [])
            if not choices:
                continue
            delta = choices[0].get("delta", {})

            # 情况1：普通文字块 → 拼接 + 回调
            content = delta.get("content")
            if content:
                content_parts.append(content)
                if on_content:
                    on_content(content)

            # 情况2：工具调用碎片 → 往桶里拼
            for piece in delta.get("tool_calls") or []:
                idx = piece.get("index", 0)
                if idx not in tool_calls_buckets:
                    tool_calls_buckets[idx] = {"id": "", "name": "", "arguments": ""}
                if piece.get("id"):
                    tool_calls_buckets[idx]["id"] = piece["id"]
                fn = piece.get("function") or {}
                if fn.get("name"):
                    tool_calls_buckets[idx]["name"] += fn["name"]
                if fn.get("arguments"):
                    tool_calls_buckets[idx]["arguments"] += fn["arguments"]
    except json.JSONDecodeError as e:
        logger.error(f"流式响应解析失败：{e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"流式连接中断：{e}")
        raise

    # 组装成与 ask_ai_with_tools 相同的返回结构
    if tool_calls_buckets:
        tool_calls = []
        for idx in sorted(tool_calls_buckets):
            b = tool_calls_buckets[idx]
            tool_calls.append({
                "id": b["id"] or f"call_{idx}",
                "type": "function",
                "function": {
                    "name": b["name"],
                    "arguments": b["arguments"],
                },
            })
        message = {"role": "assistant", "content": None, "tool_calls": tool_calls}
        logger.info(f"API流式调用完成，包含 {len(tool_calls)} 个工具调用")
    else:
        message = {"role": "assistant", "content": "".join(content_parts)}
        logger.info(f"API流式调用完成，回复长度：{len(message['content'])}")
    return message
