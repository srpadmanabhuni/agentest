"""Optional framework converters: turn a framework's in-memory or exported run data into an agentest native record.

Converters are pure data mapping. They never import a framework (objects are read by duck typing), add no runtime
dependency, and compute no verdicts. Their output feeds ``agentest std import`` (see ``standards/importers.py``),
which writes OpenTelemetry GenAI spans; every check then runs on those spans as for any other agent.
"""
