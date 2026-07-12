import requests
import os
from file_utils import write, read ,save_text_file
from datetime import datetime
from config import API_KEY, BASE_URL, MODEL_NAME,LEARN_RECORD_FILE,REPORT_DIR
from prompt import MODE_PROMPTS,MODE,DAILY_PATH
#requests 是 Python 最常用的第三方 HTTP 库，专门用来向服务器发送 GET/POST 请求。
#调用大模型 API 的本质，就是向对方的服务器发送一段 JSON 数据，然后接收返回的 AI 回答，全靠这个库实现。

def ask_ai(messages):
    url = BASE_URL#接口地址

    #请求头
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    #请求体
    data = {
        "model": MODEL_NAME,
        "messages": messages
    }

    response = requests.post(url, json=data, headers=headers)
    return response.json()["choices"][0]["message"]["content"]

mode_prompts = MODE_PROMPTS
while True:
    mode = input(MODE)
    system_prompt = mode_prompts.get(mode)
    if mode == "exit":
        print("程序已退出")
        break
    if mode not in mode_prompts:
        print("输入错误，请输入 1、2、3 或 exit")
        continue
    messages = [
        {"role" : "system",
        "content" : mode_prompts[mode] }
    ]
    print(f"\n已进入模式{mode}，输入 back 返回模式选择，输入 exit 退出")#模式选择完成，先给chat传入模式部分

    while True:
        q = input("请输入：")
        if q == "exit":
            print("程序已退出")
            exit()
        if q == "back":
            break

        #/learn 指令：保存已学内容
        if q.startswith("/learn"):
            write(LEARN_RECORD_FILE,q[6:])
            print("保存成功")
            continue

        #progress指令：输出已学内容并且给出建议
        if q.startswith("/progress"):
            print("已累计学习：")
            print("\n")
            learn_data = read(LEARN_RECORD_FILE)#读取
            if not learn_data:
                print("暂无学习记录，无法生成")
                continue

            learn_memory = "\n".join(
                f"-{item}" for item in learn_data
            )#拼接输出内容
            print(learn_memory)
            user_content = f"{learn_memory},{DAILY_PATH}"#将输出内容喂给ai
            messages.append({"role" : "user", "content" : user_content})
            answer = ask_ai(messages)
            messages.append({"role" : "assistant","content" : answer})#获取回复并且将回复加入messages列表中
            #输出学习日报
            print("将为您生成学习日报")
            #确定文件名
            date_str = datetime.now().strftime("%Y%m%d")#用日期来拼接文件名
            report_filename = f"{date_str}_学习日报.md"
            report_path = os.path.join(REPORT_DIR,report_filename)
            daily_report = "日期：" + date_str + "\n" + "---" + "\n" + answer
            if save_text_file(report_path,daily_report):
                print("学习日报保存成功！")
            else:
                print("保存失败")
            continue

        messages.append({"role" : "user","content" : q})#把用户的问题加到messages列表里
        answer = ask_ai(messages)#上述问题的回答
        print(f"\nAI回复：{answer}")
        messages.append({"role" : "assistant","content" : answer})#一次循环里再加上回答的文本记忆