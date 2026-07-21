"""
memory_tool.py — 简单的对话记忆系统

每次对话结束后将消息存到 chat_memory.json，
下次启动程序时自动加载，让 LLM 看到之前的对话内容。
"""

import json
import os

CHAT_MEMORY_FILE = "chat_memory.json"
MAX_HISTORY = 50  # 最多保留 50 条消息（约 25 轮对话）


class MemoryTool:
    """对话记忆工具：存 JSON、取 JSON"""

    def __init__(self, file_path=CHAT_MEMORY_FILE, max_messages=MAX_HISTORY):
        self.file_path = file_path
        self.max_messages = max_messages

    def save(self, messages):
        """保存消息列表到文件，只保留最近 max_messages 条"""
        trimmed = messages[-self.max_messages:] if len(messages) > self.max_messages else messages
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(trimmed, f, ensure_ascii=False, indent=2)

    def load(self):
        """从文件加载历史消息"""
        if not os.path.exists(self.file_path):
            return []
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def clear(self):
        """清空记忆文件"""
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
            print("记忆已清空")


# 全局单例
memory = MemoryTool()
