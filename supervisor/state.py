from typing import TypedDict


class SupervisorState(TypedDict):
    """
    Shared state passed between the LangGraph supervisor
    and specialist workers.
    """

    messages: list
    next: str
    user_query: str
    agent_context: str

    # Records every specialist worker executed by the graph.
    execution_trace: list

    # Final customer-facing response.
    final_response: str