"""
LearningTool — 学习记录与规划工具

将文件读写、AI 调用、日报/计划生成等能力封装为 Tool，
供 ai_chat.py 或其他模块统一调用。
"""

import json
import os
import requests
from datetime import datetime
from config import API_KEY, BASE_URL, MODEL_NAME, LEARN_RECORD_FILE, REPORT_DIR, PLAN_DIR
from prompt import DAILY_PATH, LEARNING_PLAN


class LearningTool:
    """学习工具箱：记录、查询、日报、计划"""

    def __init__(self):
        self.record_file = LEARN_RECORD_FILE
        self.report_dir = REPORT_DIR
        self.plan_dir = PLAN_DIR

    # ── 私有工具函数（原 file_utils） ──────────────────────────

    def _read_json(self, file_path):
        """读取 JSON 文件并返回完整列表"""
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_json(self, file_path, record):
        """向 JSON 文件追加一条记录"""
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []
        data.append(record)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_text(self, file_path, content):
        """覆盖写入纯文本文件"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"文件写入失败：{e}")
            return False

    # ── AI 调用封装 ────────────────────────────────────────────

    def ask_ai(self, messages):
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

    # ── 公开 Tool 接口 ────────────────────────────────────────

    def get_records(self):
        """获取所有学习记录

        Returns:
            list[dict]: 每条记录含 datetime 和 content
        """
        if not os.path.exists(self.record_file):
            return []
        return self._read_json(self.record_file)

    def save_record(self, content):
        """保存一条学习记录（自动添加当前日期）

        Args:
            content: 学习内容描述

        Returns:
            dict: 刚保存的记录 {"datetime": ..., "content": ...}
        """
        record = {
            "datetime": datetime.now().strftime("%Y%m%d"),
            "content": content,
        }
        self._write_json(self.record_file, record)
        return record

    def generate_progress(self, extra_system_prompt=None):
        """基于学习记录生成学习日报并保存到 reports/**

        Args:
            extra_system_prompt: 可选的额外 system prompt（用于注入模式上下文）

        Returns:
            str | None: 日报完整文本，失败返回 None
        """
        records = self.get_records()
        if not records:
            print("暂无学习记录，无法生成日报")
            return None

        learn_text = "\n".join(f"- {r}" for r in records)
        user_content = DAILY_PATH.format(learn_record=learn_text)

        messages = []
        if extra_system_prompt:
            messages.append({"role": "system", "content": extra_system_prompt})
        messages.append({"role": "user", "content": user_content})

        answer = self.ask_ai(messages)

        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"{date_str}_学习日报.md"
        filepath = os.path.join(self.report_dir, filename)
        full_content = f"日期：{date_str}\n---\n{answer}"

        if self._save_text(filepath, full_content):
            print("学习日报保存成功！")
        else:
            print("日报保存失败")

        return full_content

    def generate_plan(self, extra_system_prompt=None):
        """基于学习记录生成学习计划并保存到 plan/**

        Args:
            extra_system_prompt: 可选的额外 system prompt

        Returns:
            str | None: 计划完整文本，失败返回 None
        """
        records = self.get_records()
        if not records:
            print("暂无学习记录，无法生成计划")
            return None

        learn_text = "\n".join(f"{r}" for r in records)
        user_content = LEARNING_PLAN.format(learn_record=learn_text)

        messages = []
        if extra_system_prompt:
            messages.append({"role": "system", "content": extra_system_prompt})
        messages.append({"role": "user", "content": user_content})

        answer = self.ask_ai(messages)

        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"{date_str}_学习计划.md"
        filepath = os.path.join(self.plan_dir, filename)
        full_content = f"日期：{date_str}\n---\n{answer}"

        if self._save_text(filepath, full_content):
            print("学习计划保存成功！")
        else:
            print("计划保存失败")

        return full_content


# ── 全局单例，方便快速调用 ─────────────────────────────────
tool = LearningTool()
