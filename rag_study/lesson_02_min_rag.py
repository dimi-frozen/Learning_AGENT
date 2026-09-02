"""
Lesson 02: a tiny RAG system without frameworks.

Run:
    python rag_study/lesson_02_min_rag.py
    python rag_study/lesson_02_min_rag.py "年假怎么计算？"

This lesson focuses on the core RAG pipeline:
1. Split documents into chunks.
2. Retrieve chunks related to the question.
3. Build a prompt that gives those chunks to an LLM.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass


DOCUMENTS = [
    {
        "source": "employee_handbook.md",
        "title": "员工手册",
        "text": (
            "员工入职满一年后，每年享有 5 天年假。"
            "工龄满 10 年后，每年享有 10 天年假。"
            "年假申请需要提前 3 个工作日提交，并由直属主管审批。"
        ),
    },
    {
        "source": "expense_policy.md",
        "title": "报销制度",
        "text": (
            "员工因公产生的交通、住宿和餐饮费用可以申请报销。"
            "单笔超过 500 元的费用需要上传发票和付款凭证。"
            "报销申请应在费用产生后的 30 天内提交。"
        ),
    },
    {
        "source": "remote_work.md",
        "title": "远程办公制度",
        "text": (
            "员工每周最多可以申请 2 天远程办公。"
            "远程办公需要提前一天在系统中提交申请。"
            "涉及客户现场、线下会议或保密资料处理的工作，不建议远程完成。"
        ),
    },
    {
        "source": "onboarding.md",
        "title": "新人入职流程",
        "text": (
            "新员工入职第一天需要完成账号开通、设备领取和入职培训。"
            "试用期一般为 3 个月。"
            "试用期结束前，主管会根据工作表现安排转正评估。"
        ),
    },
]


@dataclass
class Chunk:
    source: str
    title: str
    chunk_id: int
    text: str


def split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[。！？!?])", text)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def chunk_document(document: dict[str, str], max_chars: int = 5) -> list[Chunk]:
    chunks: list[Chunk] = []
    current = ""

    for sentence in split_sentences(document["text"]):
        if current and len(current) + len(sentence) > max_chars:
            chunks.append(
                Chunk(
                    source=document["source"],
                    title=document["title"],
                    chunk_id=len(chunks) + 1,
                    text=current,
                )
            )
            current = sentence
        else:
            current += sentence

    if current:
        chunks.append(
            Chunk(
                source=document["source"],
                title=document["title"],
                chunk_id=len(chunks) + 1,
                text=current,
            )
        )

    return chunks


def build_chunks() -> list[Chunk]:
    chunks: list[Chunk] = []
    for document in DOCUMENTS:
        chunks.extend(chunk_document(document))
    return chunks


def tokenize(text: str) -> set[str]:
    clean_text = re.sub(r"\s+", "", text.lower())
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", clean_text)
    latin_words = re.findall(r"[a-z0-9]+", clean_text)

    # Character bigrams make this simple retriever less brittle for Chinese text.
    bigrams = [
        clean_text[index : index + 2]
        for index in range(len(clean_text) - 1)
        if re.search(r"[\u4e00-\u9fff]", clean_text[index : index + 2])
    ]

    return set(chinese_chars + latin_words + bigrams)


def score_chunk(query: str, chunk: Chunk) -> int:
    query_tokens = tokenize(query)
    chunk_tokens = tokenize(chunk.text + chunk.title)
    return len(query_tokens & chunk_tokens)


def retrieve(query: str, chunks: list[Chunk], top_k: int = 30) -> list[tuple[Chunk, int]]:
    scored_chunks = [
        (chunk, score_chunk(query, chunk))
        for chunk in chunks
    ]
    useful_chunks = [
        (chunk, score)
        for chunk, score in scored_chunks
        if score > 0
    ]
    return sorted(useful_chunks, key=lambda item: item[1], reverse=True)[:top_k]


def build_prompt(query: str, retrieved_chunks: list[tuple[Chunk, int]]) -> str:
    context_lines = []
    for index, (chunk, _score) in enumerate(retrieved_chunks, start=1):
        context_lines.append(
            f"[资料{index}] 来源：{chunk.source} / {chunk.title}\n{chunk.text}"
        )

    context = ("\n\n".join(context_lines) if context_lines else "没有检索到相关资料。")
    return f"""请只根据下面的资料回答用户问题。
如果资料里没有答案，就说“资料中没有找到答案”。
回答后列出你使用的来源。

资料：
{context}

用户问题：
{query}
"""


def fake_llm_answer(retrieved_chunks: list[tuple[Chunk, int]]) -> str:
    if not retrieved_chunks:
        return "资料中没有找到答案。"

    best_chunk = retrieved_chunks[0][0]
    return (
        "模拟回答：\n"
        f"{best_chunk.text}\n\n"
        f"来源：{best_chunk.source} / {best_chunk.title}"
    )


def main() -> None:
    query = " ".join(sys.argv[1:]).strip() or "我能歇多久？"
    chunks = build_chunks()
    retrieved_chunks = retrieve(query, chunks)
    prompt = build_prompt(query, retrieved_chunks)

    print("=== 用户问题 ===")
    print(query)

    print("\n=== 切块结果 ===")
    for chunk in chunks:
        print(f"- {chunk.source}#{chunk.chunk_id}: {chunk.text}")
        
    print("/n===打分结果===")
    for chunk, score in  retrieved_chunks:
        print(f"- {chunk.source}#{chunk.chunk_id}: {score}")

    print("\n=== 检索结果 ===")
    if not retrieved_chunks:
        print("没有找到相关资料。")
    for chunk, score in retrieved_chunks:
        print(f"- score={score} | {chunk.source}#{chunk.chunk_id}: {chunk.text}")

    print("\n=== 传给 LLM 的 Prompt ===")
    print(prompt)

    print("\n=== LLM 回答示意 ===")
    print(fake_llm_answer(retrieved_chunks))


if __name__ == "__main__":
    main()
