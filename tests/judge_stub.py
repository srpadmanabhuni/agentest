"""A deterministic stand-in judge for unit tests: answers scoring-guide questions with a function of (guide, payload).
It exercises the judge interface (agentest.standards.judge) without a model; the verdict records its identity."""
from __future__ import annotations

from contextlib import contextmanager

from agentest.standards import judge


class StubJudge:
    url = "stub"
    offline = False
    model = "unit-test-stub"

    def __init__(self, answer):
        self.answer = answer
        self.stats = {"calls": 0, "cache_hits": 0, "misses": 0, "invalid": 0, "errors": 0}

    def ask(self, gids, payload):
        self.stats["calls"] += 1
        return {g: self.answer(g, payload) for g in gids}

    def identity(self):
        return {"model": self.model, "endpoint": "stub", "temperature": 0, "seed": judge.SEED, "prompt_version": judge.PROMPT_VERSION}

    def label(self):
        return self.model


@contextmanager
def stub_judge(answer):
    prev = (judge._ACTIVE, judge._CONFIGURED)
    judge._ACTIVE, judge._CONFIGURED = StubJudge(answer), True
    try:
        yield judge._ACTIVE
    finally:
        judge._ACTIVE, judge._CONFIGURED = prev


@contextmanager
def no_judge():
    prev = (judge._ACTIVE, judge._CONFIGURED)
    judge._ACTIVE, judge._CONFIGURED = None, True
    try:
        yield
    finally:
        judge._ACTIVE, judge._CONFIGURED = prev
