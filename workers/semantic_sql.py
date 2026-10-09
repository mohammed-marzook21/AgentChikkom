import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

from llama_index.core import Settings, SQLDatabase, VectorStoreIndex
from llama_index.core.objects import (
    ObjectIndex,
    SQLTableNodeMapping,
    SQLTableSchema,
)
from llama_index.core.query_engine import SQLTableRetrieverQueryEngine
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from workers.anthropic_compat import AnthropicNoTemperature


# ---------------------------------------------------------
# Project configuration
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "telecom_ops.db"

load_dotenv(BASE_DIR / ".env")


# ---------------------------------------------------------
# LLM + embedding configuration
# ---------------------------------------------------------

if not os.getenv("ANTHROPIC_API_KEY"):
    raise RuntimeError(
        "ANTHROPIC_API_KEY is not configured. "
        "Add it to the project's .env file."
    )

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

from workers.shared_resources import get_embedding_model

embed_model = get_embedding_model(str(LOCAL_EMBED_MODEL))

Settings.embed_model = embed_model

Settings.llm = AnthropicNoTemperature(
    model="claude-sonnet-4-5",
    
    system_prompt=(
        "You are the Network Analytics SQL specialist for a telecom "
        "operations system. "
        "Your responsibility is strictly to answer network operational "
        "and analytics questions using facts returned from the SQLite database. "
        "When generating SQL for execution, output only valid SQLite SQL. "
        "Never include Markdown code fences, asterisks, headings, explanations, "
        "comments, prefixes such as 'SQLQuery:', or text before or after the SQL. "
        "Use only tables and columns provided in the database schema. "
        "After SQL results are available, answer only from those query results. "
        "Do not provide policy advice, SLA interpretation, compensation rules, "
        "billing rules, eligibility decisions, recommendations, or general knowledge. "
        "Do not guess information that is not present in the SQL results. "
        "If the user's question contains both a network analytics question and a "
        "policy or compensation question, answer only the network analytics portion. "
        "Another specialist is responsible for policy interpretation."
    ),
)



# ---------------------------------------------------------
# SQLite connection
# ---------------------------------------------------------

def get_read_only_connection():
    """Open the operational database in SQLite read-only mode."""
    db_uri = f"file:{DB_PATH.as_posix()}?mode=ro"
    return sqlite3.connect(db_uri, uri=True)


engine = create_engine(
    "sqlite://",
    creator=get_read_only_connection,
)
NETWORK_TABLES = [
    "network_towers",
    "network_outages",
    "tower_performance",
    "open_incidents",
]

sql_database = SQLDatabase(
    engine,
    include_tables=NETWORK_TABLES,
)


# ---------------------------------------------------------
# Table descriptions
# ---------------------------------------------------------

table_details = [
    SQLTableSchema(
        table_name="network_towers",
        context_str=(
            "Network tower inventory. "
            "Contains tower_id, tower_name, region, city, state, "
            "technology, operational status, latitude, longitude, "
            "and commissioned_date. "
            "Use this table for questions about tower location, "
            "technology, region, and current tower status."
        ),
    ),

    SQLTableSchema(
        table_name="network_outages",
        context_str=(
            "Historical network outage records. "
            "Contains outage_id, region, severity, start_time, "
            "end_time, duration_hours, affected_customers, "
            "root_cause, status, and description. "
            "Use this table for outage counts, CRITICAL/MAJOR/MINOR "
            "outages, outage duration, affected customers, root causes, "
            "MTTR-style analysis, and regional outage comparisons."
        ),
    ),

    SQLTableSchema(
        table_name="tower_performance",
        context_str=(
            "Time-series tower performance measurements. "
            "Contains performance_id, tower_id, recorded_at, latency_ms, "
            "packet_loss_pct, downlink_throughput_mbps, "
            "uplink_throughput_mbps, signal_strength_dbm, "
            "and active_connections. "
            "Use this table for latency, packet loss, throughput, "
            "signal strength, connection counts, latest samples, "
            "and tower performance comparisons."
        ),
    ),

    SQLTableSchema(
        table_name="open_incidents",
        context_str=(
            "Current network incidents and investigations. "
            "Contains incident_id, tower_id, severity, status, title, "
            "description, opened_at, classification, and assigned_team. "
            "Use this table for current/open incidents, incident severity, "
            "assigned NOC teams, classifications, and active investigations."
        ),
    ),
]


# ---------------------------------------------------------
# Semantic table index
# ---------------------------------------------------------

table_node_mapping = SQLTableNodeMapping(
    sql_database
)

table_index = ObjectIndex.from_objects(
    table_details,
    table_node_mapping,
    VectorStoreIndex,
)

table_retriever = table_index.as_retriever(
    similarity_top_k=2
)


# ---------------------------------------------------------
# Semantic SQL query engine
# ---------------------------------------------------------

query_engine = SQLTableRetrieverQueryEngine(
    sql_database=sql_database,
    table_retriever=table_retriever,
    llm=Settings.llm,
)


# ---------------------------------------------------------
# Public worker function
# ---------------------------------------------------------

def query_network_analytics(question: str) -> str:
    """
    Convert a natural-language network analytics question into SQL,
    execute it against the approved network tables, and return the answer.
    """

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    try:
        response = query_engine.query(question)

        return str(response)

    except Exception as exc:
        raise RuntimeError(
            f"Semantic SQL query failed: {exc}"
        ) from exc


# ---------------------------------------------------------
# Local validation
# ---------------------------------------------------------

if __name__ == "__main__":

    question = (
    "What CRITICAL incidents are currently open?"
)

    print("\nNETWORK ANALYTICS TEST")
    print("=" * 70)

    print(f"\nQuestion: {question}")

    print("\nAnswer:")
    print(query_network_analytics(question))