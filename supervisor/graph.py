from langgraph.graph import StateGraph, START, END

from supervisor.state import SupervisorState
from supervisor.workers import (
    policy_rag_node,
    network_analytics_node,
    network_diagnostics_adk_node,
    billing_resolution_adk_node,
    customer_comms_crew_node,
)


# ============================================================
# Worker names
# ============================================================

POLICY_RAG = "PolicyRAG"
NETWORK_ANALYTICS = "NetworkAnalytics"
NETWORK_DIAGNOSTICS = "NetworkDiagnosticsADK"
BILLING_RESOLUTION = "BillingResolutionADK"
CUSTOMER_COMMS = "CustomerCommsCrew"
FINISH = "FINISH"


# ============================================================
# Helper functions
# ============================================================

def _completed_workers(state: SupervisorState) -> set:
    """
    Read the execution trace and return the names of workers
    that have already executed.
    """
    return {
        item.get("worker")
        for item in state.get("execution_trace", [])
        if item.get("worker")
    }


def _comms_or_finish(completed: set) -> dict:
    """
    Every successful specialist workflow must pass through
    CustomerCommsCrew before the graph finishes.
    """
    if CUSTOMER_COMMS not in completed:
        return {"next": CUSTOMER_COMMS}

    return {"next": FINISH}


# ============================================================
# Supervisor routing logic
# ============================================================

def supervisor_node(state: SupervisorState) -> dict:
    """
    Decide which specialist should execute next.

    Required routing:

        Roaming / travel
            -> PolicyRAG
            -> CustomerCommsCrew

        SLA / outage compensation
            -> NetworkAnalytics
            -> PolicyRAG
            -> CustomerCommsCrew

        5G troubleshooting
            -> NetworkDiagnosticsADK
            -> CustomerCommsCrew

        Billing disputes
            -> BillingResolutionADK
            -> CustomerCommsCrew

        Network performance analytics
            -> NetworkAnalytics
            -> CustomerCommsCrew

        Device upgrade
            -> PolicyRAG
            -> CustomerCommsCrew

    CustomerCommsCrew is always the final worker.
    """

    query = state["user_query"].lower().strip()
    completed = _completed_workers(state)

    # ---------------------------------------------------------
    # 1. Workflow already reached CustomerCommsCrew
    # ---------------------------------------------------------

    if CUSTOMER_COMMS in completed:
        return {"next": FINISH}

    # ---------------------------------------------------------
    # 2. SLA / outage compensation
    #
    # These questions require BOTH:
    #   - network evidence
    #   - policy interpretation
    #
    # NetworkAnalytics runs first.
    # PolicyRAG runs second.
    # ---------------------------------------------------------

    sla_outage_case = (
        ("sla" in query or "outage" in query)
        and (
            "credit" in query
            or "compensation" in query
            or "refund" in query
            or "eligible" in query
            or "eligibility" in query
        )
    )

    if sla_outage_case:

        if NETWORK_ANALYTICS not in completed:
            return {"next": NETWORK_ANALYTICS}

        if POLICY_RAG not in completed:
            return {"next": POLICY_RAG}

        return _comms_or_finish(completed)

    # ---------------------------------------------------------
    # 3. Policy / FAQ questions
    #
    # IMPORTANT:
    # This is intentionally BEFORE billing routing.
    #
    # A query such as:
    #   "What roaming charges apply when I travel?"
    #
    # contains the word "charges", but it is a POLICY question,
    # not a billing-account investigation.
    #
    # Examples:
    #   roaming
    #   travel
    #   international
    #   device upgrade
    #   eligibility
    #   policy
    #   FAQ
    # ---------------------------------------------------------

    policy_keywords = (
        "policy",
        "roaming",
        "travel",
        "international",
        "device upgrade",
        "upgrade policy",
        "faq",
        "eligibility",
        "upgrade eligibility",
        "upgrade my device",
        "international plan",
        "roaming plan",
        "travel package",
        "travel pass",
    )

    if any(keyword in query for keyword in policy_keywords):

        if POLICY_RAG not in completed:
            return {"next": POLICY_RAG}

        return _comms_or_finish(completed)

    # ---------------------------------------------------------
    # 4. Billing disputes / billing operations
    #
    # Examples:
    #   "I was charged twice"
    #   "Check my billing"
    #   "duplicate charge"
    #   "billing dispute"
    #
    # Generic "charges" are handled here ONLY when the query
    # was not already identified as a policy/roaming question.
    # ---------------------------------------------------------

    billing_keywords = (
        "billing",
        "bill",
        "charge",
        "charged",
        "duplicate",
        "invoice",
        "dispute",
        "balance",
        "billing account",
        "billing issue",
        "payment",
        "payment issue",
    )

    if any(keyword in query for keyword in billing_keywords):

        if BILLING_RESOLUTION not in completed:
            return {"next": BILLING_RESOLUTION}

        return _comms_or_finish(completed)

    # ---------------------------------------------------------
    # 5. Network performance analytics
    #
    # IMPORTANT:
    # Performance questions are evaluated BEFORE generic
    # diagnostics keywords such as "packet loss", "latency",
    # and "tower".
    #
    # This prevents:
    #
    # "latest packet loss and performance"
    #
    # from incorrectly becoming NetworkDiagnosticsADK.
    # ---------------------------------------------------------

    analytics_keywords = (
        "network performance",
        "network analytics",
        "regional network",
        "region",
        "outage count",
        "critical outage",
        "highest packet loss",
        "performance summary",
        "latest performance",
        "network health",
        "network statistics",
        "network metrics",
        "performance metrics",
        "incident count",
        "performance",
    )

    # Explicit troubleshooting language should override
    # general performance language.

    explicit_diagnostics = (
        "troubleshoot",
        "troubleshooting",
        "diagnose",
        "diagnostic",
        "connectivity problem",
        "connectivity issue",
        "connection problem",
        "connection issue",
        "why is my connection",
        "why is my 5g",
        "5g connection is",
        "connection is dropping",
        "connection keeps dropping",
    )

    is_analytics_question = any(
        keyword in query
        for keyword in analytics_keywords
    )

    is_explicit_diagnostics = any(
        keyword in query
        for keyword in explicit_diagnostics
    )

    if is_analytics_question and not is_explicit_diagnostics:

        if NETWORK_ANALYTICS not in completed:
            return {"next": NETWORK_ANALYTICS}

        return _comms_or_finish(completed)

    # ---------------------------------------------------------
    # 6. Network tower / connectivity diagnostics
    #
    # These questions are intended for the Google ADK
    # Network Diagnostics A2A service.
    # ---------------------------------------------------------

    diagnostics_keywords = (
        "tower",
        "connectivity",
        "packet loss",
        "signal strength",
        "offline",
        "degraded",
        "latency",
        "5g",
        "session drop",
        "session drops",
        "dropped connection",
        "connection dropping",
        "site status",
        "tower status",
        "diagnostics",
    )

    if any(keyword in query for keyword in diagnostics_keywords):

        if NETWORK_DIAGNOSTICS not in completed:
            return {"next": NETWORK_DIAGNOSTICS}

        return _comms_or_finish(completed)

    # ---------------------------------------------------------
    # 7. Unknown / general telecom question
    #
    # PolicyRAG is the safe general knowledge fallback.
    # ---------------------------------------------------------

    if POLICY_RAG not in completed:
        return {"next": POLICY_RAG}

    return _comms_or_finish(completed)


# ============================================================
# Conditional routing function
# ============================================================

def route_supervisor(state: SupervisorState) -> str:
    """
    Return the supervisor's selected route.
    """
    return state["next"]


# ============================================================
# Build LangGraph
# ============================================================

builder = StateGraph(SupervisorState)


# ------------------------------------------------------------
# Supervisor
# ------------------------------------------------------------

builder.add_node(
    "supervisor",
    supervisor_node,
)


# ------------------------------------------------------------
# Specialist workers
# ------------------------------------------------------------

builder.add_node(
    POLICY_RAG,
    policy_rag_node,
)

builder.add_node(
    NETWORK_ANALYTICS,
    network_analytics_node,
)

builder.add_node(
    NETWORK_DIAGNOSTICS,
    network_diagnostics_adk_node,
)

builder.add_node(
    BILLING_RESOLUTION,
    billing_resolution_adk_node,
)

builder.add_node(
    CUSTOMER_COMMS,
    customer_comms_crew_node,
)


# ============================================================
# Graph entry
# ============================================================

builder.add_edge(
    START,
    "supervisor",
)


# ============================================================
# Supervisor conditional routing
# ============================================================

builder.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {
        POLICY_RAG: POLICY_RAG,
        NETWORK_ANALYTICS: NETWORK_ANALYTICS,
        NETWORK_DIAGNOSTICS: NETWORK_DIAGNOSTICS,
        BILLING_RESOLUTION: BILLING_RESOLUTION,
        CUSTOMER_COMMS: CUSTOMER_COMMS,
        FINISH: END,
    },
)


# ============================================================
# Worker -> Supervisor edges
#
# Every specialist returns control to the supervisor.
# This allows the supervisor to decide whether another
# specialist is required or whether CustomerCommsCrew
# should execute.
# ============================================================

builder.add_edge(
    POLICY_RAG,
    "supervisor",
)

builder.add_edge(
    NETWORK_ANALYTICS,
    "supervisor",
)

builder.add_edge(
    NETWORK_DIAGNOSTICS,
    "supervisor",
)

builder.add_edge(
    BILLING_RESOLUTION,
    "supervisor",
)

builder.add_edge(
    CUSTOMER_COMMS,
    "supervisor",
)


# ============================================================
# Compile graph
# ============================================================

graph = builder.compile()