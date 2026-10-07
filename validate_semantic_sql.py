import sqlite3

conn = sqlite3.connect("data/telecom_ops.db")
cursor = conn.cursor()

query = """
SELECT
    region,
    COUNT(*) AS critical_count
FROM network_outages
WHERE severity = 'CRITICAL'
GROUP BY region
ORDER BY critical_count DESC;
"""


rows = cursor.execute(query).fetchall()

print("\nCRITICAL OUTAGES BY REGION")
print("=" * 50)

for region, count in rows:
    print(f"{region:<20} {count}")
print("\nLATEST SAMPLE - HIGHEST PACKET LOSS")
print("=" * 50)

query = """
SELECT
    tp.tower_id,
    nt.tower_name,
    tp.recorded_at,
    tp.packet_loss_pct
FROM tower_performance tp
JOIN network_towers nt
    ON tp.tower_id = nt.tower_id
WHERE tp.recorded_at = (
    SELECT MAX(recorded_at)
    FROM tower_performance
)
ORDER BY tp.packet_loss_pct DESC
LIMIT 1;
"""

row = cursor.execute(query).fetchone()

print(f"Tower ID:    {row[0]}")
print(f"Tower Name:  {row[1]}")
print(f"Recorded At: {row[2]}")
print(f"Packet Loss: {row[3]}%")

print("\nCURRENTLY OPEN CRITICAL INCIDENTS")
print("=" * 50)

query = """
SELECT
    incident_id,
    tower_id,
    title,
    status,
    opened_at,
    assigned_team
FROM open_incidents
WHERE severity = 'CRITICAL'
  AND status = 'OPEN'
ORDER BY opened_at DESC;
"""

rows = cursor.execute(query).fetchall()

print(f"Count: {len(rows)}")

for row in rows:
    print(f"Incident ID:   {row[0]}")
    print(f"Tower ID:      {row[1]}")
    print(f"Title:         {row[2]}")
    print(f"Status:        {row[3]}")
    print(f"Opened At:     {row[4]}")
    print(f"Assigned Team: {row[5]}")
conn.close()