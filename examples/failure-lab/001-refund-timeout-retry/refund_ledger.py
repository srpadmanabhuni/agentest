"""The refund service of Failure Lab 001: an in-memory ledger that needs no SDK and no network.

It stands in for a payments API. A refund exists from the moment the request arrives; only the first answer is
late (``slow_replies``), which is the case a client timeout cannot tell apart from a failure. When a request
carries an idempotency key the ledger has seen, it returns the refund it already made and marks it
``"replayed": True`` instead of creating another.
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass, field

SLOW_REPLY_S = 0.6  # the refund service's first reply arrives after this long


@dataclass
class RefundLedger:
    """Refunds that were actually created. The first ``slow_replies`` answers arrive late, after the write is done."""

    slow_replies: int = 1
    rows: list[dict] = field(default_factory=list)
    keys: dict[str, dict] = field(default_factory=dict)
    requests: int = 0

    async def create(self, order_id: str, amount: float, reason: str, idempotency_key: str | None = None) -> dict:
        self.requests += 1
        if idempotency_key and idempotency_key in self.keys:
            row = dict(self.keys[idempotency_key], replayed=True)
        else:
            row = {"refund_ticket": f"RF-{1001 + len(self.rows)}", "order_id": order_id, "amount": amount, "reason": reason}
            self.rows.append(dict(row, request=self.requests))  # the refund exists from here on
            if idempotency_key:
                self.keys[idempotency_key] = row
        if self.slow_replies > 0:
            self.slow_replies -= 1
            await asyncio.sleep(SLOW_REPLY_S)  # only the answer is late; the caller may stop waiting here
        return {**row, "status": "approved_pending_processing"}


def refund_key(order_id: str, amount: float) -> str:
    """The simple key the recorded fixed run uses: derived from the arguments, so it cannot tell a retry from a repeat."""
    return "refund-" + hashlib.sha256(f"{order_id}|{amount:.2f}".encode()).hexdigest()[:16]
