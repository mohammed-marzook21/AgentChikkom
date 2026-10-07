import pytest

from workers.document_rag import retrieve_policy


@pytest.mark.parametrize(
    "question, expected_source, expected_text",
    [
        (
            "How long does a customer have to dispute a charge?",
            "billing_disputes_policy.txt",
            "60 days",
        ),
        (
            "What should a customer do when 5G is not working?",
            "5g_faq.txt",
            "tower diagnostic",
        ),
        (
            "What is the policy for roaming while travelling?",
            "roaming_policy.txt",
            "Travel Pass",
        ),
        (
            "When is a customer eligible for an SLA credit?",
            "sla_policy.txt",
            "SLA credit",
        ),
        (
            "What is the device upgrade policy?",
            "device_upgrade_policy.txt",
            "36 month",
        ),
        (
            "What should be done during a network outage?",
            "network_outage_procedures.txt",
            "CRITICAL",
        ),
    ],
)
def test_policy_retrieval(question, expected_source, expected_text):
    result = retrieve_policy(question)

    assert result
    assert expected_source in result
    assert expected_text.lower() in result.lower()
