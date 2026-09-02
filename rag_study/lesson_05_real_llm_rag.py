import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from sentence_transformers import SentenceTransformer

from lesson_02_min_rag import Chunk, build_chunks, build_prompt
from lesson_04_real_embedding_rag import (
    MODEL_DIR,
    MODEL_NAME,
    build_vector_index,
    retrieve_by_embedding,
)
from tools.ai_utils import ask_ai


def ask_llm(prompt: str) -> str:
    """Send the grounded RAG prompt to the generation model."""
    messages = [
        {
            "role": "user",
            "content": prompt,
        }
    ]
    return ask_ai(messages)


def print_retrieved_chunks(
    retrieved_chunks: list[tuple[Chunk, float]],
) -> None:
    print("\n=== 语义检索结果 ===")
    for chunk, score in retrieved_chunks:
        print(
            f"- score={score:.4f} | "
            f"{chunk.source}#{chunk.chunk_id}: {chunk.text}"
        )


def main() -> None:
    query = " ".join(sys.argv[1:]).strip() or "我一年能休息多少天？"

    print("=== 加载本地 Embedding 模型 ===")
    embedding_model = SentenceTransformer(
        MODEL_NAME,
        cache_folder=str(MODEL_DIR),
        local_files_only=True,
    )

    chunks = build_chunks()
    vector_index = build_vector_index(embedding_model, chunks)
    retrieved_chunks = retrieve_by_embedding(
        embedding_model,
        query,
        vector_index,
    )
    prompt = build_prompt(query, retrieved_chunks)

    print("\n=== 用户问题 ===")
    print(query)
    print_retrieved_chunks(retrieved_chunks)

    print("\n=== 传给生成 LLM 的 Prompt ===")
    print(prompt)

    print("\n=== 真实 LLM 回答 ===")
    answer = ask_llm(prompt)
    print(answer)


if __name__ == "__main__":
    main()
