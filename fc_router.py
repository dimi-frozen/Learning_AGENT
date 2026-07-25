"""
fc_router.py — Function Calling 工具路由

使用 OpenAI 兼容的 function calling 格式，
让大模型自动判断是否需要调用工具、调用哪个工具。

流程：
1. 用户消息 + 工具定义 → 发给 API
2. API 返回 tool_calls → 执行工具 → 结果放回 messages → 再次调 API 拿最终回复
3. API 返回普通 content → 直接输出
"""

import json
from tools.ai_utils import ask_ai_with_tools


# ── 工具定义（OpenAI function calling 格式） ──────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_record",
            "description": "保存一条学习记录。当用户说学了/学会了/掌握了某个知识点时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "学习的内容描述"
                    }
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_records",
            "description": "查看所有学习记录。当用户想查看学过什么/有哪些记录时调用。",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_progress",
            "description": "生成学习日报，分析学习进度并给出建议。当用户要求生成日报/学习进度/学习报告时调用。",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_plan",
            "description": "生成学习计划，规划未来学习路线。当用户要求制定计划/规划学习时调用。",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "file_read",
            "description": "读取文件内容。当用户说读取/查看/打开某个文件时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文件的完整路径"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "file_analyze",
            "description": "分析文件内容并保存结果。当用户要求分析/检查/审查/评估文件时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文件的完整路径"
                    },
                    "instruction": {
                        "type": "string",
                        "description": "分析要求，如'检查语法错误'、'优化代码结构'"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
]


# ── 工具执行函数 ──────────────────────────────────────────────

def _handle_save_record(args, system_prompt=None):
    from tools.learning_tool import tool
    content = args.get("content", "")
    if not content:
        return "请说明你学了什么，例如：我学了字典的遍历"
    tool.save_record(content)
    return f"已保存学习记录：{content}"


def _handle_get_records(args, system_prompt=None):
    from tools.learning_tool import tool
    records = tool.get_records()
    if not records:
        return "暂无学习记录"
    lines = [f"  - {r['datetime']}  {r['content']}" for r in records]
    return "学习记录：\n" + "\n".join(lines)


def _handle_generate_progress(args, system_prompt=None):
    from tools.learning_tool import tool
    records = tool.get_records()
    if not records:
        return "暂无学习记录，无法生成日报"
    print("已累计学习：")
    for r in records:
        print(f"  - {r['datetime']}  {r['content']}")
    print("正在生成学习日报…")
    result = tool.generate_progress(extra_system_prompt=system_prompt)
    return "学习日报已生成并保存！" if result else "生成日报失败"


def _handle_generate_plan(args, system_prompt=None):
    from tools.learning_tool import tool
    records = tool.get_records()
    if not records:
        return "暂无学习记录，无法生成计划"
    print("正在生成学习计划…")
    result = tool.generate_plan(extra_system_prompt=system_prompt)
    return "学习计划已生成并保存！" if result else "生成计划失败"


def _handle_file_read(args, system_prompt=None):
    from tools.file_tool import file_tool
    file_path = args.get("file_path", "")
    if not file_path:
        return "请提供文件路径"
    print(f"正在读取文件：{file_path}")
    return file_tool.read(file_path)


def _handle_file_analyze(args, system_prompt=None):
    from tools.file_tool import file_tool
    file_path = args.get("file_path", "")
    instruction = args.get("instruction", "")
    if not file_path:
        return "请提供文件路径"
    return file_tool.analyze(file_path, instruction)


# ── 工具名 → 执行函数 映射 ────────────────────────────────────
TOOL_HANDLERS = {
    "save_record": _handle_save_record,
    "get_records": _handle_get_records,
    "generate_progress": _handle_generate_progress,
    "generate_plan": _handle_generate_plan,
    "file_read": _handle_file_read,
    "file_analyze": _handle_file_analyze,
}


# ── 核心：带 function calling 的对话 ─────────────────────────

def chat_with_tools(messages, system_prompt=None):
    """带 function calling 的对话

    1. 发送 messages + TOOLS 给 API
    2. 如果 API 返回 tool_calls → 执行工具 → 结果放回 messages → 再次调 API
    3. 如果 API 返回普通 content → 直接返回

    注意：此函数会修改传入的 messages 列表（追加工具交互记录）

    Args:
        messages: 对话消息列表（会被就地修改）
        system_prompt: 当前模式的角色提示

    Returns:
        str: AI 的最终回复文本
    """
    # 第一次调用：让模型决定是否使用工具
    response = ask_ai_with_tools(messages, tools=TOOLS)

    # 没有工具调用 → 普通回复
    if not response.get("tool_calls"):
        content = response.get("content", "")
        messages.append({"role": "assistant", "content": content})
        return content

    # ── 有工具调用 → 执行并回传结果 ──
    messages.append(response)  # 把 assistant 的 tool_calls 消息加入历史

    for tool_call in response["tool_calls"]:
        func_name = tool_call["function"]["name"]
        func_args = json.loads(tool_call["function"]["arguments"])

        handler = TOOL_HANDLERS.get(func_name)
        if handler:
            result = handler(func_args, system_prompt)
        else:
            result = f"未知工具：{func_name}"

        # 把工具执行结果加入 messages（role="tool"）
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": result,
        })

    # 第二次调用：让模型基于工具结果生成最终回复
    final_response = ask_ai_with_tools(messages)
    content = final_response.get("content", "")
    messages.append({"role": "assistant", "content": content})
    return content
