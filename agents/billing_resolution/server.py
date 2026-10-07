import os
import tempfile

# Ensure LiteLLM/tiktoken uses the locally cached tokenizer.
# This avoids external tokenizer downloads in restricted corporate environments.
CACHE_DIR = os.path.join(tempfile.gettempdir(), "data-gym-cache")

os.environ["TIKTOKEN_CACHE_DIR"] = CACHE_DIR
os.environ["DATA_GYM_CACHE_DIR"] = CACHE_DIR

import tiktoken

# Pre-warm the tokenizer before ADK/LiteLLM is initialized.
tiktoken.get_encoding("cl100k_base")

from google.adk.a2a.utils.agent_to_a2a import to_a2a
from agents.billing_resolution.agent import root_agent

app = to_a2a(
    root_agent,
    host="localhost",
    port=8002,
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="localhost",
        port=8002,
    )