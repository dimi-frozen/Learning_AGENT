"""
ai_chat.py — AI 对话主程序

硬编码命令（/learn /progress /plan）直接执行，
自然语言由 fc_router 的 function calling 自动路由到对应工具。
"""

import logging
from prompt import MODE_PROMPTS, MODE
from tools.learning_tool import tool
from fc_router import chat_with_tools
from tools.memory_tool import memory
from config import setup_logging

logger = logging.getLogger(__name__)


def main():
    setup_logging()
    logger.info("程序启动")
    mode_prompts = MODE_PROMPTS

    while True:
        mode = input(MODE)
        if mode == "exit":
            logger.info("用户退出程序")
            print("程序已退出")
            break
        if mode not in mode_prompts:
            print("输入错误，请输入 1、2、3 或 exit")
            continue

        logger.info(f"进入模式{mode}")
        system_prompt = mode_prompts[mode]

        # 加载历史记忆（只有 user/assistant 消息，不含 system prompt）
        history = memory.load()
        if history:
            logger.info(f"加载了 {len(history)} 条历史记忆")
            print(f"已加载 {len(history)} 条历史对话记忆")
        messages = [
            {"role": "system", "content": system_prompt}
        ] + history
        print(f"\n已进入模式{mode}，输入 back 返回模式选择，输入 exit 退出")

        while True:
            q = input("请输入：")
            if q == "exit":
                logger.info("用户强制退出")
                print("程序已退出")
                exit()
            if q == "back":
                logger.info("返回模式选择")
                break

            # ── 优先匹配硬编码命令 ────────────────────
            if q.startswith("/learn"):
                parts = q.split(maxsplit=1)
                if len(parts) < 2:
                    print("请输入要保存的内容，例如：/learn 内容")
                    continue
                tool.save_record(parts[1])
                logger.info(f"保存学习记录：{parts[1]}")
                print("保存成功")
                continue

            if q.startswith("/progress"):
                records = tool.get_records()
                if not records:
                    print("暂无学习记录，无法生成")
                    continue
                print("已累计学习：")
                for r in records:
                    print(f"  - {r}")
                print("将为您生成学习日报")
                logger.info("开始生成学习日报")
                tool.generate_progress(extra_system_prompt=system_prompt)
                continue

            if q.startswith("/plan"):
                print("生成中请稍后")
                logger.info("开始生成学习计划")
                tool.generate_plan(extra_system_prompt=system_prompt)
                continue

            # ── 自然语言：function calling 自动路由 ──
            messages.append({"role": "user", "content": q})
            logger.debug(f"用户输入：{q}")
            answer = chat_with_tools(messages, system_prompt)
            logger.info(f"AI回复完成，长度：{len(answer)}")
            print(f"\nAI回复：{answer}")
            # 保存到记忆（去掉 system prompt，只存 user/assistant 消息）
            memory.save(messages[1:])


if __name__ == "__main__":
    main()
