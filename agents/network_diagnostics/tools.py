import sqlite3
from pathlib import Path
from typing import Any


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "telecom_ops.db"


# ---------------------------------------------------------
# Database helper
# ---------------------------------------------------------

def get_db_connection() -> sqlite3.Connection:
    """
    Open a read-only connection to the telecom operational database.
    """

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Telecom database not found: {DB_PATH}"
        )

    db_uri = f"file:{DB_PATH.as_posix()}?mode=ro"

    conn = sqlite3.connect(
        db_uri,
        uri=True,
    )

    conn.row_factory = sqlite3.Row

    return conn


# ---------------------------------------------------------
# Tool 1 - Tower status
# ---------------------------------------------------------

def check_tower_status(tower_id: str) -> dict[str, Any]:
    """
    Check the current operational status and latest performance
    information for a telecom tower.

    Args:
        tower_id: Tower identifier such as TX-512.

    Returns:
        Dictionary containing tower information and its latest
        performance metrics.
    """

    tower_id = tower_id.strip().upper()

    if not tower_id:
        return {
            "status": "error",
            "message": "tower_id cannot be empty",
        }

    conn = get_db_connection()

    try:
        tower = conn.execute(
            """
            SELECT
                tower_id,
                tower_name,
                region,
                city,
                state,
                technology,
                status
            FROM network_towers
            WHERE tower_id = ?
            """,
            (tower_id,),
        ).fetchone()

        if tower is None:
            return {
                "status": "not_found",
                "message": f"Tower {tower_id} was not found.",
            }

        performance = conn.execute(
            """
            SELECT
                recorded_at,
                latency_ms,
                packet_loss_pct,
                downlink_throughput_mbps,
                uplink_throughput_mbps,
                signal_strength_dbm,
                active_connections
            FROM tower_performance
            WHERE tower_id = ?
            ORDER BY recorded_at DESC
            LIMIT 1
            """,
            (tower_id,),
        ).fetchone()

        result = {
            "status": "success",
            "tower": dict(tower),
            "latest_performance": (
                dict(performance)
                if performance is not None
                else None
            ),
        }

        return result

    finally:
        conn.close()


# ---------------------------------------------------------
# Tool 2 - Connectivity diagnostics
# ---------------------------------------------------------

def run_connectivity_diagnostics(
    tower_id: str,
) -> dict[str, Any]:
    """
    Run connectivity diagnostics for a tower using its latest
    performance metrics and currently open incidents.

    Args:
        tower_id: Tower identifier such as FL-090.

    Returns:
        Dictionary containing the latest network measurements,
        open incidents and diagnostic observations.
    """

    tower_id = tower_id.strip().upper()

    if not tower_id:
        return {
            "status": "error",
            "message": "tower_id cannot be empty",
        }

    conn = get_db_connection()

    try:
        tower = conn.execute(
            """
            SELECT
                tower_id,
                tower_name,
                region,
                city,
                technology,
                status
            FROM network_towers
            WHERE tower_id = ?
            """,
            (tower_id,),
        ).fetchone()

        if tower is None:
            return {
                "status": "not_found",
                "message": f"Tower {tower_id} was not found.",
            }

        performance = conn.execute(
            """
            SELECT
                recorded_at,
                latency_ms,
                packet_loss_pct,
                downlink_throughput_mbps,
                uplink_throughput_mbps,
                signal_strength_dbm,
                active_connections
            FROM tower_performance
            WHERE tower_id = ?
            ORDER BY recorded_at DESC
            LIMIT 1
            """,
            (tower_id,),
        ).fetchone()

        incidents = conn.execute(
            """
            SELECT
                incident_id,
                severity,
                status,
                title,
                description,
                opened_at,
                classification,
                assigned_team
            FROM open_incidents
            WHERE tower_id = ?
              AND status != 'RESOLVED'
            ORDER BY opened_at DESC
            """,
            (tower_id,),
        ).fetchall()

        observations = []

        if performance is None:
            observations.append(
                "No performance data is available for this tower."
            )
        else:
            packet_loss = performance["packet_loss_pct"]
            latency = performance["latency_ms"]
            signal = performance["signal_strength_dbm"]
            downlink = performance["downlink_throughput_mbps"]

            if packet_loss >= 100:
                observations.append(
                    "Complete packet loss detected."
                )
            elif packet_loss >= 5:
                observations.append(
                    "High packet loss detected."
                )
            elif packet_loss >= 1:
                observations.append(
                    "Elevated packet loss detected."
                )

            if latency >= 100:
                observations.append(
                    "High network latency detected."
                )

            if signal <= -110:
                observations.append(
                    "Very weak or unavailable radio signal detected."
                )
            elif signal <= -95:
                observations.append(
                    "Weak radio signal detected."
                )

            if downlink <= 0:
                observations.append(
                    "No downlink throughput detected."
                )
            elif downlink < 50:
                observations.append(
                    "Low downlink throughput detected."
                )

        if incidents:
            observations.append(
                f"{len(incidents)} unresolved incident(s) "
                "are associated with this tower."
            )

        if not observations:
            observations.append(
                "No major connectivity issue detected from "
                "the latest available measurements."
            )

        return {
            "status": "success",
            "tower": dict(tower),
            "latest_performance": (
                dict(performance)
                if performance is not None
                else None
            ),
            "open_incidents": [
                dict(row) for row in incidents
            ],
            "diagnostic_observations": observations,
        }

    finally:
        conn.close()


# ---------------------------------------------------------
# Tool 3 - Regional network summary
# ---------------------------------------------------------

def get_regional_network_summary(
    region: str,
) -> dict[str, Any]:
    """
    Get a regional network summary using tower inventory,
    unresolved incidents and recent tower performance.

    Args:
        region: Network region such as Midwest or Southwest.

    Returns:
        Dictionary containing tower counts, tower status,
        unresolved incidents and latest regional performance.
    """

    region = region.strip()

    if not region:
        return {
            "status": "error",
            "message": "region cannot be empty",
        }

    conn = get_db_connection()

    try:
        towers = conn.execute(
            """
            SELECT
                tower_id,
                tower_name,
                status,
                technology,
                city,
                state
            FROM network_towers
            WHERE LOWER(region) = LOWER(?)
            ORDER BY tower_id
            """,
            (region,),
        ).fetchall()

        if not towers:
            return {
                "status": "not_found",
                "message": f"Region {region} was not found.",
            }

        tower_ids = [row["tower_id"] for row in towers]

        placeholders = ",".join(
            "?" for _ in tower_ids
        )

        incidents = conn.execute(
            f"""
            SELECT
                incident_id,
                tower_id,
                severity,
                status,
                title,
                opened_at,
                assigned_team
            FROM open_incidents
            WHERE tower_id IN ({placeholders})
              AND status != 'RESOLVED'
            ORDER BY opened_at DESC
            """,
            tower_ids,
        ).fetchall()

        performance = conn.execute(
            """
            WITH latest AS (
                SELECT
                    tp.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY tp.tower_id
                        ORDER BY tp.recorded_at DESC
                    ) AS rn
                FROM tower_performance tp
                JOIN network_towers nt
                    ON nt.tower_id = tp.tower_id
                WHERE LOWER(nt.region) = LOWER(?)
            )
            SELECT
                COUNT(*) AS towers_with_performance,
                ROUND(AVG(latency_ms), 2)
                    AS avg_latency_ms,
                ROUND(AVG(packet_loss_pct), 2)
                    AS avg_packet_loss_pct,
                ROUND(AVG(downlink_throughput_mbps), 2)
                    AS avg_downlink_mbps,
                ROUND(AVG(signal_strength_dbm), 2)
                    AS avg_signal_strength_dbm
            FROM latest
            WHERE rn = 1
            """,
            (region,),
        ).fetchone()

        status_counts = {}

        for tower in towers:
            tower_status = tower["status"]

            status_counts[tower_status] = (
                status_counts.get(tower_status, 0) + 1
            )

        return {
            "status": "success",
            "region": region,
            "tower_count": len(towers),
            "tower_status_counts": status_counts,
            "towers": [
                dict(row) for row in towers
            ],
            "unresolved_incident_count": len(incidents),
            "unresolved_incidents": [
                dict(row) for row in incidents
            ],
            "latest_performance_summary": dict(performance),
        }

    finally:
        conn.close()