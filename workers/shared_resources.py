from functools import lru_cache

from llama_index.embeddings.huggingface import HuggingFaceEmbedding


EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embedding_model(model_path: str) -> HuggingFaceEmbedding:
    """Load the embedding model once per Python process."""
    return HuggingFaceEmbedding(
        model_name=model_path,
        normalize=True,
    )
