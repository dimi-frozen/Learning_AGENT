import sys
from pathlib import Path

from sentence_transformers import SentenceTransformer

from lesson_02_min_rag import Chunk, build_chunks, build_prompt, fake_llm_answer
from lesson_03_cosine_similarity import cosine_similarity


MODEL_NAME = "BAAI/bge-small-zh-v1.5"
MODEL_DIR = Path(__file__).parent / "models"
QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："


def embed_text(model: SentenceTransformer, text: str) -> list[float]:
    """Turn one piece of text into an embedding vector."""
    vector = model.encode(text)
    return vector.tolist()


def build_vector_index(
    model: SentenceTransformer,
    chunks: list[Chunk],
) -> list[tuple[Chunk, list[float]]]:
    """Calculate and store one vector for every chunk."""
    vector_index = []

    for chunk in chunks:
        text_for_embedding = f"{chunk.title}\n{chunk.text}"
        chunk_vector = embed_text(model, text_for_embedding)
        vector_index.append((chunk, chunk_vector))

    return vector_index


def retrieve_by_embedding(
    model: SentenceTransformer,
    query: str,
    vector_index: list[tuple[Chunk, list[float]]],
    top_k: int = 3,
) -> list[tuple[Chunk, float]]:
    """Retrieve chunks by semantic vector similarity."""
    query_vector = embed_text(model, QUERY_INSTRUCTION + query)
    scored_chunks = []

    for chunk, chunk_vector in vector_index:
        score = cosine_similarity(query_vector, chunk_vector)
        scored_chunks.append((chunk, score))

    return sorted(
        scored_chunks,
        key=lambda item: item[1],
        reverse=True,
    )[:top_k]


def main() -> None:
    query = " ".join(sys.argv[1:]).strip() or "我能歇多久？"

    print("=== 加载本地 Embedding 模型 ===")
    model = SentenceTransformer(
        MODEL_NAME,
        cache_folder=str(MODEL_DIR),
    )

    chunks = build_chunks()
    vector_index = build_vector_index(model, chunks)
    retrieved_chunks = retrieve_by_embedding(model, query, vector_index)
    prompt = build_prompt(query, retrieved_chunks)

    print(f"模型目录：{MODEL_DIR.resolve()}")
    print(f"向量维度：{len(vector_index[0][1])}")

    print("\n=== 用户问题 ===")
    print(query)

    print("\n=== 语义检索结果 ===")
    for chunk, score in retrieved_chunks:
        print(
            f"- score={score:.4f} | "
            f"{chunk.source}#{chunk.chunk_id}: {chunk.text}"
        )

    print("\n=== 传给 LLM 的 Prompt ===")
    print(prompt)

    print("\n=== LLM 回答示意 ===")
    print(fake_llm_answer(retrieved_chunks))


if __name__ == "__main__":
    main()
