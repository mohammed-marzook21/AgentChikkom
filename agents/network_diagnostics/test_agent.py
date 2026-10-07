import pytest

from agents.network_diagnostics.tools import (
    check_tower_status,
    run_connectivity_diagnostics,
    get_regional_network_summary,
)


def test_check_tower_status():
    result = check_tower_status("TX-512")

    assert result["status"] == "success"
    assert result["tower"]["tower_id"] == "TX-512"
    assert result["tower"]["tower_name"] == "Austin Riverside"
    assert result["tower"]["status"] == "OPERATIONAL"
    assert result["latest_performance"]["packet_loss_pct"] == 3.8


def test_run_connectivity_diagnostics():
    result = run_connectivity_diagnostics("TX-512")

    assert result["status"] == "success"
    assert result["tower"]["tower_id"] == "TX-512"
    assert result["latest_performance"]["packet_loss_pct"] == 3.8
    assert result["latest_performance"]["downlink_throughput_mbps"] == 85.0
    assert len(result["open_incidents"]) >= 1
    assert result["open_incidents"][0]["incident_id"] == "INC-8841"
    assert "Elevated packet loss detected." in result["diagnostic_observations"]


def test_regional_network_summary():
    result = get_regional_network_summary("Southwest")

    assert result["status"] == "success"
    assert result["region"] == "Southwest"
    assert result["tower_count"] == 2
    assert result["unresolved_incident_count"] == 2
    assert result["latest_performance_summary"]["avg_packet_loss_pct"] == 6.2
