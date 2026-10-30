# Framework converters

The converters turn a framework's own run output into one native record for `agentest std import`. They read plain
objects and dicts, and they never import the framework, so agentest keeps pyyaml as its only runtime dependency.

## LangChain / LangGraph: `agentest.standards.converters.langchain`

| You have | Call |
|---|---|
| A message list (objects, `messages_to_dict`, `dumpd`, or plain dicts) | `from_messages(msgs)` |
| `astream_events(version="v2")` events | `from_stream_events(events)` |
| A graph state `{"messages": [...]}`, `graph.get_state(config)` (a `StateSnapshot`), a checkpoint, or a `CheckpointTuple` from a checkpointer | `from_state(obj, key="messages")` |
| `graph.get_state_history(config)` | `from_state_history(history)` (uses the newest checkpoint that has messages) |

```python
from agentest.standards.converters import langchain as lc
state = graph.invoke({"messages": [("user", "Find item 42")]}, config)
rec = lc.to_record(lc.from_state(state), agent="my_agent", probe="find-42")
# write rec as one JSON line, then: agentest std import run.jsonl --dialect langgraph_msgs
```

`from_state` drops messages that share an `id`, and it raises `ValueError` when there is no message list under `key`.
System messages are dropped. Any text the model writes beside its tool calls is kept as each call's stated reason.

## OpenAI Agents SDK: `agentest.standards.converters.openai_agents`

```python
from agentest.standards.converters import openai_agents as oa
result = await Runner.run(agent, "Refund order 7")
rec = oa.to_record(oa.from_items(result.new_items), agent="my_agent", input="Refund order 7",
                   final_output=result.final_output)
# or: oa.from_items(result.to_input_list(), agent="my_agent")
# then: agentest std import run.jsonl --dialect openai_agents
```

Tool calls, tool outputs, handoffs (source and target agent) and assistant messages are all kept. Tool arguments that
are not valid JSON are kept as `{"input": "<raw text>"}`. A non-string `final_output` is stored as JSON.
