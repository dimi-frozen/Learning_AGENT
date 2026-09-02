from math import sqrt


def dot_product(vector_a: list[float], vector_b: list[float]) -> float:
    """Calculate the dot product of two vectors."""
    if len(vector_a) != len(vector_b):
        raise ValueError("两个向量的维度必须相同。")

    return sum(a * b for a, b in zip(vector_a, vector_b))


def vector_length(vector: list[float]) -> float:
    """Calculate the length of a vector."""
    return sqrt(sum(value * value for value in vector))


def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    """Compare two vectors by their direction."""
    length_product = vector_length(vector_a) * vector_length(vector_b)

    if length_product == 0:
        return 0.0

    return dot_product(vector_a, vector_b) / length_product


def main() -> None:
    query_vector = [1.0, 0.0]

    chunk_vectors = [
        ("chunk_a", [10.0, 0.0]),
        ("chunk_b", [1.0, 1.0]),
        ("chunk_c", [0.0, 5.0]),
    ]

    scored_chunks = []
    for chunk_name, chunk_vector in chunk_vectors:
        score = cosine_similarity(query_vector, chunk_vector)
        scored_chunks.append((chunk_name, score))

    scored_chunks.sort(key = lambda item: item[1],reverse=True)
    print("=== 按余弦相似度排序 ===")
    for chunk_name, score in scored_chunks:
        print(f"{chunk_name}: {score:.4f}")


if __name__ == "__main__":
    main()
