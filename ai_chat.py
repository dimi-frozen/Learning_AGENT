"""
ai_chat.py — AI 对话主程序

普通对话由 LearningTool.ask_ai() 处理，
工具类请求由 DecisionMaker 自动路由到对应方法。
"""

from prompt import MODE_PROMPTS, MODE
from tools.learning_tool import tool
from decision import maker


def main():
    mode_prompts = MODE_PROMPTS

    while True:
        mode = input(MODE)
        if mode == "exit":
            print("程序已退出")
            break
        if mode not in mode_prompts:
            print("输入错误，请输入 1、2、3 或 exit")
            continue

        system_prompt = mode_prompts[mode]
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        print(f"\n已进入模式{mode}，输入 back 返回模式选择，输入 exit 退出")

        while True:
            q = input("请输入：")
            if q == "exit":
                print("程序已退出")
                exit()
            if q == "back":
                break

            # ── 优先匹配硬编码命令 ────────────────────
            if q.startswith("/learn"):
                parts = q.split(maxsplit=1)
                if len(parts) < 2:
                    print("请输入要保存的内容，例如：/learn 内容")
                    continue
                tool.save_record(parts[1])
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
                tool.generate_progress(extra_system_prompt=system_prompt)
                continue

            if q.startswith("/plan"):
                print("生成中请稍后")
                tool.generate_plan(extra_system_prompt=system_prompt)
                continue

            # ── 自然语言：让决策器判断是否调用工具 ──
            decision = maker.tool_router(q, system_prompt)
            result = maker.execute(decision, system_prompt)

            if result is not None:
                print(result)
                continue

            # ── 普通对话 ──
            messages.append({"role": "user", "content": q})
            answer = tool.ask_ai(messages)
            print(f"\nAI回复：{answer}")
            messages.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()
