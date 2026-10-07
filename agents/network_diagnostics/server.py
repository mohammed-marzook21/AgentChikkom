import os
import tempfile

# ---------------------------------------------------------------------------
# Corporate-environment tokenizer cache setup
#
# LiteLLM uses tiktoken internally when an Anthropic request is executed.
# Preload the tokenizer before importing ADK/LiteLLM so the A2A server never
# needs to download cl100k_base.tiktoken during a request.
# ---------------------------------------------------------------------------

CACHE_DIR = os.path.join(tempfile.gettempdir(), "data-gym-cache")

os.environ["TIKTOKEN_CACHE_DIR"] = CACHE_DIR
os.environ["DATA_GYM_CACHE_DIR"] = CACHE_DIR

# Validate the locally cached tokenizer before loading ADK/LiteLLM.
import tiktoken

tiktoken.get_encoding("cl100k_base")


from google.adk.a2a.utils.agent_to_a2a import to_a2a
from agents.network_diagnostics.agent import root_agent


app = to_a2a(
    root_agent,
    host="localhost",
    port=8001,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="localhost",
        port=8001,
    )