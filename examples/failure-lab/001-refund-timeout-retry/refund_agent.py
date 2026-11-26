"""The refund agent from the OpenAI Agents SDK example ``examples/basic/stream_ws.py`` (v0.26.0), run offline.

What is kept from the example: the two agents, their instructions, the three tools and their names and
argument lists, ``needs_approval=True`` on ``submit_refund``, and auto-approval (the example's
``EXAMPLES_INTERACTIVE_MODE=auto`` path approves every prompt).

What this lab adds, so the run is repeatable without an API key:

* ``ScriptedModel`` stands in for the model. It makes the choices a model makes in this workflow, in a fixed
  order: look up the order, ask the policy specialist, submit the refund, and, when the tool result says the
  call timed out, call ``submit_refund`` again with the same arguments. Whether a live model retries is
  model-dependent; the script fixes that choice so the tool side can be studied.
* ``RefundLedger`` (in ``refund_ledger.py``, which needs no SDK) is an in-memory refund service. It creates the refund as soon as the request arrives,
  then its first answer is slow. That is the case a client timeout cannot tell apart from a failure.
* ``submit_refund`` gets the SDK's per-tool ``timeout`` (a documented option of the ``tool`` decorator) and is
  ``async``, because the SDK supports that timeout only on async tools. The example sets no timeout; a refund
  call to a real payments service usually has one.

``VARIANT = "original"`` keeps the example's tool contract (no idempotency key).
``VARIANT = "fixed"`` sends an idempotency key built from the order, so a retried request returns the
refund that already exists instead of creating a second one.
"""

from __future__ import annotations

import ast
import asyncio
import json
from typing import Any

from agents.decorators import tool
from agents.models.interface import Model
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText
from refund_ledger import RefundLedger, refund_key

from agents import Agent, ModelResponse, ModelSettings, Runner, Usage

PROMPT = (
    "Customer wants a refund for order ORD-1001 because the mouse arrived "
    "damaged. Please check the order, ask the refund policy specialist, and "
    "if it is eligible submit the refund. Reply with only the refund ticket."
)
TOOL_TIMEOUT_S = 0.2  # the SDK stops waiting for submit_refund after this long


# ---------------------------------------------------------------- the refund service: see refund_ledger.py
LEDGER = RefundLedger()
VARIANT = "original"


# ---------------------------------------------------------------- tools: names, arguments and docstrings as in the example
@tool
def lookup_order(order_id: str) -> dict[str, Any]:
    """Return deterministic order data for the demo."""
    orders = {
        "ORD-1001": {"order_id": "ORD-1001", "status": "delivered", "delivered_days_ago": 3, "amount": 49.99, "currency": "USD", "item": "Wireless Mouse"},
        "ORD-2002": {"order_id": "ORD-2002", "status": "delivered", "delivered_days_ago": 12, "amount": 129.0, "currency": "USD", "item": "Keyboard"},
    }
    return orders.get(order_id, {"order_id": order_id, "status": "unknown", "delivered_days_ago": 999, "amount": 0.0, "currency": "USD", "item": "unknown"})


@tool(needs_approval=True, timeout=TOOL_TIMEOUT_S)
async def submit_refund(order_id: str, amount: float, reason: str) -> dict[str, Any]:
    """Create a refund request. This tool requires approval."""
    key = refund_key(order_id, amount) if VARIANT == "fixed" else None
    return await LEDGER.create(order_id, amount, reason, idempotency_key=key)


# ---------------------------------------------------------------- scripted model
def _parse(text: str) -> dict:
    """Tool outputs are the str() of the returned dict."""
    try:
        out = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return {}
    return out if isinstance(out, dict) else {}


def _text(item: Any) -> str:
    return item if isinstance(item, str) else json.dumps(item, default=str)


class ScriptedModel(Model):
    """Replays a model's decisions for this workflow from what is already in the conversation."""

    def __init__(self, role: str) -> None:
        self.role = role
        self.n = 0

    def _reply(self, items: list[dict]) -> list[Any]:
        self.n += 1
        if self.role == "policy":
            return [_message("Eligible: delivered 3 days ago, inside the 7-day full-refund window.")]
        calls = {i["call_id"]: i for i in items if i.get("type") == "function_call"}
        outs = [(calls.get(i["call_id"], {}).get("name"), _text(i.get("output"))) for i in items if i.get("type") == "function_call_output"]
        done = [name for name, _ in outs]
        if "lookup_order" not in done:
            return [_call("lookup_order", {"order_id": "ORD-1001"}, self.n)]
        if "refund_policy_specialist" not in done:
            return [_call("refund_policy_specialist", {"input": "Order ORD-1001, Wireless Mouse, delivered 3 days ago, arrived damaged. Eligible?"}, self.n)]
        refunds = [out for name, out in outs if name == "submit_refund"]
        if not refunds or "timed out" in refunds[-1]:
            # first attempt, or the last attempt timed out: try the same request again
            return [_call("submit_refund", {"order_id": "ORD-1001", "amount": 49.99, "reason": "Item arrived damaged"}, self.n)]
        ticket = _parse(refunds[-1]).get("refund_ticket", "")
        return [_message(ticket or refunds[-1])]

    async def get_response(self, system_instructions, input, model_settings, tools, output_schema, handoffs, tracing, *, previous_response_id=None, conversation_id=None, prompt=None):  # noqa: A002
        items = [input] if isinstance(input, str) else list(input)
        items = [i if isinstance(i, dict) else getattr(i, "model_dump", lambda: {})() for i in items]
        return ModelResponse(output=self._reply(items), usage=Usage(), response_id=None)

    def stream_response(self, *args, **kwargs):  # pragma: no cover - the lab uses Runner.run
        raise NotImplementedError


def _call(name: str, args: dict, n: int) -> ResponseFunctionToolCall:
    return ResponseFunctionToolCall(type="function_call", name=name, arguments=json.dumps(args), call_id=f"call_{n}_{name}", id=f"fc_{n}", status="completed")


def _message(text: str) -> ResponseOutputMessage:
    return ResponseOutputMessage(type="message", id="msg_final", role="assistant", status="completed", content=[ResponseOutputText(type="output_text", text=text, annotations=[])])


# ---------------------------------------------------------------- agents: instructions as in the example
def build_agents() -> Agent:
    policy_agent = Agent(
        name="RefundPolicySpecialist",
        instructions=(
            "You are a refund policy specialist. The policy is simple: orders delivered "
            "within 7 days are eligible for a full refund, and older delivered orders "
            "are not. Return a short answer with eligibility and a one-line reason."
        ),
        model=ScriptedModel("policy"),
        model_settings=ModelSettings(max_tokens=120),
    )
    return Agent(
        name="SupportAgent",
        instructions=(
            "You are a support agent. For refund requests, do this in order: "
            "1) call lookup_order, 2) call refund_policy_specialist, 3) if the user "
            "asked to proceed and the order is eligible, call submit_refund. "
            "When asked for only the refund ticket, return only the ticket token "
            "(for example RF-1001)."
        ),
        tools=[
            lookup_order,
            policy_agent.as_tool(tool_name="refund_policy_specialist", tool_description="Check refund eligibility and explain the policy decision."),
            submit_refund,
        ],
        model=ScriptedModel("support"),
        model_settings=ModelSettings(max_tokens=200),
    )


async def _run() -> dict:
    agent = build_agents()
    approvals: list[dict] = []
    result = await Runner.run(agent, PROMPT)
    while result.interruptions:  # the example's auto mode approves every prompt
        state = result.to_state()
        for it in result.interruptions:
            approvals.append({"tool": it.name, "arguments": it.arguments, "granted": True})
            state.approve(it)
        result = await Runner.run(agent, state)
    return {"items": result.to_input_list(), "answer": str(result.final_output), "approvals": approvals}


def run_scenario(variant: str = "original") -> dict:
    """Run the workflow once with a fresh refund service. Returns the items, answer, approvals and refunds created."""
    global LEDGER, VARIANT
    if variant not in ("original", "fixed"):
        raise ValueError("variant must be 'original' or 'fixed'")
    LEDGER, VARIANT = RefundLedger(), variant
    out = asyncio.run(_run())
    out["refunds"] = [dict(r) for r in LEDGER.rows]
    out["variant"] = variant
    return out
