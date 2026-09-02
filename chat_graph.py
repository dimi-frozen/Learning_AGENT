"""
chat_graph.py — 第一步：用「图的思维」重写 chat_with_tools

不安装 LangGraph，手写一个极简版「图引擎」。
目标：让你看到你现有的 chat_with_tools 其实就是一个藏在循环里的状态机。

结构（对照你整理的蓝图 ①~⑤）：
    AgentState —— 公文包（节点间共享的数据）
    llm_node   —— 调 API，只负责「思考」
    tool_node  —— 执行工具，只负责「动手」
    router     —— 条件边：判断下一步去哪
    run_graph  —— 极简版图引擎：负责循环、合并状态、走边
"""

import json
import logging
import sys
from typing import Callable, TypedDict

from fc_router import TOOLS, TOOL_HANDLERS
from tools.ai_utils import ask_ai_with_tools_stream

logger = logging.getLogger(__name__)

# 工具调用轮数上限（相当于 LangGraph 的 recursion_limit）
MAX_ROUNDS = 5


# ── ① State：所有节点共享的公文包 ──────────────────────────
class AgentState(TypedDict):
    """蓝图里的 AgentState。这里没有 add_messages reducer，
    合并逻辑由 run_graph 里的 _merge() 手动完成。"""
    messages: list          # 对话消息列表
    system_prompt: str      # 传给工具的参数
    on_content: Callable    # 流式输出回调


def new_state(messages: list, system_prompt: str, on_content: Callable) -> AgentState:
    """初始化公文包"""
    return {
        "messages": messages,
        "system_prompt": system_prompt,
        "on_content": on_content,
    }


# ── ② llm_node：只「思考」，不决定 ──────────────────────────
def llm_node(state: AgentState) -> dict:
    """调一次 API，把模型回复放进 state。

    对比 fc_router.py 里 chat_with_tools 的第 186 行：
    - 原来：在循环体里调用，还要自己判断「有没有 tool_calls」
    - 现在：只调用，把「下一步去哪」的决定权交给 router
    """
    try:
        response = ask_ai_with_tools_stream(
            state["messages"], tools=TOOLS, on_content=state["on_content"]
        )
    except Exception as e:
        logger.error(f"API调用异常：{e}")
        # 关键转变：错误不再是「提前 return 字符串」，而是变成一条普通消息。
        # 这样所有节点返回的结构永远一致（{"messages": [...]}），router 照常判断。
        response = {
            "role": "assistant",
            "content": f"AI服务暂时不可用，请稍后重试。（错误：{e}）",
        }
    return {"messages": [response]}


# ── ③ tool_node：只「动手」，不决定 ──────────────────────────
def tool_node(state: AgentState) -> dict:
    """执行最后一条消息里的所有 tool_calls，返回 tool 结果消息。

    TODO（你的任务）：把 fc_router.py 里 chat_with_tools 的第 204~240 行
    （`for tool_call in response["tool_calls"]:` 那一整段）搬到这里。
    需要改三处：
      1. 循环对象从 `response["tool_calls"]` 改成 `state["messages"][-1]["tool_calls"]`
      2. 不要原地 `messages.append(...)`，改成收集到一个 new_messages 列表
      3. handler 传参里的 `system_prompt` 改成 `state["system_prompt"]`
    最后 `return {"messages": new_messages}`
    """
    new_messages = []
    for tool_call in state["messages"][-1]["tool_calls"]:
                    func_name = tool_call["function"]["name"]
                    
                    # 解析工具参数
                    try:
                        func_args = json.loads(tool_call["function"]["arguments"])
                    except json.JSONDecodeError as e:
                        logger.error(f"工具参数解析失败：{func_name}，错误：{e}")
                        func_args = {}
                        result = f"工具参数格式错误，无法执行：{func_name}"
                        new_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": result,
                        })
                        continue
                    
                    logger.info(f"执行工具：{func_name}，参数：{func_args}")
        
                    handler = TOOL_HANDLERS.get(func_name)
                    if handler:
                        try:
                            result = handler(func_args, state["system_prompt"])
                            logger.debug(f"工具 {func_name} 执行完成，结果长度：{len(result)}")
                        except Exception as e:
                            logger.error(f"工具执行异常：{func_name}，错误：{e}")
                            result = f"工具执行失败：{e}"
                    else:
                        result = f"未知工具：{func_name}"
                        logger.warning(f"未知工具被调用：{func_name}")
        
                    # 把工具执行结果加入 messages（role="tool"）
                    new_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": result,
                    })
    return {"messages": new_messages}

# ── ④ 条件边路由器：if/else 搬到这里 ───────────────────────
def router(state: AgentState) -> str:
    """读状态，返回下一步节点名。
    这是整个图里唯一允许做「流程判断」的地方。"""
    if state["messages"][-1].get("tool_calls"):
        return "tool"
    return "end"


# ── ⑤ 极简版图引擎：模拟 LangGraph 的 compile().invoke() ──
def _merge(state: AgentState, update: dict) -> None:
    """手动实现 add_messages：把节点返回的新消息追加进 state"""
    state["messages"].extend(update["messages"])


def run_graph(state: AgentState) -> AgentState:
    """从入口节点出发，循环走边，直到 END。

    对应蓝图的这几步：
        graph.set_entry_point("llm")
        graph.add_conditional_edges("llm", router, {"tool": "tool", "end": END})
        graph.add_edge("tool", "llm")
    外加递归上限（对应你原来的 MAX_TOOL_ROUNDS）。
    """
    current = "llm"          # set_entry_point
    rounds = 0               # 记录节点访问次数（LangGraph 的 recursion 计数）
    while current != "end":
        rounds += 1
        if rounds > MAX_ROUNDS:
            logger.warning(f"节点访问次数达到上限（{MAX_ROUNDS}），已停止")
            break

        if current == "llm":
            _merge(state, llm_node(state))   # ① 先合并
            current = router(state)          # ② 再走条件边
        elif current == "tool":
            _merge(state, tool_node(state))
            current = "llm"                  # ③ 普通边，形成循环
    return state


# ── 演示入口 ───────────────────────────────────────────────
if __name__ == "__main__":
    # Windows 控制台默认 GBK，输出不了 emoji（📝）会抛 UnicodeEncodeError。
    # 切成 UTF-8，编码不了的字符用 ? 代替，不再崩。
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    def demo_on_content(text: str) -> None:
        sys.stdout.write(text)
        sys.stdout.flush()

    s = new_state(
        messages=[{"role": "system", "content": "你是学习助手。"}],
        system_prompt="你是学习助手。",
        on_content=demo_on_content,
    )
    s["messages"].append({"role": "user", "content": "我学了字典的遍历"})
    print("\n[图开始运行]")
    final = run_graph(s)
    print(f"\n[图运行结束] 最后回复：{final['messages'][-1]['content']}")
