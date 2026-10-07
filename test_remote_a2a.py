import json
from urllib.request import urlopen

import pytest


NETWORK_CARD_URL = "http://localhost:8001/.well-known/agent-card.json"
BILLING_CARD_URL = "http://localhost:8002/.well-known/agent-card.json"


def get_agent_card(url):
    with urlopen(url, timeout=5) as response:
        assert response.status == 200
        return json.load(response)


def skill_names(card):
    return {skill["name"] for skill in card["skills"]}


def test_network_a2a_agent_card():
    card = get_agent_card(NETWORK_CARD_URL)

    assert card["name"] == "network_diagnostics_agent"
    assert card["supportedInterfaces"][0]["protocolBinding"] == "JSONRPC"
    assert card["capabilities"]["streaming"] is True

    skills = skill_names(card)

    assert "check_tower_status" in skills
    assert "run_connectivity_diagnostics" in skills
    assert "get_regional_network_summary" in skills


def test_billing_a2a_agent_card():
    card = get_agent_card(BILLING_CARD_URL)

    assert card["name"] == "billing_resolution_agent"
    assert card["supportedInterfaces"][0]["protocolBinding"] == "JSONRPC"
    assert card["capabilities"]["streaming"] is True

    skills = skill_names(card)

    assert "lookup_billing_account" in skills
    assert "check_duplicate_charges" in skills
    assert "apply_billing_credit" in skills


def test_a2a_services_are_independent():
    network_card = get_agent_card(NETWORK_CARD_URL)
    billing_card = get_agent_card(BILLING_CARD_URL)

    network_url = network_card["supportedInterfaces"][0]["url"]
    billing_url = billing_card["supportedInterfaces"][0]["url"]

    assert network_url != billing_url
    assert network_url.endswith(":8001")
    assert billing_url.endswith(":8002")
