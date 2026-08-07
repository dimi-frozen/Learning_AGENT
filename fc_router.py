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
import logging
from tools.ai_utils import ask_ai_with_tools
from pydantic import BaseModel,Field

logger = logging.getLogger(__name__)

# 工具输入参数定义  pydantic
class SaveRecordInput(BaseModel):
    """保存一条学习记录。当用户说学了/学会了/掌握了某个知识点时调用。"""
    model_config = {"title": "save_record"}
    content: str = Field(description="学习内容描述")
    
class GetRecordsInput(BaseModel):
    """查看所有学习记录。当用户想查看学过什么/有哪些记录时调用。"""
    model_config = {"title": "get_records"}
    pass

class GenerateProgressInput(BaseModel):
    """生成学习日报。当用户要求生成日报/学习进度/学习报告时调用。"""
    model_config = {"title": "generate_progress"}
    extra_system_prompt: str = Field(description="额外的系统提示，用于生成日报")

class FileReadInput(BaseModel):
    """读取文件内容。当用户说读取/查看/打开某个文件时调用。"""
    model_config = {"title": "file_read"}
    file_path: str = Field(description="文件的完整路径")

class FileAnalyzeInput(BaseModel):
    """分析文件内容并保存结果。当用户要求分析/检查/审查/评估文件时调用。"""
    model_config = {"title": "file_analyze"}
    
# 自动生成 OpenAI 格式的 tools 列表
def build_tool_schema(model_cls):
    schema = model_cls.model_json_schema()
    return {
        "type": "function",
        "function": {
            "name": schema["title"],
            "description": schema.get("description", ""),
            "parameters": schema,
        }
    }



# ── 工具定义（OpenAI function calling 格式） ──────────────────
TOOLS = [
    build_tool_schema(SaveRecordInput),
    build_tool_schema(GetRecordsInput),
    build_tool_schema(GenerateProgressInput),
    build_tool_schema(FileReadInput),
    build_tool_schema(FileAnalyzeInput),
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
    logger.info("开始生成学习日报")
    result = tool.generate_progress(extra_system_prompt=system_prompt)
    logger.info("学习日报生成完成" if result else "学习日报生成失败")
    return "学习日报已生成并保存！" if result else "生成日报失败"


def _handle_generate_plan(args, system_prompt=None):
    from tools.learning_tool import tool
    records = tool.get_records()
    if not records:
        return "暂无学习记录，无法生成计划"
    print("正在生成学习计划…")
    logger.info("开始生成学习计划")
    result = tool.generate_plan(extra_system_prompt=system_prompt)
    logger.info("学习计划生成完成" if result else "学习计划生成失败")
    return "学习计划已生成并保存！" if result else "生成计划失败"


def _handle_file_read(args, system_prompt=None):
    from tools.file_tool import file_tool
    file_path = args.get("file_path", "")
    if not file_path:
        return "请提供文件路径"
    logger.info(f"读取文件：{file_path}")
    print(f"正在读取文件：{file_path}")
    return file_tool.read(file_path)


def _handle_file_analyze(args, system_prompt=None):
    from tools.file_tool import file_tool
    file_path = args.get("file_path", "")
    instruction = args.get("instruction", "")
    if not file_path:
        return "请提供文件路径"
    logger.info(f"分析文件：{file_path}，指令：{instruction}")
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
    while True:
        # 第一次调用：让模型决定是否使用工具
        try:
            response = ask_ai_with_tools(messages, tools=TOOLS)
        except Exception as e:
            logger.error(f"API调用异常：{e}")
            return f"AI服务暂时不可用，请稍后重试。（错误：{e}）"

        # 没有工具调用 → 普通回复
        if not response.get("tool_calls"):
            content = response.get("content", "")
            messages.append({"role": "assistant", "content": content})
            logger.debug("AI返回普通回复，无工具调用")
            return content

        # ── 有工具调用 → 执行并回传结果 ──
        logger.info(f"AI请求调用 {len(response['tool_calls'])} 个工具")
        messages.append(response)  # 把 assistant 的 tool_calls 消息加入历史

        for tool_call in response["tool_calls"]:
            func_name = tool_call["function"]["name"]
            
            # 解析工具参数
            try:
                func_args = json.loads(tool_call["function"]["arguments"])
            except json.JSONDecodeError as e:
                logger.error(f"工具参数解析失败：{func_name}，错误：{e}")
                func_args = {}
                result = f"工具参数格式错误，无法执行：{func_name}"
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result,
                })
                continue
            
            logger.info(f"执行工具：{func_name}，参数：{func_args}")

            handler = TOOL_HANDLERS.get(func_name)
            if handler:
                try:
                    result = handler(func_args, system_prompt)
                    logger.debug(f"工具 {func_name} 执行完成，结果长度：{len(result)}")
                except Exception as e:
                    logger.error(f"工具执行异常：{func_name}，错误：{e}")
                    result = f"工具执行失败：{e}"
            else:
                result = f"未知工具：{func_name}"
                logger.warning(f"未知工具被调用：{func_name}")

            # 把工具执行结果加入 messages（role="tool"）
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": result,
            })
