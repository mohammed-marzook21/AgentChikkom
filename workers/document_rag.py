from pathlib import Path
import os

from dotenv import load_dotenv
from workers.anthropic_compat import AnthropicNoTemperature

from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

DOCUMENTS_DIR = BASE_DIR / "data" / "documents"
INDEX_DIR = BASE_DIR / "data" / "vector_index"


# ---------------------------------------------------------
# Embedding configuration
# ---------------------------------------------------------
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

LLAMA_INDEX_CACHE = (
    Path.home()
    / "AppData"
    / "Local"
    / "llama_index"
    / "llama_index"
    / "Cache"
)

MODEL_CACHE_DIR = (
    LLAMA_INDEX_CACHE
    / "models--sentence-transformers--all-MiniLM-L6-v2"
)

SNAPSHOTS_DIR = MODEL_CACHE_DIR / "snapshots"


def _resolve_local_embedding_model() -> Path:
    """
    Resolve the locally cached MiniLM snapshot.

    The project intentionally uses the existing local model so startup
    does not depend on external Hugging Face network access.
    """
    if not SNAPSHOTS_DIR.exists():
        raise FileNotFoundError(
            "Local all-MiniLM-L6-v2 model cache was not found at "
            f"{SNAPSHOTS_DIR}"
        )

    snapshots = [
        path
        for path in SNAPSHOTS_DIR.iterdir()
        if path.is_dir()
    ]

    if not snapshots:
        raise FileNotFoundError(
            "No cached all-MiniLM-L6-v2 snapshot was found."
        )

    return snapshots[0]


LOCAL_EMBED_MODEL = _resolve_local_embedding_model()

embed_model = HuggingFaceEmbedding(
    model_name=str(LOCAL_EMBED_MODEL),
)

Settings.embed_model = embed_model
# ---------------------------------------------------------
# LLM configuration
# ---------------------------------------------------------

load_dotenv()

if not os.getenv("ANTHROPIC_API_KEY"):
    raise RuntimeError(
        "ANTHROPIC_API_KEY is not configured in the .env file."
    )

llm = AnthropicNoTemperature(
    model="claude-sonnet-4-5"
)
Settings.llm = llm


# ---------------------------------------------------------
# Build vector index
# ---------------------------------------------------------

def build_index() -> VectorStoreIndex:
    """
    Read telecom policy documents, split them into chunks,
    create embeddings and persist the VectorStoreIndex.
    """

    if not DOCUMENTS_DIR.exists():
        raise FileNotFoundError(
            f"Documents directory not found: {DOCUMENTS_DIR}"
        )

    txt_files = list(DOCUMENTS_DIR.glob("*.txt"))

    if not txt_files:
        raise FileNotFoundError(
            f"No .txt policy documents found in {DOCUMENTS_DIR}"
        )

    print(f"Found {len(txt_files)} policy documents.")

    documents = SimpleDirectoryReader(
        input_dir=str(DOCUMENTS_DIR),
        required_exts=[".txt"],
    ).load_data()

    print(f"Loaded {len(documents)} documents.")

    splitter = SentenceSplitter(
        chunk_size=512,
        chunk_overlap=50,
    )

    nodes = splitter.get_nodes_from_documents(documents)

    print(f"Created {len(nodes)} text chunks.")

    index = VectorStoreIndex(
        nodes,
        embed_model=embed_model,
    )

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    index.storage_context.persist(
        persist_dir=str(INDEX_DIR)
    )

    print(f"Vector index persisted to: {INDEX_DIR}")

    return index


# ---------------------------------------------------------
# Load existing vector index
# ---------------------------------------------------------

def load_index() -> VectorStoreIndex:
    """
    Load an already-created vector index from disk.
    """

    if not INDEX_DIR.exists():
        raise FileNotFoundError(
            "Vector index does not exist. Run this file first "
            "to build the index."
        )

    storage_context = StorageContext.from_defaults(
        persist_dir=str(INDEX_DIR)
    )

    return load_index_from_storage(
        storage_context,
        embed_model=embed_model,
    )


# ---------------------------------------------------------
# Retrieve relevant policy chunks
# ---------------------------------------------------------

def retrieve_policy(question: str, top_k: int = 3) -> str:
    """
    Retrieve the most relevant policy text for a user question.

    This function performs retrieval only and does not require
    an external LLM.
    """

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    if INDEX_DIR.exists():
        index = load_index()
    else:
        index = build_index()

    retriever = index.as_retriever(
        similarity_top_k=top_k
    )

    nodes = retriever.retrieve(question)

    if not nodes:
        return "No relevant policy information was found."

    results = []

    for position, node in enumerate(nodes, start=1):
        file_name = node.metadata.get(
            "file_name",
            "Unknown document"
        )

        score = node.score

        results.append(
            f"\n--- Result {position} ---\n"
            f"Source: {file_name}\n"
            f"Similarity score: "
            f"{score:.4f}\n"
            f"{node.get_content()}"
        )

    return "\n".join(results)
# ---------------------------------------------------------
# Generate grounded policy answer
# ---------------------------------------------------------

def query_policy(question: str) -> str:
    """
    Answer a telecom policy question using only the
    indexed policy documents.

    LlamaIndex retrieves relevant policy chunks and Claude
    synthesizes the final grounded response.
    """

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    if INDEX_DIR.exists():
        index = load_index()
    else:
        index = build_index()

    query_engine = index.as_query_engine(
        similarity_top_k=3,
        llm=llm,
    )

    try:
        response = query_engine.query(question)
        return str(response)

    except Exception as exc:
        raise RuntimeError(
            f"Policy RAG query failed: {exc}"
        ) from exc


# ---------------------------------------------------------
# Local test
# ---------------------------------------------------------

if __name__ == "__main__":

    if INDEX_DIR.exists():
        print("\nExisting Policy RAG index found.")
        print("Loading persisted vector index...\n")
        load_index()
    else:
        print("\nNo existing index found.")
        print("Building Policy RAG vector index...\n")
        build_index()

    test_question = (
    "What should a customer do if 5G is not working on their device?"
)






    print("\nTEST QUESTION")
    print("-" * 60)
    print(test_question)

    print("\nPOLICY RAG ANSWER")
    print("-" * 60)

    answer = query_policy(test_question)

    print(answer)