import socket

import sqlite3

from pathlib import Path


import streamlit as st




BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "data" / "telecom_ops.db"

VECTOR_INDEX_PATH = BASE_DIR / "data" / "vector_index"


# =========================================================

# Configuration

# =========================================================


st.set_page_config(

    page_title="Prodapt AI Operations Center",

    page_icon="📡",

    layout="wide",

)


# =========================================================

# System Health Checks

# =========================================================


@st.cache_data(ttl=5, show_spinner=False)
def check_port(port: int) -> bool:

    """Return True when a local service is listening."""

    try:

        with socket.create_connection(

            ("127.0.0.1", port),

            timeout=0.2,

        ):

            return True

    except OSError:

        return False


@st.cache_data(ttl=10, show_spinner=False)
def check_database() -> bool:

    """Verify that the telecom SQLite database is accessible."""

    if not DB_PATH.exists():

        return False


    try:

        connection = sqlite3.connect(DB_PATH)

        connection.execute("SELECT 1")

        connection.close()

        return True

    except sqlite3.Error:

        return False


@st.cache_data(ttl=10, show_spinner=False)
def check_vector_index() -> bool:

    """Check whether the persisted policy vector index exists."""

    return VECTOR_INDEX_PATH.exists()


# =========================================================

# Human-in-the-Loop Billing Approval

# =========================================================


@st.cache_data(ttl=5, show_spinner=False)
def get_pending_billing_credits():

    """

    Read pending billing credits directly from SQLite.


    The database remains the source of truth.

    """

    if not DB_PATH.exists():

        return []


    connection = None


    try:

        connection = sqlite3.connect(DB_PATH)

        connection.row_factory = sqlite3.Row


        rows = connection.execute(

            """

            SELECT

                credit_id,

                customer_id,

                amount,

                reason,

                status,

                related_charge_id

            FROM billing_credits

            WHERE status = 'PENDING_APPROVAL'

            ORDER BY credit_id

            """

        ).fetchall()


        return [dict(row) for row in rows]


    except sqlite3.Error:

        return []


    finally:

        if connection is not None:

            connection.close()


def approve_billing_credit(credit_id: int) -> tuple[bool, str]:

    """

    Approve a pending billing credit.


    This performs the database update inside a transaction.


    Approval rules:

    - Credit must currently be PENDING_APPROVAL.

    - The credit is changed to APPLIED.

    - The customer's balance is reduced by the credit amount.

    """

    connection = None


    try:

        connection = sqlite3.connect(DB_PATH)

        connection.row_factory = sqlite3.Row


        connection.execute("BEGIN")


        credit = connection.execute(

            """

            SELECT

                credit_id,

                customer_id,

                amount,

                status

            FROM billing_credits

            WHERE credit_id = ?

            """,

            (credit_id,),

        ).fetchone()


        if credit is None:

            connection.rollback()

            return False, "Billing credit was not found."


        if credit["status"] != "PENDING_APPROVAL":

            connection.rollback()

            return False, (

                f"Credit {credit_id} is no longer pending approval."

            )


        customer_id = credit["customer_id"]

        amount = float(credit["amount"])


        account = connection.execute(

            """

            SELECT current_balance

            FROM billing_accounts

            WHERE customer_id = ?

            """,

            (customer_id,),

        ).fetchone()


        if account is None:

            connection.rollback()

            return False, (

                f"Billing account for {customer_id} was not found."

            )


        current_balance = float(account["current_balance"])


        new_balance = max(

            0.0,

            current_balance - amount,

        )


        connection.execute(

            """

            UPDATE billing_credits

            SET status = 'APPLIED'

            WHERE credit_id = ?

              AND status = 'PENDING_APPROVAL'

            """,

            (credit_id,),

        )


        connection.execute(

            """

            UPDATE billing_accounts

            SET current_balance = ?

            WHERE customer_id = ?

            """,

            (new_balance, customer_id),

        )


        connection.commit()


        return True, (

            f"Credit #{credit_id} approved. "

            f"${amount:.2f} applied to {customer_id}."

        )


    except sqlite3.Error as exc:

        if connection is not None:

            connection.rollback()


        return False, f"Approval failed: {exc}"


    finally:

        if connection is not None:

            connection.close()


def reject_billing_credit(credit_id: int) -> tuple[bool, str]:

    """

    Reject a pending billing credit.


    Rejection keeps the financial balance unchanged.

    """

    connection = None


    try:

        connection = sqlite3.connect(DB_PATH)


        connection.execute("BEGIN")


        cursor = connection.execute(

            """

            UPDATE billing_credits

            SET status = 'REJECTED'

            WHERE credit_id = ?

              AND status = 'PENDING_APPROVAL'

            """,

            (credit_id,),

        )


        if cursor.rowcount == 0:

            connection.rollback()

            return False, (

                f"Credit {credit_id} was not pending approval."

            )


        connection.commit()


        return True, (

            f"Credit #{credit_id} was rejected."

        )


    except sqlite3.Error as exc:

        if connection is not None:

            connection.rollback()


        return False, f"Rejection failed: {exc}"


    finally:

        if connection is not None:

            connection.close()


# =========================================================


# =========================================================
# Presentation helpers
# =========================================================

def show_status(name: str, available: bool) -> None:
    """Display component availability."""
    if available:
        st.success(f"🟢 {name}: Online")
    else:
        st.error(f"🔴 {name}: Offline")


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .hero {
            padding: 1.2rem 1.4rem;
            border-radius: 18px;
            background: linear-gradient(135deg, #0b1220 0%, #16233a 55%, #0f766e 140%);
            color: white;
            border: 1px solid rgba(255,255,255,.10);
            margin-bottom: 1rem;
        }
        .hero-title {font-size: 2rem; font-weight: 800; margin: 0;}
        .hero-sub {font-size: .95rem; opacity: .82; margin-top: .35rem;}
        .pill {
            display:inline-block; padding:.25rem .55rem; border-radius:999px;
            background:rgba(255,255,255,.10); margin:.45rem .25rem 0 0;
            font-size:.75rem;
        }
        .section-card {
            border: 1px solid rgba(128,128,128,.22);
            border-radius: 16px;
            padding: 1rem;
            margin-bottom: .75rem;
        }
        .status-ok {color:#16a34a; font-weight:700;}
        .status-warn {color:#d97706; font-weight:700;}
        .status-bad {color:#dc2626; font-weight:700;}
        .agent-node {
            border:1px solid rgba(99,102,241,.28);
            border-radius:14px;
            padding:.75rem;
            text-align:center;
            min-height:92px;
        }
        .agent-node .name {font-weight:750; font-size:.92rem;}
        .agent-node .tech {font-size:.72rem; opacity:.72; margin-top:.25rem;}
        .arrow {text-align:center; font-size:1.5rem; opacity:.6; padding-top:1.2rem;}
        .case-label {font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; opacity:.6;}
        .case-value {font-weight:700; margin-top:.15rem;}
        .timeline-step {
            border-left:3px solid #6366f1;
            padding: .15rem 0 .8rem 1rem;
            margin-left:.5rem;
        }
        .timeline-step:last-child {border-left-color:#16a34a;}
        .timeline-num {font-size:.72rem; opacity:.6;}

        .health-grid {
            display:grid;
            grid-template-columns:repeat(5, minmax(0, 1fr));
            gap:.7rem;
            margin: .15rem 0 1.15rem 0;
        }
        .health-card {
            border:1px solid rgba(128,128,128,.20);
            border-radius:14px;
            padding:.72rem .75rem;
            background:rgba(128,128,128,.045);
            min-width:0;
        }
        .health-card.ok {
            border-color:rgba(22,163,74,.22);
            background:rgba(22,163,74,.055);
        }
        .health-card.warn {
            border-color:rgba(217,119,6,.22);
            background:rgba(217,119,6,.055);
        }
        .health-name {
            font-size:.76rem;
            font-weight:650;
            opacity:.72;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
        }
        .health-state {
            display:flex;
            align-items:center;
            gap:.42rem;
            margin-top:.28rem;
            font-size:.9rem;
            font-weight:750;
        }
        .health-dot {
            width:9px;
            height:9px;
            border-radius:50%;
            display:inline-block;
            flex:0 0 9px;
            background:#16a34a;
            box-shadow:0 0 0 4px rgba(22,163,74,.12);
        }
        .health-dot.warn {
            background:#d97706;
            box-shadow:0 0 0 4px rgba(217,119,6,.12);
        }
        @media (max-width: 900px) {
            .health-grid {grid-template-columns:repeat(2, minmax(0, 1fr));}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def infer_intent(query: str) -> str:
    q = query.lower()
    if any(k in q for k in ["sla", "outage", "compensation"]):
        return "SLA / Outage Compensation"
    if any(k in q for k in [
        "billing", "bill", "charge", "charged", "duplicate",
        "credit", "refund", "dispute", "invoice"
    ]):
        return "Billing Resolution"
    if any(k in q for k in [
        "roaming", "travel", "policy", "faq", "upgrade", "eligibility"
    ]):
        return "Policy / Eligibility"
    if any(k in q for k in [
        "latency", "packet loss", "throughput", "tower", "network",
        "outage", "performance", "region"
    ]):
        return "Network Operations"
    if any(k in q for k in ["5g", "signal", "connectivity", "internet", "connection"]):
        return "5G / Connectivity Diagnostics"
    return "General Operations"


def worker_display_name(worker: str) -> tuple[str, str]:
    mapping = {
        "PolicyRAG": ("Policy RAG", "LlamaIndex"),
        "NetworkAnalytics": ("Network Analytics", "LlamaIndex Semantic SQL"),
        "NetworkDiagnostics": ("Network Diagnostics", "Google ADK + A2A"),
        "BillingResolution": ("Billing Resolution", "Google ADK + A2A"),
        "CustomerCommsCrew": ("Customer Communications", "CrewAI"),
    }
    return mapping.get(worker, (worker, "Specialist Agent"))


def trace_outputs(trace: list) -> list[str]:
    outputs = []
    for item in trace or []:
        output = item.get("output", "")
        if isinstance(output, str) and output.strip():
            outputs.append(output)
        elif output:
            outputs.append(str(output))
    return outputs


def extract_evidence(trace: list, context: str) -> dict:
    """Extract only explicit evidence-like values from returned agent text."""
    text = "\n".join(trace_outputs(trace)) + "\n" + (context or "")
    evidence = {}

    patterns = [
        ("Customer", r"\bCUST-\d+\b"),
        ("Charge", r"\bCHG-\d+\b"),
        ("Incident", r"\bINC-\d+\b"),
        ("Tower", r"\b[A-Z]{2}-\d{3}\b"),
        ("Credit", r"(?:credit\s*#|credit_id[=: ]+)(\d+)"),
        ("Packet loss", r"packet loss(?:\s*[:=]| of )\s*([0-9]+(?:\.[0-9]+)?)\s*%?"),
        ("Latency", r"latency(?:\s*[:=]| of )\s*([0-9]+(?:\.[0-9]+)?)\s*ms"),
        ("Downlink", r"downlink(?: throughput)?(?:\s*[:=]| of )\s*([0-9]+(?:\.[0-9]+)?)\s*Mbps"),
        ("Approval state", r"\b(PENDING_APPROVAL|APPLIED|REJECTED)\b"),
    ]

    import re as _re
    for label, pattern in patterns:
        match = _re.search(pattern, text, flags=_re.IGNORECASE)
        if match:
            value = match.group(0)
            if label in {"Packet loss", "Latency", "Downlink"} and match.lastindex:
                value = match.group(1)
                if label == "Packet loss":
                    value += "%"
                elif label == "Latency":
                    value += " ms"
                else:
                    value += " Mbps"
            evidence[label] = value
    return evidence


def explain_case(query: str, result: dict) -> str:
    trace = result.get("execution_trace", []) or []
    if not trace:
        return "No specialist execution trace is available for this case."

    workers = [item.get("worker", "Unknown Worker") for item in trace]
    names = [worker_display_name(w)[0] for w in workers]
    intent = infer_intent(query)
    evidence = extract_evidence(trace, result.get("agent_context", ""))
    evidence_text = ", ".join(f"{k}: {v}" for k, v in evidence.items())

    parts = [
        f"The request was classified as **{intent}**.",
        f"The workflow executed {len(names)} specialist stage(s): **"
        + " → ".join(names)
        + "**.",
    ]
    if evidence_text:
        parts.append(
            "The explanation is grounded in explicit returned evidence: "
            + evidence_text
            + "."
        )
    parts.append(
        "The final customer response was produced from the specialist context "
        "available to the workflow; no hidden chain-of-thought is exposed."
    )
    return "\n\n".join(parts)


def render_mission_control(trace: list) -> None:
    st.markdown("### 🧠 Agent Mission Control")
    st.caption(
        "Live view of the specialist path actually recorded by the supervisor."
    )

    if not trace:
        st.info("No specialist stages were recorded for this case.")
        return

    cols = st.columns(len(trace))
    for index, item in enumerate(trace):
        worker = item.get("worker", "Unknown Worker")
        name, tech = worker_display_name(worker)
        with cols[index]:
            st.markdown(
                f"""
                <div class="agent-node">
                    <div class="case-label">Step {index + 1}</div>
                    <div class="name">✓ {name}</div>
                    <div class="tech">{tech}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if index < len(trace) - 1:
            pass

    st.markdown(
        "<div style='text-align:center;opacity:.55;padding:.35rem'>↓</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="agent-node">
            <div class="case-label">Final Stage</div>
            <div class="name">💬 Customer Response</div>
            <div class="tech">CrewAI-reviewed communication</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_case_dna(query: str, result: dict) -> None:
    trace = result.get("execution_trace", []) or []
    workers = [item.get("worker", "Unknown") for item in trace]
    domains = []
    for worker in workers:
        if "Billing" in worker:
            domains.append("Billing")
        elif "Network" in worker:
            domains.append("Network")
        elif "Policy" in worker:
            domains.append("Policy")
        elif "Comms" in worker:
            domains.append("Communications")

    evidence = extract_evidence(trace, result.get("agent_context", ""))
    st.markdown("### 🧬 Case DNA")
    cols = st.columns(5)
    values = [
        ("Intent", infer_intent(query)),
        ("Agents", str(len(workers))),
        ("Domains", " → ".join(dict.fromkeys(domains)) or "Operations"),
        ("Evidence", str(len(evidence))),
        ("HITL", "Triggered" if "PENDING_APPROVAL" in result.get("agent_context", "") else "Not triggered"),
    ]
    for col, (label, value) in zip(cols, values):
        with col:
            st.markdown(
                f'<div class="section-card"><div class="case-label">{label}</div>'
                f'<div class="case-value">{value}</div></div>',
                unsafe_allow_html=True,
            )


def render_evidence(trace: list, context: str) -> None:
    st.markdown("### 🔎 Grounded Evidence")
    evidence = extract_evidence(trace, context)

    if not evidence:
        st.info("No compact evidence fields could be safely extracted. See the detailed specialist output below.")
        return

    cols = st.columns(min(4, len(evidence)))
    for col, (label, value) in zip(cols, evidence.items()):
        with col:
            st.metric(label, value)


def render_timeline(trace: list) -> None:
    st.markdown("### 🕐 Resolution Timeline")
    if not trace:
        st.info("No workflow stages recorded.")
        return

    for index, item in enumerate(trace, 1):
        worker = item.get("worker", "Unknown Worker")
        name, tech = worker_display_name(worker)
        st.markdown(
            f"""
            <div class="timeline-step">
                <div class="timeline-num">STEP {index}</div>
                <strong>{name}</strong><br>
                <span style="opacity:.7">{tech} • completed</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="timeline-step">
            <div class="timeline-num">FINAL</div>
            <strong>Customer response generated</strong><br>
            <span style="opacity:.7">CrewAI communication layer</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# UI
# =========================================================

inject_styles()

database_ready = check_database()
vector_ready = check_vector_index()
network_adk_ready = check_port(8001)
billing_adk_ready = check_port(8002)
pending_credits = get_pending_billing_credits()

st.markdown(
    """
    <div class="hero">
        <div class="hero-title">📡 Prodapt AI Operations Center</div>
        <div class="hero-sub">
            Agentic telecom resolution console — investigate, ground, decide,
            govern, and communicate.
        </div>
        <span class="pill">LangGraph</span>
        <span class="pill">LlamaIndex</span>
        <span class="pill">Google ADK + A2A</span>
        <span class="pill">CrewAI</span>
        <span class="pill">Human-in-the-loop</span>
    </div>
    """,
    unsafe_allow_html=True,
)

health_items = [
    ("Database", database_ready, "Online" if database_ready else "Offline"),
    ("Policy RAG", vector_ready, "Online" if vector_ready else "Offline"),
    ("Network A2A", network_adk_ready, "Online" if network_adk_ready else "Offline"),
    ("Billing A2A", billing_adk_ready, "Online" if billing_adk_ready else "Offline"),
    (
        "HITL Queue",
        len(pending_credits) == 0,
        "Clear" if len(pending_credits) == 0 else f"{len(pending_credits)} pending",
    ),
]

health_cols = st.columns(5, gap="small")
for col, (name, ready, state) in zip(health_cols, health_items):
    state_class = "ok" if ready else "warn"
    dot_class = "" if ready else "warn"
    with col:
        st.markdown(
            f"""
            <div class=\"health-card {state_class}\">
                <div class=\"health-name\">{name}</div>
                <div class=\"health-state\">
                    <span class=\"health-dot {dot_class}\"></span>
                    <span>{state}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with st.sidebar:
    st.header("⚙️ Operations Console")
    st.subheader("System Status")
    if st.button("↻ Refresh status", use_container_width=True):
        check_port.clear()
        check_database.clear()
        check_vector_index.clear()
        get_pending_billing_credits.clear()
        st.rerun()
    show_status("Operational Database", database_ready)
    show_status("Policy Vector Index", vector_ready)
    show_status("Network Diagnostics A2A :8001", network_adk_ready)
    show_status("Billing Resolution A2A :8002", billing_adk_ready)

    if not network_adk_ready or not billing_adk_ready:
        st.warning(
            "One or more ADK services are offline. Start the Network Diagnostics "
            "and Billing Resolution A2A services before testing those workflows."
        )

    st.divider()
    st.subheader("Framework Map")
    st.markdown(
        """
        **LangGraph**  
        Supervisor / orchestration

        **LlamaIndex**  
        Policy Document RAG + Network Semantic SQL

        **Google ADK + A2A**  
        Network Diagnostics + Billing Resolution

        **CrewAI**  
        Customer communications / review

        **HITL**  
        Human approval for governed billing actions
        """
    )

    st.divider()
    st.subheader("Governance")
    st.success("✓ SQLite source of truth")
    st.success("✓ Policy-grounded workflow")
    st.success("✓ Specialist execution trace")
    st.success("✓ Human approval controls")

    if pending_credits:
        st.warning(f"⚠ {len(pending_credits)} billing approval(s) pending.")
    else:
        st.success("✓ No pending billing approvals.")

# ---------------------------------------------------------
# Demo scenarios
# ---------------------------------------------------------

st.subheader("🎬 Demo Scenarios")
demo_options = {
    "Choose a scenario": "",
    "💳 Duplicate billing investigation": (
        "CUST-10002 was charged twice for Unlimited Plus. "
        "Investigate the duplicate charge and determine the appropriate resolution."
    ),
    "📡 5G connectivity investigation": (
        "Customer reports intermittent 5G session drops at Austin Riverside. "
        "Investigate the network condition and explain the evidence."
    ),
    "🚨 SLA / outage eligibility": (
        "Which region has the most CRITICAL outages, and could affected customers qualify for SLA credits?"
    ),
    "🌍 Roaming policy": (
        "What is the policy for roaming while travelling internationally?"
    ),
    "🛠 Device upgrade policy": (
        "What is the device upgrade eligibility policy?"
    ),
}
selected_demo = st.selectbox("Load a ready-to-demo case", list(demo_options.keys()))
if st.button("Load Scenario", use_container_width=True):
    if demo_options[selected_demo]:
        st.session_state["draft_query"] = demo_options[selected_demo]
        st.rerun()

# ---------------------------------------------------------
# Main query interface
# ---------------------------------------------------------

st.subheader("🧭 Ask the Operations Center")
user_query = st.text_area(
    "Customer or operations inquiry",
    value=st.session_state.get("draft_query", ""),
    placeholder=(
        "Ask a question in plain English. For example:\n\n"
        "Which region has the most CRITICAL outages, and could affected "
        "customers qualify for SLA credits?"
    ),
    height=140,
)

run_clicked = st.button(
    "🚀 Run Agent Workflow",
    type="primary",
    use_container_width=True,
)

if run_clicked:
    if not user_query.strip():
        st.warning("Please enter a question.")
    else:
        import time
        started = time.perf_counter()
        with st.spinner("LangGraph is coordinating specialist agents..."):
            try:
                from supervisor.runner import run_supervisor
                result = run_supervisor(user_query.strip())
                elapsed = time.perf_counter() - started
                st.session_state["last_result"] = result
                st.session_state["last_query"] = user_query.strip()
                st.session_state["last_elapsed"] = elapsed
                st.session_state["draft_query"] = user_query.strip()
                st.rerun()
            except Exception as exc:
                st.error(f"Workflow failed: {exc}")

# ---------------------------------------------------------
# Human approval panel
# ---------------------------------------------------------

st.divider()
st.subheader("🛡️ Human Approval Console")
# Reuse the cached pending-credit result from the health section above.

if not pending_credits:
    st.success("✓ No billing credits currently require human approval.")
else:
    st.warning(
        "These financial actions exceeded the automatic approval threshold "
        "and require an explicit human decision."
    )
    for credit in pending_credits:
        credit_id = credit["credit_id"]
        customer_id = credit["customer_id"]
        amount = float(credit["amount"])
        reason = credit["reason"]
        related_charge = credit["related_charge_id"]

        with st.container(border=True):
            top = st.columns([2, 2, 2])
            with top[0]:
                st.markdown(f"**Credit #{credit_id}**")
                st.write(f"Customer: `{customer_id}`")
            with top[1]:
                st.metric("Requested", f"${amount:,.2f}")
                st.write(f"Charge: `{related_charge or 'N/A'}`")
            with top[2]:
                st.markdown("**Status**")
                st.warning("PENDING APPROVAL")

            st.write(f"**Reason:** {reason}")
            st.caption("Human decision → APPLIED or REJECTED")

            approve_col, reject_col = st.columns(2)
            with approve_col:
                if st.button(
                    "✓ Approve Credit",
                    key=f"approve_{credit_id}",
                    type="primary",
                    use_container_width=True,
                ):
                    success, message = approve_billing_credit(credit_id)
                    if success:
                        st.success(message)
                        get_pending_billing_credits.clear()
                        st.rerun()
                    else:
                        st.error(message)
            with reject_col:
                if st.button(
                    "✕ Reject Credit",
                    key=f"reject_{credit_id}",
                    use_container_width=True,
                ):
                    success, message = reject_billing_credit(credit_id)
                    if success:
                        st.info(message)
                        get_pending_billing_credits.clear()
                        st.rerun()
                    else:
                        st.error(message)

# ---------------------------------------------------------
# Results
# ---------------------------------------------------------

if "last_result" in st.session_state:
    result = st.session_state["last_result"]
    query = st.session_state.get("last_query", "")
    trace = result.get("execution_trace", []) or []
    context = result.get("agent_context", "") or ""
    elapsed = st.session_state.get("last_elapsed")

    st.divider()
    st.subheader("📊 Case Intelligence")

    meta_cols = st.columns(4)
    with meta_cols[0]:
        st.metric("Intent", infer_intent(query))
    with meta_cols[1]:
        st.metric("Specialist stages", len(trace))
    with meta_cols[2]:
        st.metric("Evidence fields", len(extract_evidence(trace, context)))
    with meta_cols[3]:
        st.metric("Workflow time", f"{elapsed:.1f}s" if elapsed is not None else "—")

    render_case_dna(query, result)
    render_mission_control(trace)
    render_timeline(trace)
    render_evidence(trace, context)

    st.divider()
    response_col, explain_col = st.columns([3, 1])

    with response_col:
        st.subheader("💬 Final Customer Response")
        final_response = result.get(
            "final_response",
            "No final response was generated.",
        )
        st.success(final_response)

    with explain_col:
        st.subheader("🔍 Resolution")
        if st.button(
            "Explain this case",
            key="explain_case",
            use_container_width=True,
        ):
            st.session_state["show_explanation"] = True

    if st.session_state.get("show_explanation"):
        with st.container(border=True):
            st.markdown("#### Why this resolution?")
            st.markdown(explain_case(query, result))

    st.subheader("🔎 Detailed Agent Execution Trace")
    if trace:
        st.caption(
            "Specialist outputs below are the actual workflow results. "
            "The visual layer does not invent additional agent steps."
        )
        for number, item in enumerate(trace, start=1):
            worker = item.get("worker", "Unknown Worker")
            output = item.get("output", "")
            name, tech = worker_display_name(worker)
            with st.expander(f"{number}. {name}  ·  {tech}", expanded=True):
                st.write(output)
    else:
        st.info("No specialist workers were executed.")

    with st.expander("📚 Combined Specialist Context"):
        st.text(context)

    with st.expander("🛡️ Trust & Governance"):
        st.markdown(
            """
            - **Operational source of truth:** SQLite-backed telecom data.
            - **Policy grounding:** persisted document vector index.
            - **Orchestration:** LangGraph supervisor and recorded execution trace.
            - **Specialist services:** Google ADK exposed through A2A.
            - **Customer communication:** CrewAI review layer.
            - **Financial governance:** credits requiring human approval remain
              `PENDING_APPROVAL` until explicitly approved or rejected.
            - **Transparency:** this panel exposes returned evidence and workflow
              stages, not hidden model chain-of-thought.
            """
        )

# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------

st.divider()
st.caption(
    "Prodapt Capstone 2 • Multi-Agent Telecom Operations Assistant • "
    "Agentic Operations Command Center"
)
