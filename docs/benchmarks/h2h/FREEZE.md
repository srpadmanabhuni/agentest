# H2H benchmark freeze record: 29 Oct 2026, 20:51 IST

Pre-registration. Frozen BEFORE any test-split run. TRAIL data is not included (HF terms: no resharing); only hashes and IDs-free metadata are recorded here.

- agentest commit: 4113b592447ff83595d139ceeb855cb76185e0ee (branch v4.1-h2h-converted)
- Regression floors at the freeze commit (box): examples 393 judge-off / 391 replay; strict 388 / 385
- Judge: Qwen2.5-7B-Instruct-Q4_K_M, http://127.0.0.1:8008/v1, temperature 0, CPU
- Competitor venv (Python 3.12.15, /workspace/h2h/venv): deepeval==4.3.2 inspect-ai==0.3.286 openai==3.41.0 scikit-learn==1.9.1 scipy==1.18.1
- Seeds: 42 (TRAIL dev/test split 30/70 stratified by source; tau-bench 40 failed + 40 passed sample; bootstrap B=2000)
- Mapping: 16 checks -> 7 TRAIL categories (config/mapping.json), chosen by definition, not fitted
- Primary detection rule: any fail; sensitivity row excluding T5-015/X-003 (pre-registered)
- Split sizes: GAIA dev 35 / test 82; SWE-bench dev 9 / test 22; test split never run before this freeze

## sha256
```
b84d2c298bd0e7518a755647872c7dfb65266399231bce31456b5c3e47055117  PROTOCOL.md
d2b1b0cfed7ee619409be5ed47bd66f4107a3a0d0ba69271b85b143c2bf49d66  config/mapping.json
76fc347aae166b353f0d78e2316bb88ba3c21731bbd41b0d3264e03b68c5aa8c  scripts/convert_chat_to_otlp.py
f9d32bba9c6b99be9afcf3ecaecf7975c01f1c98a0c090519b019c802a5abef8  scripts/convert_openinference_to_otlp.py
28e6b8b2a833e203a314d4b2e780178ceaaf227007b0af339c595f559bb657aa  scripts/deepeval_run.py
b8f216af9f2d61b63239372b1d62a4b85712f04ea2902c362cfd639513093d4d  scripts/inspect_task.py
05419750bf6619df41704ad0b7ea7a64aac93377e2b394f7b2ee381581909eb4  scripts/score.py
c4f782980902d509f478512cd2fc4a2a02a79c9148a351f7b96215b1506f52c5  scripts/stats.py
d98ee96b73ca367244e4cfce6416e8af4f544128722d5e3f803b6a6173a915b0  scripts/to_trail_format.py
ed81ebd529da189425efb9c58183e7c1dcd55a234264ea039e03428bcc5f24d2  scripts/trail_calculate_scores.py
00a4b9fb14636c12a37f5446c42e47cb5f961581e600551b627ada9c45a096ef  scripts/freeze.sh
c4476f02f4fc51d7e108c4470546a697e5e4e86f7f45b773e555fe5f8d556a95  splits/trail_gaia/split_dev.txt
a7cca56f592dd2b2452916e2538ff88339effd2deb311f335212de43c6eeef79  splits/trail_gaia/split_test.txt
6d7a8f5ece6d05f3a1b80fa15f05b46dcd8b1af14c408578266957f8c2b03772  splits/trail_swe_bench/split_dev.txt
55256c968b4d6e42134fb424842b19ec715f7a4a4c2f582a286bcf5223dd37b5  splits/trail_swe_bench/split_test.txt
e9e6c0297660c537f83d4fd9c476ce7a9a86ecd2784874b7bfc13be598e37bfa  data/tau/gpt-4o-airline.json
65b8fcd92af6b4fefa935c625d1ac27ea29dcb6ee14589c55a8f115ceaaa1423  /workspace/gguf/Qwen2.5-7B-Instruct-Q4_K_M.gguf
daf24a510c42b110bd936466f20b0b21288ad9763880236d1ac5f46bf828b493  TRAIL dataset (all 300 files, sorted; manifest hash)
```

Verify: `cd /workspace/h2h && sed -n '/^```$/,/^```$/p' FREEZE.md | grep -v '^```' | grep -v TRAIL | sha256sum -c`
