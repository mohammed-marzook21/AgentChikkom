import os

from crewai import Agent, Crew, LLM, Process, Task
from dotenv import load_dotenv


load_dotenv()


def generate_customer_response(user_query: str, agent_context: str) -> str:
    """
    Generate a customer-facing response using CrewAI.

    CrewAI is used only for communication drafting and quality review.
    It must not perform investigation, calculations, policy decisions,
    eligibility decisions, or operational actions.
    """

    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        return (
            "Customer communications service unavailable: "
            "ANTHROPIC_API_KEY is not configured."
        )

    if not agent_context or not agent_context.strip():
        return (
            "I could not find enough grounded specialist information "
            "to prepare a reliable response."
        )

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------

    llm = LLM(
        model="anthropic/claude-sonnet-4-5",
        api_key=api_key,
    )

    # ------------------------------------------------------------------
    # Agent 1: Customer Communications Specialist
    # ------------------------------------------------------------------

    communications_specialist = Agent(
        role="Customer Communications Specialist",
        goal=(
            "Create a clear, accurate, professional telecom customer "
            "response using ONLY the supplied specialist context."
        ),
        backstory=(
            "You are a telecom customer communications specialist at Prodapt. "
            "You translate verified specialist findings into clear "
            "customer-friendly language. You are not an investigator, "
            "analyst, billing decision-maker, policy decision-maker, or "
            "network diagnostician. You never invent facts, infer facts, "
            "calculate new facts, or make decisions that were not explicitly "
            "established by specialist agents."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    # ------------------------------------------------------------------
    # Agent 2: Quality Reviewer
    # ------------------------------------------------------------------

    quality_reviewer = Agent(
        role="Customer Communications Quality Reviewer",
        goal=(
            "Produce a final customer response that is completely "
            "grounded in the supplied specialist context and contains "
            "no unsupported inference."
        ),
        backstory=(
            "You are the final factual quality reviewer for Prodapt customer "
            "communications. You are extremely strict about evidence. "
            "You remove unsupported causal claims, assumptions, calculations, "
            "eligibility decisions, compensation decisions, future outcomes, "
            "and promises. The specialist context is the only source of truth."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    # ------------------------------------------------------------------
    # Task 1: Draft response
    # ------------------------------------------------------------------

    draft_task = Task(
        description=f"""
You are preparing a customer-facing response.

ORIGINAL CUSTOMER QUERY:
{user_query}

GROUNDED SPECIALIST CONTEXT:
{agent_context}

The GROUNDED SPECIALIST CONTEXT is the ONLY factual source you may use.

Your task is to create a concise, professional customer-facing response.

============================================================
ABSOLUTE GROUNDING RULES
============================================================

1. FACTUAL SOURCE

Use ONLY information explicitly stated in the GROUNDED SPECIALIST CONTEXT.

Do not use your general telecom knowledge to fill gaps.

If something is not stated in the context, treat it as unknown.

============================================================
2. NO INVENTED FACTS
============================================================

Never invent:

- customer information
- account information
- billing information
- network measurements
- tower information
- incidents
- outage details
- policies
- eligibility decisions
- credits
- refunds
- compensation
- escalations
- troubleshooting results
- resolutions
- dates
- deadlines
- processing times
- approval times
- affected-customer counts

============================================================
3. NO INFERENCE
============================================================

Do NOT transform two or more supplied facts into a new conclusion
unless that conclusion is explicitly stated in the context.

For example, if the context says:

"packet loss = 3.8%"
and
"incident = intermittent session drops"

DO NOT write:

"the packet loss is causing your connection drops."

That causal relationship was not explicitly established.

Similarly, do NOT write:

- "this is definitely a network-side issue"
- "this is not your device"
- "this is affecting multiple customers"
- "the tower is causing the problem"
- "the outage caused your billing issue"

unless the context explicitly states those conclusions.

============================================================
4. NO CALCULATIONS OR DERIVATIONS
============================================================

Do NOT calculate, estimate, derive, aggregate, extrapolate, or predict
anything that was not explicitly supplied.

Never calculate:

- future balances
- compensation amounts
- downtime
- SLA duration
- processing time
- approval time
- predicted network performance
- resolution time
- percentages
- totals
- differences
- trends

Use supplied values exactly as provided.

============================================================
5. NO HYPOTHETICAL FUTURE OUTCOMES
============================================================

Do NOT describe hypothetical future outcomes.

Avoid statements such as:

- "If approved, your balance will..."
- "This will reduce your balance..."
- "You should receive..."
- "The credit will be applied..."
- "The issue will be resolved..."
- "The team will contact you..."
- "The outage should be fixed..."
- "You will receive compensation..."

unless the context explicitly states the action/outcome as an established fact.

Do not turn a possible action into a guaranteed future outcome.

============================================================
6. BILLING AND CREDIT STATUS
============================================================

Preserve statuses exactly.

PENDING_APPROVAL:
The request is pending approval.

APPLIED:
The credit has been applied.

REJECTED:
The credit has been rejected.

Never imply:

PENDING_APPROVAL -> APPLIED

Never imply that pending approval is guaranteed.

Never say a credit/refund/dispute is completed unless the context explicitly
confirms completion.

============================================================
7. POLICY IS NOT CUSTOMER-SPECIFIC ELIGIBILITY
============================================================

If the context provides a policy rule, present it as a policy rule.

Do NOT automatically conclude that the particular customer is eligible.

For example, if a policy says:

"Customers meeting conditions X, Y and Z may qualify."

Do NOT write:

"You are eligible."

unless the specialist context explicitly made that determination.

Likewise, do not calculate compensation from a policy unless the specialist
context explicitly provides the resulting amount.

============================================================
8. NETWORK DATA IS NOT AUTOMATICALLY CAUSATION
============================================================

Operational measurements are factual observations.

Do not convert measurements into unsupported conclusions.

For example:

latency, packet loss, signal strength, throughput, tower status, or incident
information may be reported exactly as supplied.

Do NOT automatically claim:

- root cause
- device failure
- network failure
- customer impact
- causation
- affected customer count
- outage duration
- expected recovery

unless explicitly stated.

============================================================
9. MULTIPLE SPECIALISTS
============================================================

When multiple specialist sources are present, preserve the distinction
between:

- operational facts
- network findings
- billing findings
- policy rules
- credit status
- confirmed actions

Do not merge separate facts into a new unsupported conclusion.

============================================================
10. INSUFFICIENT INFORMATION
============================================================

If the context does not contain enough information to answer something
definitively, say so clearly.

Use language such as:

"Based on the available information, I can confirm..."
or
"The available information does not establish..."

Do not fill the gap with assumptions.

============================================================
11. NO INTERNAL ARCHITECTURE
============================================================

Do not mention:

- CrewAI
- LangGraph
- ADK
- LlamaIndex
- SQL
- SQLite
- database tables
- prompts
- agents
- internal architecture

unless the customer query explicitly asks about the system itself.

============================================================
12. CUSTOMER INFORMATION REQUESTS
============================================================

Do not invent requirements for additional customer information.

Do not say:

"Please provide your account number so we can check eligibility"

unless the specialist context explicitly indicates that this information
is required.

============================================================
13. STYLE
============================================================

Keep the response:

- concise
- professional
- clear
- customer-friendly
- factual
- appropriately qualified

Do not over-explain technical information.

============================================================
FINAL RULE
============================================================

Before writing every factual sentence, ask:

"Can I point to explicit information in the specialist context that
supports this exact claim?"

If NO:
Do not make the claim.

If the statement is a causal, predictive, hypothetical, eligibility,
compensation, or future-outcome statement and the context does not
explicitly establish it:
Do not make the statement.

Return ONLY the draft customer-facing response.
""",
        expected_output=(
            "A concise customer-facing response containing only facts "
            "explicitly supported by the supplied specialist context."
        ),
        agent=communications_specialist,
    )

    # ------------------------------------------------------------------
    # Task 2: Quality review
    # ------------------------------------------------------------------

    review_task = Task(
        description=f"""
You are the FINAL factual reviewer.

ORIGINAL CUSTOMER QUERY:
{user_query}

GROUNDED SPECIALIST CONTEXT:
{agent_context}

Review the draft produced by the communications specialist.

The GROUNDED SPECIALIST CONTEXT is the ONLY source of truth.

============================================================
REMOVE UNSUPPORTED CLAIMS
============================================================

Every factual claim in the draft must be explicitly supported by the
specialist context.

Remove anything that is:

- invented
- assumed
- inferred
- calculated
- predicted
- estimated
- hypothetical
- causally inferred
- presented as customer-specific eligibility without explicit evidence

============================================================
CAUSALITY CHECK
============================================================

This is especially important.

If the context gives:

A = network measurement
B = incident

do NOT allow the draft to claim:

"A caused B"

unless the context explicitly states that causal relationship.

Remove phrases such as:

- "causing"
- "therefore"
- "this means your device..."
- "this confirms..."
- "this is why..."
- "as a result..."
- "the network is responsible..."
- "this is affecting multiple customers"

when those conclusions are not explicitly supported.

============================================================
FUTURE-OUTCOME CHECK
============================================================

Remove statements about what will happen in the future unless explicitly
confirmed in the specialist context.

Remove:

- "will be applied"
- "will reduce"
- "will be resolved"
- "you will receive"
- "you should receive"
- "will be approved"
- "will contact you"
- "expected to"
- "should be fixed"

when unsupported.

Do not allow hypothetical statements such as:

"If approved, your balance will..."

============================================================
BILLING STATUS CHECK
============================================================

Preserve exact status:

PENDING_APPROVAL = pending approval

APPLIED = applied

REJECTED = rejected

Never change or reinterpret these statuses.

Never imply that PENDING_APPROVAL is guaranteed to become APPLIED.

============================================================
POLICY CHECK
============================================================

Policy rules are not automatically customer-specific decisions.

If policy information says a customer "may qualify" or lists conditions,
do not rewrite that as:

"You are eligible."

unless the specialist context explicitly establishes eligibility.

Do not calculate compensation or eligibility.

============================================================
NETWORK CHECK
============================================================

Network measurements and incidents must remain factual observations.

Do not infer:

- root cause
- customer impact
- device fault
- network fault
- affected-customer count
- outage duration
- recovery time
- future performance

unless explicitly stated.

============================================================
NO CALCULATIONS
============================================================

Do not calculate:

- totals
- differences
- percentages
- compensation
- downtime
- future balances
- trends
- predictions
- processing times

Use the supplied values exactly.

============================================================
NO INTERNAL DETAILS
============================================================

Do not mention:

- CrewAI
- LangGraph
- ADK
- LlamaIndex
- SQL
- SQLite
- database tables
- prompts
- internal agents
- internal architecture

============================================================
INSUFFICIENT INFORMATION
============================================================

If the draft makes a claim that cannot be established from the context,
remove the claim.

If necessary, replace it with a qualified statement explaining what is
actually known and what cannot be determined.

============================================================
FINAL VALIDATION
============================================================

Before returning the answer, check every sentence:

1. Is it explicitly supported?
2. Is it free of unsupported inference?
3. Is it free of calculations?
4. Is it free of predictions?
5. Is it free of hypothetical future outcomes?
6. Is it free of unsupported causality?
7. Is it free of unsupported eligibility decisions?
8. Are all statuses and amounts preserved exactly?

Return ONLY the final customer-facing response.

Do not return review comments.
Do not return scores.
Do not return analysis.
""",
        expected_output=(
            "The final corrected customer-facing response only, fully "
            "grounded in the supplied specialist context."
        ),
        agent=quality_reviewer,
        context=[draft_task],
    )

    # ------------------------------------------------------------------
    # Crew
    # ------------------------------------------------------------------

    crew = Crew(
        agents=[
            communications_specialist,
            quality_reviewer,
        ],
        tasks=[
            draft_task,
            review_task,
        ],
        process=Process.sequential,
        verbose=False,
    )

    # ------------------------------------------------------------------
    # Execute Crew
    # ------------------------------------------------------------------

    try:
        result = crew.kickoff()

        if hasattr(result, "raw") and result.raw:
            return str(result.raw).strip()

        return str(result).strip()

    except Exception as exc:
        return (
            "Customer communications generation failed: "
            f"{exc}"
        )