from supervisor.state import SupervisorState
from workers.document_rag import query_policy
from workers.semantic_sql import query_network_analytics
from agents.remote_clients import call_network_agent, call_billing_agent
from crews.customer_comms import generate_customer_response


def _append_trace(
    state: SupervisorState,
    worker: str,
    output: str,
) -> list:
    """
    Return a new execution trace with one worker result appended.
    """
    trace = state.get("execution_trace", []).copy()

    trace.append(
        {
            "worker": worker,
            "output": str(output),
        }
    )

    return trace


def policy_rag_node(state: SupervisorState) -> dict:
    """
    LangGraph worker node for telecom policies, FAQs,
    roaming, SLA, device upgrades and other document knowledge.
    """
    question = state["user_query"]

    try:
        result = query_policy(question)

        context = (
            state.get("agent_context", "")
            + "\n\n[PolicyRAG]\n"
            + str(result)
        ).strip()

        trace = _append_trace(
            state,
            "PolicyRAG",
            str(result),
        )

        return {
            "agent_context": context,
            "execution_trace": trace,
            "next": "supervisor",
        }

    except Exception as exc:
        error_message = f"ERROR: {exc}"

        context = (
            state.get("agent_context", "")
            + "\n\n[PolicyRAG ERROR]\n"
            + str(exc)
        ).strip()

        trace = _append_trace(
            state,
            "PolicyRAG",
            error_message,
        )

        return {
            "agent_context": context,
            "execution_trace": trace,
            "next": "supervisor",
        }


def network_analytics_node(state: SupervisorState) -> dict:
    """
    LangGraph worker node for read-only network
    analytics through LlamaIndex Semantic SQL.
    """
    question = state["user_query"]

    try:
        result = query_network_analytics(question)

        context = (
            state.get("agent_context", "")
            + "\n\n[NetworkAnalytics]\n"
            + str(result)
        ).strip()

        trace = _append_trace(
            state,
            "NetworkAnalytics",
            str(result),
        )

        return {
            "agent_context": context,
            "execution_trace": trace,
            "next": "supervisor",
        }

    except Exception as exc:
        error_message = f"ERROR: {exc}"

        context = (
            state.get("agent_context", "")
            + "\n\n[NetworkAnalytics ERROR]\n"
            + str(exc)
        ).strip()

        trace = _append_trace(
            state,
            "NetworkAnalytics",
            error_message,
        )

        return {
            "agent_context": context,
            "execution_trace": trace,
            "next": "supervisor",
        }


def network_diagnostics_adk_node(
    state: SupervisorState,
) -> dict:
    """
    LangGraph worker node for remote Network Diagnostics
    through Google ADK + A2A.
    """
    question = state["user_query"]

    result = call_network_agent(question)

    context = (
        state.get("agent_context", "")
        + "\n\n[NetworkDiagnosticsADK]\n"
        + str(result)
    ).strip()

    trace = _append_trace(
        state,
        "NetworkDiagnosticsADK",
        str(result),
    )

    return {
        "agent_context": context,
        "execution_trace": trace,
        "next": "supervisor",
    }


def billing_resolution_adk_node(
    state: SupervisorState,
) -> dict:
    """
    LangGraph worker node for remote Billing Resolution
    through Google ADK + A2A.
    """
    question = state["user_query"]

    result = call_billing_agent(question)

    context = (
        state.get("agent_context", "")
        + "\n\n[BillingResolutionADK]\n"
        + str(result)
    ).strip()

    trace = _append_trace(
        state,
        "BillingResolutionADK",
        str(result),
    )

    return {
        "agent_context": context,
        "execution_trace": trace,
        "next": "supervisor",
    }


def customer_comms_crew_node(
    state: SupervisorState,
) -> dict:
    """
    Final LangGraph worker.

    CrewAI receives the original customer query plus the grounded
    context produced by the specialist workers. It drafts and reviews
    the final customer-facing response.
    """
    question = state["user_query"]
    context = state.get("agent_context", "").strip()

    try:
        if not context:
            result = (
                "I could not find enough grounded specialist information "
                "to prepare a reliable response."
            )
        else:
            result = generate_customer_response(
                question,
                context,
            )

        trace = _append_trace(
            state,
            "CustomerCommsCrew",
            str(result),
        )

        return {
            "final_response": str(result),
            "execution_trace": trace,
            "next": "supervisor",
        }

    except Exception as exc:
        error_message = (
            "Customer communications generation failed: "
            f"{exc}"
        )

        trace = _append_trace(
            state,
            "CustomerCommsCrew",
            f"ERROR: {exc}",
        )

        return {
            "final_response": error_message,
            "execution_trace": trace,
            "next": "supervisor",
        }