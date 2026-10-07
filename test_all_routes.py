import pytest

from supervisor.graph import (
    supervisor_node,
    NETWORK_ANALYTICS,
    NETWORK_DIAGNOSTICS,
    BILLING_RESOLUTION,
    POLICY_RAG,
    CUSTOMER_COMMS,
    FINISH,
)


def make_state(query, execution_trace=None):
    return {
        "messages": [],
        "next": "",
        "user_query": query,
        "agent_context": "",
        "execution_trace": execution_trace or [],
        "final_response": "",
    }


def workers(*names):
    return [{"worker": name} for name in names]


@pytest.mark.parametrize(
    "query, expected",
    [
        (
            "I am travelling abroad next week. What is the roaming policy for my plan?",
            POLICY_RAG,
        ),
        (
            "Which region has the most CRITICAL outages, and could customers be eligible for outage compensation?",
            NETWORK_ANALYTICS,
        ),
        (
            "My 5G connection is slow and dropping. Can you troubleshoot the network around Austin Riverside?",
            NETWORK_DIAGNOSTICS,
        ),
        (
            "I was charged twice for the same subscription charge. Can you check and help resolve it for CUST-10002?",
            BILLING_RESOLUTION,
        ),
        (
            "What is the latest packet loss and performance for the Austin Riverside tower?",
            NETWORK_ANALYTICS,
        ),
        (
            "Can I upgrade my device and what are the device upgrade eligibility rules?",
            POLICY_RAG,
        ),
    ],
)
def test_initial_route(query, expected):
    state = make_state(query)

    result = supervisor_node(state)

    assert result["next"] == expected


def test_sla_route_moves_to_policy_after_network_analytics():
    state = make_state(
        "Could customers be eligible for outage compensation?",
        workers(NETWORK_ANALYTICS),
    )

    result = supervisor_node(state)

    assert result["next"] == POLICY_RAG


def test_completed_policy_route_moves_to_customer_comms():
    state = make_state(
        "What is the roaming policy?",
        workers(POLICY_RAG),
    )

    result = supervisor_node(state)

    assert result["next"] == CUSTOMER_COMMS


def test_completed_customer_comms_finishes():
    state = make_state(
        "What is the roaming policy?",
        workers(POLICY_RAG, CUSTOMER_COMMS),
    )

    result = supervisor_node(state)

    assert result["next"] == FINISH


def test_completed_billing_route_moves_to_customer_comms():
    state = make_state(
        "I was charged twice for the same subscription charge.",
        workers(BILLING_RESOLUTION),
    )

    result = supervisor_node(state)

    assert result["next"] == CUSTOMER_COMMS


def test_completed_network_analytics_route_moves_to_customer_comms():
    state = make_state(
        "Show me network performance statistics.",
        workers(NETWORK_ANALYTICS),
    )

    result = supervisor_node(state)

    assert result["next"] == CUSTOMER_COMMS