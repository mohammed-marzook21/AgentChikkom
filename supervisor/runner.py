from supervisor.graph import graph


def run_supervisor(user_query: str) -> dict:
    """
    Run the Prodapt LangGraph supervisor and return
    the standard application response contract.
    """

    if not user_query or not user_query.strip():
        raise ValueError("User query cannot be empty.")

    initial_state = {
        "messages": [],
        "next": "",
        "user_query": user_query.strip(),
        "agent_context": "",
        "execution_trace": [],
        "final_response": "",
    }

    result = graph.invoke(initial_state)

    trace = result.get("execution_trace", [])
    final_response = result.get("final_response", "").strip()

    if not final_response:
        final_response = (
            "The workflow completed, but no final customer response "
            "was generated."
        )

    return {
        "final_response": final_response,
        "execution_trace": trace,
        "agent_context": result.get(
            "agent_context",
            "",
        ),
    }