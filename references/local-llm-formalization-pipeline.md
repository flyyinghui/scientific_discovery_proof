# Local LLM Formalization Pipeline (llama.cpp + DeepSeek) — 2026-08-16

Validated workflow for formalizing a math textbook (Complex Analysis, Gamelin, 494pp) into Lean 4 + Mathlib using local + remote LLMs. End result: 209 theorems, 100% compilable via a mixed generate→verify→fix loop.

## 1. Thinking-model token exhaustion (THE core pitfall)

All three current-generation LLMs are **thinking models** — their hidden reasoning chain silently eats the `max_tokens` budget, returning empty `content`. Each has a DIFFERENT correct disable mechanism:

| Model/Server | Symptom | Correct disable | Wrong attempts |
|---|---|---|---|
| **DeepSeek v4-pro** | `reasoning_content` reaches 48,000+ chars, `content=""` even at max_tokens=16000 | payload `"thinking": {"type": "disabled"}` | `"thinking": false` (deserialize error); `"enable_thinking": false` (silently ignored) |
| **llama-server** (llama.cpp) | `reasoning_content` field populated, `content` empty on long prompts | payload `"chat_template_kwargs": {"enable_thinking": False}` | `--reasoning off` CLI flag (ignored); top-level `"enable_thinking": false` (ignored — must be nested under `chat_template_kwargs`) |
| **Ollama** | `/api/generate` `response` empty; `/api/chat` splits into `message.thinking` + `message.content` | use `/api/chat` and read `message.content` | `/api/generate` for thinking models |

Key insight: these models have a Jinja chat template with `{% if enable_thinking is undefined or enable_thinking is true %}` → reasoning defaults ON. The variable must reach the template parser through the server's kwargs channel, not the raw payload.

## 2. llama.cpp multi-GPU (layer split, NOT tensor parallel)

- 4× RTX 4000 Ada (80GB total) vs 48GB q8 model → must use multi-GPU.
- `llama-cli -m model.gguf -ngl 99 --tensor-split 1,1,1,1` → 4 GPUs evenly split (12-13GB each).
- Result: **6.3 t/s** vs Ollama's 2.8 t/s (2.25× speedup). Ollama only used 1 GPU (35% GPU / 65% CPU) because its Windows multi-GPU split (`num_gpu=99`) deadlocks at "Stopping...".
- **`--tensor-split` is LAYER split (pipeline), NOT tensor parallel**: layers run sequentially, only the layer's GPU is active at a time. Expect 6-10 t/s for a 27B q8, NOT the 30-60 t/s of true tensor parallelism (vLLM/TensorRT-LLM, which need WSL2 on Windows).
- GGUF export from Ollama: the 29GB weight blob lives in `~/.ollama/models/blobs/sha256-<hash>` — copy it, no re-download needed.

## 3. Mixed generate→verify→fix pipeline (100% compilable)

```
llama-server (multi-GPU, thinking disabled, ~30s/theorem)
  → 40% compile on first try
  → 60% fail → DeepSeek v4-pro fix (thinking disabled, 100% fix rate)
  → final 100% compilable
```

- Output quality: "type-correct statement + `sorry` body" level. Statements are rigorous, proofs are stubs (full proofs need Mathlib analysis library depth — separate effort).
- Batch loop: extract theorem stmt from PDF (pymupdf `fitz`, skip TOC pages) → generate → `lake env lean <file>.lean` compile check → on failure send errors back to DeepSeek for fix → recompile.
- Speed budget: ~4 min/theorem (30s generate + 3min compile where import Mathlib alone is ~90-110s) + 60% need a fix pass.

## 4. Mathlib `deriv` chain-rule proof pattern (P0-6 V_prime)

Genuine derivation (NOT axiom) of the Starobinsky potential derivative. The exact lemma signatures that work in mathlib 4.34:

```lean
theorem V_prime_formula (φ : ℝ) : deriv V φ = ... := by
  unfold V
  simp only [M_Pl, div_one]        -- ONLY works if M_Pl := 1 (integer). M_Pl := 1.0 breaks div_one!
  rw [deriv_const_mul (c := V0) (d := fun y => ...) (x := φ) (hd := by fun_prop)]
  rw [deriv_fun_pow (f := fun y => ...) (x := φ) (h := by fun_prop) (n := 2)]
  have hpow : (2 - 1 : ℕ) = 1 := by norm_num
  rw [hpow, pow_one]
  rw [deriv_fun_sub (f := ...) (g := ...) (x := φ) (hf := by fun_prop) (hg := by fun_prop)]
  simp only [deriv_const, zero_sub]
  rw [deriv_exp (f := fun y => ...) (x := φ) (hc := by fun_prop)]
  rw [deriv_const_mul_id (c := -Real.sqrt (2/3)) (x := φ)]
  ring
```

Pitfalls learned:
- Lemma names are `deriv_fun_pow`/`deriv_fun_sub`/`deriv_const_mul_id` (NOT `deriv_pow`/`deriv_sub`). Supplying implicit args explicitly (`c :=`, `d :=`, `x :=`, `h :=`, `n :=`) is mandatory — bare `rw [deriv_const_mul]` leaves metavariables `fun_prop` can't solve.
- `Real.deriv_exp` is the bare exp derivative; the composition form is root-namespace `deriv_exp` with a `hc` differentiability proof.
- **M_Pl := 1.0 (float) breaks `div_one`** (which matches only integer `1`). If the paper's constant is `1.0`, either change the def to integer `1` (mathematically equal in ℝ) or use `norm_num` (which then rewrites `sqrt(2/3) → √2/√3` and breaks downstream matching).
- `norm_num` on a floating cube `(1+4.29)^3` is imprecise → prefer the inequality form `|x - target| < tol`.

## 5. Subagent delegation for hard Lean proofs

For a genuinely-hard proof (chain rule, 30+ compile iterations), delegate to a leaf subagent with: the goal theorem, the compile command, the exact mathlib path to grep lemma signatures from, and "iterate write→compile→read error→fix until exit 0". It ran 30 API calls / ~28min and returned a compiling proof — much better than burning parent context on 30 failed `rw` attempts.

## 6. Loading a 144GB MoE model on 80GB VRAM (DeepSeek V4 Flash Q4_K_XL) — 2026-08-17

DeepSeek-V4-Flash is a 284B MoE (Q4_K_XL = 144.4GB). It CANNOT fit 4×20GB VRAM, so MoE expert weights must stay on CPU:

```bash
# WRONG: -ngl 40 → each MoE layer is ~34GB, single card has 20GB → cudaMalloc OOM
# RIGHT:
llama-server.exe -m DeepSeek-V4-Flash-Q4_K_XL-MERGED.gguf \
  --n-gpu-layers 16 --cpu-moe --ctx-size 8192 --port 11435
```

- `--cpu-moe` keeps ALL Mixture-of-Experts weights on CPU (needs ~144GB RAM; verified on 536GB box).
- Resulting speed: **0.5–0.96 char/s** (MoE CPU offload). A ~200-char short theorem takes ~7min; a >500-char proof exceeds a 15min timeout.
- **Verdict**: local Q4_K_XL is usable for SHORT theorems only. Long-theorem local inference is not viable at this speed; use DeepSeek API (seconds) instead.

## 7. Signature-skeleton prompt trick (boosts generator pass-rate sharply)

Giving qwen3.8 the **exact theorem signature** in the prompt (instead of a prose description) lifted direct-compile pass rate from 0/8 to 2/4:

```
BAD:  "Formalize: the inverse of an element in a group is unique."
GOOD: "Formalize: theorem my_inv_unique {G} [Group G] (a b c : G) (hab : a*b=1) (hac : a*c=1) : b = c := by ..."
```

Also: name the theorem something that does NOT collide with Mathlib (`inv_unique` is already declared — use `my_inv_unique`).

## 8. False-OK detection: check `has_theorem`, not just exit code

An empty file containing only `import Mathlib` **compiles with returncode 0** but proves nothing. The compile-check predicate must be:

```python
ok = (r.returncode == 0) and ('theorem' in code or 'lemma' in code or 'def' in code)
```

This caught 2 "successful" theorems that were actually 18-byte empty files (Q4_K_XL returned nothing for complex prompts).

## 9. Hard Mathlib API beats all three models — classify by API depth

Three-model hybrid (qwen3.8 generate + Q4_K_XL fix short + DeepSeek API fix long) on "Mathematics for Physicists" Linear Algebra:
- **Short theorems (sets/groups/maps, ~200 char)**: 3/3 compiled (qwen3.8 direct ×2, Q4_K_XL ×1).
- **Long theorems (dot/det/eigen/Cauchy-Schwarz)**: 0/5 — even a hand-written "correct" `norm_inner_le_norm ℝ x y` failed with `Application type mismatch`.

Root cause: deep Mathlib APIs (Finset.sum algebra, InnerProductSpace typeclass, Matrix.det theory, `norm_inner_le_norm` exact args) are beyond the automatic knowledge of ALL three models. They need manual Mathlib-source lookup. This is a DIFFERENT failure mode than the Complex-Analysis case (statement-stub → proof, shallow API → 100% DeepSeek fix rate).

**Llemma 7B** (EleutherAI, trained on proof-pile-2 = Lean 4 proofs) is the domain-specialist model for exactly this. Downloadable non-gated via hf-mirror.com (hf-mirror.com/api/models/EleutherAI/llemma_7b → 996 downloads, ~15GB). InternLM2-Math-7B on ModelScope is a fallback. DeepSeek-Prover-V1.5 is gated (401 + ModelScope 404).
