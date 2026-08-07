"""
file_tool.py — 文件分析工具

提供三个操作：
- read(path)      读取文本文件内容
- write(content)  把分析结果写入文件
- analyze(path)   读文件 + AI 分析 + 写结果，一步完成
"""

import logging
import os
from datetime import datetime
from config import ANALYSIS_DIR
from tools.ai_utils import ask_ai

logger = logging.getLogger(__name__)


ANALYSIS_PROMPT = """以下是一个文件的内容：

```
{file_content}
```

用户的要求：{instruction}
请分析这个文件。指出其中的优点、问题或改进建议。"""


class FileTool:
    """文件分析工具箱"""

    # 支持分析的文本文件扩展名
    SUPPORTED_EXT = {
        ".py", ".java", ".js", ".ts", ".html", ".css",
        ".md", ".txt", ".json", ".csv", ".log",
        ".yaml", ".yml", ".toml", ".ini", ".xml",
        ".sql", ".sh", ".bat", ".cfg", ".conf",
    }

    def __init__(self):
        self.analysis_dir = ANALYSIS_DIR
        os.makedirs(self.analysis_dir, exist_ok=True)

    # ── 公开接口 ─────────────────────────────────────────

    def read(self, file_path):
        """读取文件内容

        Args:
            file_path: 文件路径

        Returns:
            str: 文件内容，读取失败返回错误提示
        """
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在：{file_path}")
            return f"文件不存在：{file_path}"

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.SUPPORTED_EXT:
            logger.warning(f"不支持的文件类型：{ext}")
            return f"不支持的文件类型：{ext}，支持的扩展名：{', '.join(sorted(self.SUPPORTED_EXT))}"

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            logger.info(f"文件读取成功：{file_path}，大小：{len(content)} 字符")
            return content
        except Exception as e:
            logger.error(f"读取文件失败：{file_path}，错误：{e}")
            return f"读取文件失败：{e}"

    def write(self, content, filename=None):
        """将内容写入分析结果文件

        Args:
            content: 要写入的文本内容
            filename: 可选的文件名，不传则自动生成

        Returns:
            str: 保存成功的文件路径，失败返回错误提示
        """
        if not filename:
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{date_str}_分析报告.md"

        file_path = os.path.join(self.analysis_dir, filename)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"分析报告保存成功：{file_path}")
            return file_path
        except Exception as e:
            logger.error(f"写入文件失败：{file_path}，错误：{e}")
            return f"写入文件失败：{e}"

    def analyze(self, file_path, instruction=None):
        """读取文件 → AI 分析 → 保存结果

        Args:
            file_path: 文件路径
            instruction: 分析指令（如"检查代码错误"）

        Returns:
            str: 分析结果文案
        """
        # 1. 读文件
        content = self.read(file_path)
        if content.startswith("文件不存在") or content.startswith("不支持") or content.startswith("读取文件失败"):
            return content

        # 2. AI 分析
        instruction = instruction or "分析这个文件"
        prompt = ANALYSIS_PROMPT.format(file_content=content, instruction=instruction)

        messages = [
            {"role": "user", "content": prompt}
        ]
        logger.info(f"开始分析文件：{file_path}")
        print("正在分析文件…")
        try:
            analysis = ask_ai(messages)
        except Exception as e:
            logger.error(f"AI分析失败：{e}")
            return f"分析失败：{e}"

        # 3. 保存结果
        date_str = datetime.now().strftime("%Y%m%d")
        base_name = os.path.basename(file_path)
        result_filename = f"{date_str}_{base_name}_分析报告.md"
        result_path = self.write(analysis, result_filename)

        if os.path.exists(result_path):
            logger.info(f"文件分析完成：{file_path}")
            return f"分析完成，结果已保存到：{result_path}\n\n{analysis}"
        logger.warning(f"文件分析完成但保存失败：{file_path}")
        return f"分析完成，但保存失败。\n\n{analysis}"


# 全局单例
file_tool = FileTool()
