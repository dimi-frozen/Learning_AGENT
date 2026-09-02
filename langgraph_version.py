"""
langgraph_version.py — 第二步：用真 LangGraph 实现蓝图

和 chat_graph.py 对比，删掉/换掉的东西：
    _merge        → 被 Annotated[list, add_messages] 取代（框架自动合并）
    run_graph     → 被 graph.compile().invoke() 取代（框架自动跑边）
    MAX_ROUNDS    → 被 recursion_limit 取代（invoke 的 config 参数）

节点本身变化很小，两处关键：
    llm_node  发 API 前要把消息对象转回 OpenAI dict（convert_to_openai_messages）
    tool_node 用属性访问 tool_calls，参数已解析不用 json.loads
"""

import logging
import sys
from typing import Annotated, TypedDict
from langgraph.checkpoint.memory import InMemorySaver

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    ToolMessage,
    convert_to_openai_messages,
)
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from fc_router import TOOLS, TOOL_HANDLERS
from tools.ai_utils import ask_ai_with_tools

logger = logging.getLogger(__name__)

checkpointer = InMemorySaver()
# ── ① State：公文包（messages 加上了 reducer，合并交给框架）──
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]   # ← 你手写的 _merge 被它接管
    system_prompt: str


# ── ② llm_node：只「思考」，不决定 ──────────────────────────
def llm_node(state: AgentState) -> dict:
    # state["messages"] 现在是 LangChain 消息对象，转回 OpenAI dict 再发 API
    openai_messages = convert_to_openai_messages(state["messages"])
    try:
        response = ask_ai_with_tools(openai_messages, tools=TOOLS)
    except Exception as e:
        logger.error(f"API调用异常：{e}")
        response = {
            "role": "assistant",
            "content": f"AI服务暂时不可用，请稍后重试。（错误：{e}）",
        }
    # 返回 OpenAI dict 也没问题——add_messages 会自动转成 AIMessage
    return {"messages": [response]}


# ── ③ tool_node：只「动手」，不决定 ──────────────────────────
def tool_node(state: AgentState) -> dict:
    last = state["messages"][-1]   # 一定是 AIMessage（带 tool_calls）
    new_messages = []
    for tool_call in last.tool_calls:
        func_name = tool_call["name"]   # 原版是 function.name
        func_args = tool_call["args"]   # 已解析成 dict，不用 json.loads 了！
        logger.info(f"执行工具：{func_name}，参数：{func_args}")

        handler = TOOL_HANDLERS.get(func_name)
        if handler:
            try:
                result = handler(func_args, state["system_prompt"])
            except Exception as e:
                logger.error(f"工具执行异常：{func_name}，错误：{e}")
                result = f"工具执行失败：{e}"
        else:
            result = f"未知工具：{func_name}"
            logger.warning(f"未知工具被调用：{func_name}")

        new_messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
    return {"messages": new_messages}


# ── ④ 条件边路由器：if/else 搬到这里 ───────────────────────
def router(state: AgentState) -> str:
    if state["messages"][-1].tool_calls:   # 属性访问（AIMessage.tool_calls）
        return "tool"
    return "end"


# ── ⑤ 组装成图（蓝图原样）──────────────────────────────────
graph = StateGraph(AgentState)
graph.add_node("llm", llm_node)
graph.add_node("tool", tool_node)
graph.add_edge(START, "llm")                              # set_entry_point("llm")
graph.add_conditional_edges("llm", router, {"tool": "tool", "end": END})
graph.add_edge("tool", "llm")                             # 循环边，形成 loop
app = graph.compile(checkpointer=checkpointer)                                     # 编译，得到可运行图
 

# ── 演示：像没用框架时那样循环 ───────────────────────────
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    # stdin 也要切成 UTF-8：否则管道/重定向输入的中文会按 GBK 解码变成乱码，
    # 发到 API 直接 400。终端里手动输入时同样保证一致。
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")

    config = {"configurable": {"thread_id": "学习001"},
              "recursion_limit": 10}

    # 先给这个会话埋好初始状态（system 提示 + 工具要用的 system_prompt）。
    # 对应旧版 chat_with_tools 里的 messages = [system] + history 那一步。
    # 用 update_state 只改状态不跑图，省掉一次没意义的 API 调用。
    app.update_state(config, {
        "messages": [SystemMessage(content="你是学习助手。")],
        "system_prompt": "你是学习助手。",
    })

    print("[对话开始，输入 exit 退出]\n")
    while True:
        q = input("你：").strip()
        if q in ("exit", "退出"):
            print("再见！")
            break

        # 一次 invoke = 一次完整回答：
        #   内部工具循环（llm→tool→llm）由图的边自己跑，
        #   对话历史由 checkpointer 记住，这里只需要发新消息。
        final = app.invoke({"messages": [HumanMessage(content=q)]}, config)
        print(f"AI：{final['messages'][-1].content}\n")
