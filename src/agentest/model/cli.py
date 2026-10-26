"""``agentest model ...`` sub-commands."""

from __future__ import annotations

import json
from pathlib import Path

from agentest.model import runner
from agentest.model.generator import generate
from agentest.model.profile import load_all
from agentest.model.trace import validate


def cmd_model(args) -> int:
    profs = load_all(Path(args.profiles) if args.profiles else None)
    if args.agent:
        if args.agent not in profs:
            print(f"no profile for {args.agent!r}; known: {', '.join(profs)}")
            return 2
        profs = {args.agent: profs[args.agent]}
    if args.action == "validate":
        n, errs = 0, []
        for a, p in profs.items():
            for e in runner.traces(p):
                n += 1
                errs += [f"{a}/{e.probe}: {x}" for x in validate(e.to_dict())]
        print(f"{len(profs)} profiles, {n} episodes converted, {len(errs)} schema errors")
        print("\n".join(errs[:20]))
        return 1 if errs else 0
    if args.action == "convert":
        for e in runner.traces(next(iter(profs.values()))):
            print(json.dumps(e.to_dict(), ensure_ascii=False, default=str))
        return 0
    if args.action == "generate":
        p = next(iter(profs.values()))
        seeds = args.seed or [e.input for e in runner.traces(p) if e.probe in p.role("canonical")][:1]
        for c in generate(p, seeds):
            print(json.dumps(c, ensure_ascii=False))
        return 0
    gen = runner.run_all(profs)
    if args.action == "run":
        if args.json:
            Path(args.json).write_text(json.dumps(runner.to_json(gen), indent=1))
        text = runner.summary_md(gen)
        if args.md:
            Path(args.md).write_text(text + "\n")
        else:
            print(text)
        return 0
    par = runner.parity(gen, runner.v1_results())
    if args.json:
        Path(args.json).write_text(json.dumps(par, indent=1))
    print(json.dumps(par["tally"]), f"comparable={par['comparable']}")
    return 0
