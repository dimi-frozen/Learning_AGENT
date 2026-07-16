"""
decision.py — 自动工具路由决策

职责：
1. tool_router()：让 AI 判断用户意图，返回结构化决策
2. execute()：根据决策调用对应的 LearningTool 方法
"""

import json
import re
from config import API_KEY, BASE_URL, MODEL_NAME
from prompt import DECISION_PROMPT
import requests


class DecisionMaker:
    """工具决策器：判断用户意图并路由到对应工具"""

    def tool_router(self, question, system_prompt=None):
        """让 AI 判断用户想调用哪个工具

        Args:
            question: 用户输入文本
            system_prompt: 当前模式的角色提示（可选，帮助 AI 理解上下文）

        Returns:
            dict: {"tool": "工具名", "params": {…}}
        """
        prompt = DECISION_PROMPT.format(question=question)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
        }

        resp = requests.post(BASE_URL, json=payload, headers=headers)
        content = resp.json()["choices"][0]["message"]["content"]

        # 从 AI 返回文本中提取 JSON
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # 解析失败时的安全兜底 → 走普通对话
        return {"tool": "chat", "params": {}}

    def execute(self, decision, system_prompt=None):
        """执行决策，调用对应的 LearningTool 方法

        Args:
            decision: tool_router 返回的决策 dict
            system_prompt: 当前模式的角色提示

        Returns:
            str | None: 执行结果文案，None 表示走普通对话
        """
        from tools.learning_tool import tool

        tool_name = decision.get("tool", "chat")
        params = decision.get("params", {})

        if tool_name == "save_record":
            return self._do_save(tool, params)
        if tool_name == "get_records":
            return self._do_get_records(tool)
        if tool_name == "generate_progress":
            return self._do_progress(tool, system_prompt)
        if tool_name == "generate_plan":
            return self._do_plan(tool, system_prompt)
        # chat / 未知 → 普通对话
        return None

    # ── 各工具的具体执行 ─────────────────────────────

    def _do_save(self, tool, params):
        content = params.get("content", "")
        if not content:
            return "请说明你学了什么，例如：我学了字典的遍历"
        tool.save_record(content)
        return f"已保存学习记录：{content}"

    def _do_get_records(self, tool):
        records = tool.get_records()
        if not records:
            return "暂无学习记录"
        lines = [f"  - {r['datetime']}  {r['content']}" for r in records]
        return "学习记录：\n" + "\n".join(lines)

    def _do_progress(self, tool, system_prompt):
        records = tool.get_records()
        if not records:
            return "暂无学习记录，无法生成日报"
        print("已累计学习：")
        for r in records:
            print(f"  - {r['datetime']}  {r['content']}")
        print("正在生成学习日报…")
        result = tool.generate_progress(extra_system_prompt=system_prompt)
        return "学习日报已生成并保存！" if result else "生成日报失败"

    def _do_plan(self, tool, system_prompt):
        records = tool.get_records()
        if not records:
            return "暂无学习记录，无法生成计划"
        print("正在生成学习计划…")
        result = tool.generate_plan(extra_system_prompt=system_prompt)
        return "学习计划已生成并保存！" if result else "生成计划失败"


# 全局单例
maker = DecisionMaker()
