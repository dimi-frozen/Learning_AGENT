import json
import os
#文件读写的工具函数
def write (file_path,messages):
    if os.path.exists(file_path):
      with open(file_path,"r",encoding = "utf-8") as f:
          data = json.load(f)#读取文件中保存的json
    else:
      data = []#初始化
    data.append(messages)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)#写入


def read (file_path):
    with open(file_path,"r",encoding = "utf-8") as f:
        data = json.load(f)#读取json
    return data

def save_text_file (file_path,content):
   """
    覆盖写入纯文本内容到文件
    文件不存在自动创建，已存在则覆盖原有内容
    适合保存学习日报、导出对话记录等单份完整文本
    :param file_path: 保存的文件路径，如 "20260709_学习日报.md"
    :param content: 要写入的完整文本内容
    :return: 成功返回 True，失败返回 False
    """
   try:
    with open(file_path,"w",encoding = "utf-8") as f:
        f.write(content)
        return True,None
   except Exception as e:
      return False,str(e)
      