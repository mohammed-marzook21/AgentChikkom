import asyncio
import threading

from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


NETWORK_AGENT_CARD = (
    "http://localhost:8001/.well-known/agent-card.json"
)

BILLING_AGENT_CARD = (
    "http://localhost:8002/.well-known/agent-card.json"
)


network_remote_agent = RemoteA2aAgent(
    name="network_diagnostics_remote",
    description=(
        "Remote A2A client for the Prodapt Network Diagnostics specialist."
    ),
    agent_card=NETWORK_AGENT_CARD,
)


billing_remote_agent = RemoteA2aAgent(
    name="billing_resolution_remote",
    description=(
        "Remote A2A client for the Prodapt Billing Resolution specialist."
    ),
    agent_card=BILLING_AGENT_CARD,
)


async def _call_remote_agent(
    agent: RemoteA2aAgent,
    question: str,
    session_id: str,
) -> str:
    """
    Send a question to a remote ADK A2A agent and return
    its final text response.
    """
    app_name = "prodapt_supervisor"
    user_id = "langgraph_user"

    session_service = InMemorySessionService()

    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )

    runner = Runner(
        app_name=app_name,
        agent=agent,
        session_service=session_service,
    )

    message = types.Content(
        role="user",
        parts=[types.Part(text=question)],
    )

    final_response = ""

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=message,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response = "".join(
                    part.text or ""
                    for part in event.content.parts
                )

    if not final_response:
        return "Remote agent returned no response."

    return final_response


class _PersistentAsyncRunner:
    """
    Runs all RemoteA2A calls on one persistent event loop.

    This avoids asyncio.run() creating and closing a different
    event loop for every LangGraph worker invocation.
    """

    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
        )
        self._thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run(self, coroutine):
        future = asyncio.run_coroutine_threadsafe(
            coroutine,
            self._loop,
        )
        return future.result()


_async_runner = _PersistentAsyncRunner()


def call_network_agent(question: str) -> str:
    """
    Synchronous wrapper used by LangGraph for Network Diagnostics.
    """
    try:
        return _async_runner.run(
            _call_remote_agent(
                network_remote_agent,
                question,
                "network_langgraph_session",
            )
        )
    except Exception as exc:
        return (
            "Network Diagnostics service unavailable: "
            f"{exc}"
        )


def call_billing_agent(question: str) -> str:
    """
    Synchronous wrapper used by LangGraph for Billing Resolution.
    """
    try:
        return _async_runner.run(
            _call_remote_agent(
                billing_remote_agent,
                question,
                "billing_langgraph_session",
            )
        )
    except Exception as exc:
        return (
            "Billing Resolution service unavailable: "
            f"{exc}"
        )
