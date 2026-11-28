"""Sample agent recordings that ship inside the wheel, for ``agentest demo <example>``.

``refill/`` holds a plain-Python refill assistant in two builds, as the standard files the judge reads (A2A AgentCard,
MCP tools/list, OTLP traces). They are byte-for-byte copies of ``examples/agnostic_demo/agents/`` (tests/test_demo_refill.py
keeps them identical). Nothing here is read by a check: the checks see them like any other agent directory.
"""
