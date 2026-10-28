"""Optional, deterministic, offline semantic oracle: local embeddings and a local small language model (v3.5).

An *oracle task* is a closed classification question ("is this tool call a break-glass access?") with labelled
prototype texts and an SLM prompt. :class:`Oracle` answers it with

1. **embedding**: cosine similarity of the text to every label's prototypes (nearest prototype per label); the
   margin between the best and the second-best label decides, inside an abstain band nothing is decided;
2. **embedding + SLM**: the embedding is only a recall pre-filter (a clear negative is decided at once); every
   remaining text goes to the local SLM, whose answer must be one of the task's labels (anything else: not assessed);
3. **slm**: the SLM alone.

Determinism: temperature 0, fixed seed (``AGENTEST_ORACLE_SEED``, default 0), greedy decoding, vectors rounded to 6
decimals, and every vector and label cached on disk by ``sha256(backend model id | kind | task@version | text)``. With
``AGENTEST_ORACLE_OFFLINE=1`` only the cache answers (CI replay); a miss raises :class:`OracleUnavailable`, which a
rule reports as ``not-assessed``, never as a keyword fallback.

Backends (``AGENTEST_ORACLE_EMBED`` / ``AGENTEST_ORACLE_SLM``)::

    hash                         built-in character-trigram hashing; no dependency; NOT semantic (plumbing, tests)
    llamacpp:/path/model.gguf    in-process llama.cpp           (extra: pip install "agentest[oracle-llamacpp]")
    onnx:/path/model_dir         ONNX Runtime + tokenizer.json  (extra: pip install "agentest[oracle-onnx]")
    http://127.0.0.1:8080/v1     a local OpenAI-compatible server (llama.cpp server); standard library only.
                                 Loopback only unless AGENTEST_ORACLE_ALLOW_REMOTE=1, so "offline" stays true.
    replay                       no model: answers from the cache only

``AGENTEST_ORACLE_CACHE`` sets the cache file (JSON lines; default ``~/.cache/agentest/oracle.jsonl``). pyyaml stays the
only required dependency: every third-party import here is lazy and optional.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import threading
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from agentest.standards.judge import NotAssessed

SEED = 0
DIGITS = 6
_LOCK = threading.Lock()


class OracleUnavailable(NotAssessed):
    """The oracle cannot answer (no backend configured, offline cache miss, or an answer outside the label set)."""


# ---------------------------------------------------------------- tasks

@dataclass
class Task:
    id: str
    version: int
    labels: dict[str, list[str]]          # label -> prototype texts
    positive: str                         # the label the pre-filter must not miss
    question: str = ""                    # SLM instruction; {labels} and {text} are filled in
    method: str = "embedding+slm"         # embedding | embedding+slm | slm
    abstain: float = 0.02                 # embedding: |margin| below this decides nothing
    reject_margin: float = 0.10           # embedding+slm: negative margin at least this large is decided without the SLM
    query_prefix: str = ""                # e.g. "query: " for E5-style embedding models
    meta: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> Task:
        keys = {k for k in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in keys and k != "meta"}, meta={k: v for k, v in d.items() if k not in keys})


def load_task(path_or_id: str | Path) -> Task:
    """A task from a JSON/YAML file, or a bundled task id (``oracle_tasks/<id>.json``)."""
    p = Path(path_or_id)
    if not p.exists():
        p = Path(__file__).with_name("oracle_tasks") / f"{path_or_id}.json"
    text = p.read_text(encoding="utf-8")
    if p.suffix == ".json":
        return Task.from_dict(json.loads(text))
    import yaml

    return Task.from_dict(yaml.safe_load(text))


# ---------------------------------------------------------------- backends

class Backend:
    model_id = "none"

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise OracleUnavailable(f"backend {self.model_id} has no embeddings")

    def generate(self, prompt: str, labels: list[str]) -> str:
        raise OracleUnavailable(f"backend {self.model_id} has no text generation")


class HashBackend(Backend):
    """Character-trigram feature hashing (blake2b), L2-normalised. Deterministic everywhere; no semantics across
    synonyms or languages. For testing the plumbing and as an honest lower bound."""

    def __init__(self, dim: int = 512) -> None:
        self.dim, self.model_id = dim, f"hash-trigram-{dim}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            v = [0.0] * self.dim
            s = f"  {t.lower()}  "
            for i in range(len(s) - 2):
                h = int.from_bytes(hashlib.blake2b(s[i:i + 3].encode("utf-8"), digest_size=8).digest(), "big")
                v[h % self.dim] += 1.0 if (h >> 63) & 1 else -1.0
            out.append(v)
        return out


class LlamaCppBackend(Backend):
    """In-process llama.cpp through ``llama-cpp-python`` (optional extra ``oracle-llamacpp``)."""

    def __init__(self, path: str, seed: int = SEED, n_threads: int | None = None, n_ctx: int = 2048) -> None:
        self.path, self.seed, self.n_threads, self.n_ctx = path, seed, n_threads, n_ctx
        self.model_id = f"llamacpp:{Path(path).name}"
        self._emb = self._gen = None

    def _llama(self, embedding: bool):
        try:
            from llama_cpp import Llama
        except ImportError as e:  # pragma: no cover - depends on the optional extra
            raise OracleUnavailable('llama.cpp backend needs: pip install "agentest[oracle-llamacpp]"') from e
        return Llama(self.path, embedding=embedding, seed=self.seed, n_ctx=self.n_ctx, n_threads=self.n_threads, verbose=False)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self._emb is None:
            self._emb = self._llama(True)
        return [list(self._emb.embed(t, normalize=True)) for t in texts]

    def generate(self, prompt: str, labels: list[str]) -> str:
        if self._gen is None:
            self._gen = self._llama(False)
        try:
            from llama_cpp import LlamaGrammar
        except ImportError:  # pragma: no cover
            grammar = None
        else:
            grammar = LlamaGrammar.from_string("root ::= " + " | ".join(json.dumps(x) for x in labels), verbose=False)
        r = self._gen.create_chat_completion(messages=[{"role": "user", "content": prompt}], temperature=0.0, top_k=1, top_p=1.0,
                                             seed=self.seed, max_tokens=16, grammar=grammar)
        return str(r["choices"][0]["message"]["content"])


class OnnxBackend(Backend):
    """ONNX Runtime sentence-embedding model: ``model_dir/model.onnx`` + ``tokenizer.json``; mean pooling, L2 norm.
    Optional extra ``oracle-onnx`` (onnxruntime, tokenizers, numpy)."""

    def __init__(self, model_dir: str) -> None:
        self.dir = Path(model_dir)
        self.model_id = f"onnx:{self.dir.name}"
        self._s = self._tok = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            import numpy as np
            import onnxruntime as ort
            from tokenizers import Tokenizer
        except ImportError as e:  # pragma: no cover - depends on the optional extra
            raise OracleUnavailable('ONNX backend needs: pip install "agentest[oracle-onnx]"') from e
        if self._s is None:
            so = ort.SessionOptions()
            so.intra_op_num_threads = so.inter_op_num_threads = 1  # single-threaded: bit-stable float sums
            self._s = ort.InferenceSession(str(self.dir / "model.onnx"), so, providers=["CPUExecutionProvider"])
            self._tok = Tokenizer.from_file(str(self.dir / "tokenizer.json"))
            self._tok.enable_truncation(512)
        out = []
        names = {i.name for i in self._s.get_inputs()}
        for t in texts:
            enc = self._tok.encode(t)
            feed = {"input_ids": np.array([enc.ids], dtype=np.int64), "attention_mask": np.array([enc.attention_mask], dtype=np.int64)}
            if "token_type_ids" in names:
                feed["token_type_ids"] = np.zeros_like(feed["input_ids"])
            h = self._s.run(None, {k: v for k, v in feed.items() if k in names})[0][0]
            m = feed["attention_mask"][0][:, None]
            out.append([float(x) for x in (h * m).sum(0) / max(1, m.sum())])
        return out


class HttpBackend(Backend):
    """A local OpenAI-compatible server (``/embeddings``, ``/chat/completions``); standard library only."""

    def __init__(self, url: str, model: str = "", timeout: float = 600.0, seed: int = SEED) -> None:
        host = urllib.parse.urlparse(url).hostname or ""
        if host not in ("127.0.0.1", "localhost", "::1") and os.environ.get("AGENTEST_ORACLE_ALLOW_REMOTE") != "1":
            raise ValueError(f"oracle endpoint {url} is not on this machine (set AGENTEST_ORACLE_ALLOW_REMOTE=1 to allow)")
        self.url, self.model, self.timeout, self.seed = url.rstrip("/"), model, timeout, seed
        self.model_id = f"http:{model or 'default'}"

    def _post(self, path: str, body: dict) -> dict:
        req = urllib.request.Request(self.url + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:  # noqa: S310 - loopback by default
                return json.loads(r.read())
        except OSError as e:
            raise OracleUnavailable(f"oracle endpoint {self.url} unreachable: {e}") from e

    def embed(self, texts: list[str]) -> list[list[float]]:
        d = self._post("/embeddings", {"model": self.model, "input": texts})
        return [list(x["embedding"]) for x in sorted(d["data"], key=lambda x: x.get("index", 0))]

    def generate(self, prompt: str, labels: list[str]) -> str:
        d = self._post("/chat/completions", {"model": self.model, "temperature": 0, "top_p": 1, "seed": self.seed, "max_tokens": 16,
                                             "messages": [{"role": "user", "content": prompt}]})
        return str(d["choices"][0]["message"]["content"])


def backend(spec: str | None, model: str = "") -> Backend | None:
    """Parse a backend spec (see the module docstring). ``None`` / "" / "off" = no backend."""
    if not spec or spec == "off":
        return None
    seed = int(os.environ.get("AGENTEST_ORACLE_SEED", SEED))
    if spec == "hash":
        return HashBackend()
    if spec == "replay":
        b = Backend()
        b.model_id = model or "replay"
        return b
    if spec.startswith("llamacpp:"):
        return LlamaCppBackend(spec.split(":", 1)[1], seed=seed)
    if spec.startswith("onnx:"):
        return OnnxBackend(spec.split(":", 1)[1])
    if spec.startswith(("http://", "https://")):
        return HttpBackend(spec, model, seed=seed)
    raise ValueError(f"unknown oracle backend {spec!r}")


# ---------------------------------------------------------------- the oracle

def _key(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _unit(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [round(x / n, DIGITS) for x in v]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


@dataclass
class Decision:
    label: str
    via: str                 # embedding | slm
    margin: float | None     # embedding margin (best - second best), when computed
    scores: dict[str, float] = field(default_factory=dict)


class Oracle:
    def __init__(self, embedder: Backend | None = None, slm: Backend | None = None, cache: str | Path | None = None,
                 offline: bool = False, embed_id: str = "", slm_id: str = "") -> None:
        self.embedder, self.slm, self.offline = embedder, slm, offline
        self.embed_id = embed_id or (embedder.model_id if embedder else "")
        self.slm_id = slm_id or (slm.model_id if slm else "")
        self.cache_path = Path(cache) if cache else Path(os.environ.get("AGENTEST_ORACLE_CACHE") or Path.home() / ".cache" / "agentest" / "oracle.jsonl")
        self._cache: dict[str, object] | None = None

    # -- cache
    def _load(self) -> dict:
        if self._cache is None:
            self._cache = {}
            if self.cache_path.exists():
                for ln in self.cache_path.read_text(encoding="utf-8").splitlines():
                    if ln.strip():
                        d = json.loads(ln)
                        self._cache[d["key"]] = d["value"]
        return self._cache

    def _put(self, key: str, value, meta: dict) -> None:
        with _LOCK:
            self._load()[key] = value
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self.cache_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"key": key, **meta, "value": value}, ensure_ascii=False, separators=(",", ":")) + "\n")

    # -- primitives
    def vectors(self, texts: list[str], prefix: str = "") -> list[list[float]]:
        if not self.embed_id:
            raise OracleUnavailable("no embedding backend configured (AGENTEST_ORACLE_EMBED)")
        c, out, todo = self._load(), {}, []
        for t in texts:
            k = _key(self.embed_id, "embed", prefix + t)
            if k in c:
                out[t] = c[k]
            else:
                todo.append(t)
        if todo:
            if self.offline or self.embedder is None or type(self.embedder) is Backend:
                raise OracleUnavailable(f"embedding not in the oracle cache (offline): {todo[0][:60]!r}")
            for t, v in zip(todo, self.embedder.embed([prefix + t for t in todo]), strict=True):
                out[t] = _unit(v)
                self._put(_key(self.embed_id, "embed", prefix + t), out[t], {"model": self.embed_id, "kind": "embed", "text": prefix + t})
        return [out[t] for t in texts]

    def ask(self, task: Task, text: str) -> str:
        if not self.slm_id:
            raise OracleUnavailable("no SLM backend configured (AGENTEST_ORACLE_SLM)")
        labels = list(task.labels)
        k = _key(self.slm_id, "label", f"{task.id}@{task.version}", text)
        c = self._load()
        if k in c:
            ans = c[k]
        else:
            if self.offline or self.slm is None or type(self.slm) is Backend:
                raise OracleUnavailable(f"SLM answer not in the oracle cache (offline): {task.id} {text[:60]!r}")
            raw = self.slm.generate(task.question.format(labels=" | ".join(labels), text=text), labels).strip()
            ans = raw.strip(" .\"'`*\n").split()[0].lower() if raw.strip(" .\"'`*\n") else ""
            self._put(k, ans, {"model": self.slm_id, "kind": "label", "task": f"{task.id}@{task.version}", "text": text, "raw": raw[:80]})
        if ans not in labels:
            raise OracleUnavailable(f"SLM answer {ans!r} is not one of {labels}")
        return ans

    def scores(self, task: Task, text: str) -> dict[str, float]:
        """Nearest-prototype cosine per label."""
        protos = [(lab, p) for lab, ps in task.labels.items() for p in ps]
        vs = self.vectors([text] + [p for _, p in protos], task.query_prefix)
        q, out = vs[0], {}
        for (lab, _), v in zip(protos, vs[1:], strict=True):
            out[lab] = max(out.get(lab, -1.0), round(cosine(q, v), DIGITS))
        return out

    def classify(self, task: Task, text: str) -> Decision:
        if task.method == "slm":
            return Decision(self.ask(task, text), "slm", None)
        s = self.scores(task, text)
        ranked = sorted(s.items(), key=lambda kv: (-kv[1], kv[0]))
        best, second = ranked[0], ranked[1] if len(ranked) > 1 else (None, -1.0)
        margin = round(best[1] - second[1], DIGITS)
        pos_margin = round(s[task.positive] - max(v for k, v in s.items() if k != task.positive), DIGITS)
        if task.method == "embedding":
            if margin < task.abstain:
                raise OracleUnavailable(f"embedding margin {margin:.3f} inside the abstain band {task.abstain}")
            return Decision(best[0], "embedding", margin, s)
        # embedding+slm: a clear negative is decided by the embedding pre-filter, the rest by the SLM
        if pos_margin <= -task.reject_margin:
            return Decision(best[0], "embedding", pos_margin, s)
        return Decision(self.ask(task, text), "slm", pos_margin, s)


_ACTIVE: Oracle | None = None


def configure(embed: str | None = None, slm: str | None = None, cache: str | Path | None = None, offline: bool | None = None,
              embed_model: str = "", slm_model: str = "") -> Oracle | None:
    """Set the process-wide oracle from arguments, else ``AGENTEST_ORACLE_*``. Returns it (``None`` = no oracle)."""
    global _ACTIVE
    embed = embed if embed is not None else os.environ.get("AGENTEST_ORACLE_EMBED")
    slm = slm if slm is not None else os.environ.get("AGENTEST_ORACLE_SLM")
    off = offline if offline is not None else os.environ.get("AGENTEST_ORACLE_OFFLINE") == "1"
    eb = backend(embed, embed_model or os.environ.get("AGENTEST_ORACLE_EMBED_MODEL", ""))
    sb = backend(slm, slm_model or os.environ.get("AGENTEST_ORACLE_SLM_MODEL", ""))
    _ACTIVE = Oracle(eb, sb, cache, off) if (eb or sb) else None
    return _ACTIVE


def active() -> Oracle | None:
    return _ACTIVE


def describe() -> dict:
    o = _ACTIVE
    return {"oracle": None if o is None else {"embed": o.embed_id or None, "slm": o.slm_id or None, "offline": o.offline,
                                               "cache": str(o.cache_path)}}
