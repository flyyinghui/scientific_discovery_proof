# Thinking-Model Disable + Multi-GPU LLM + PDF Formalization (2026-08-16)

Three hard-won techniques from the "formalize Complex Analysis (Gamelin) PDF" session, reusable for any LLM-driven Lean/formalization batch job.

## 1. Disabling thinking on two LLM backends

Both qwen3.8 and deepseek-v4-pro are THINKING models. On complex prompts the thinking
chain silently consumes the entire max_tokens budget and `content` comes back empty.
Disable it — the exact incantation differs per backend:

| Backend | Correct disable | Wrong approaches (all verified to fail) |
|---------|-----------------|------------------------------------------|
| **llama.cpp / llama-server** (OpenAI-compat) | JSON body field `"chat_template_kwargs": {"enable_thinking": False}` | `--reasoning off` (server flag — ignored by qwen3.8 template); top-level `"enable_thinking": false` (ignored); prompt "do not think" (makes it worse) |
| **DeepSeek v4-pro** | JSON body field `"thinking": {"type": "disabled"}` | `"thinking": false` (deserialize error); top-level `"enable_thinking": false` (ignored) |

With thinking disabled: qwen3.8 27b goes from ~6 t/s (thinking burned) to direct-answer
in ~26-64s for a full Lean theorem (~24× wall-clock speedup). DeepSeek v4-pro returns a
1159-char Lean proof in ~6s.

**Diagnosis trick**: on both backends the thinking text lives in a separate field —
`message.reasoning_content` (llama-server & DeepSeek) — while `message.content` is the
answer. If `content` is empty but `reasoning_content` is huge, thinking ate the budget;
disable it, don't just raise max_tokens.

## 2. llama.cpp multi-GPU for a 48GB model on 4×20GB GPUs

```
llama-server -m model.gguf -ngl 99 --tensor-split 1,1,1,1 --port 8081 --ctx-size 8192
```

- `--tensor-split 1,1,1,1` = uniform LAYER split across 4 GPUs (pipeline, not tensor
  parallel — GPUs work serially per layer, so speedup vs CPU-offload is ~2×, NOT the
  4× you'd get from true tensor parallel which llama.cpp doesn't support).
- Result: qwen3.8 27b q8 (48GB) offloaded fully, 6.3 t/s vs Ollama's 2.8 t/s (Ollama on
  Windows WDDM only used ONE GPU and stuck at "Stopping..." when num_gpu=99 was forced).
- GGUF is already on disk at `~/.ollama/models/blobs/sha256-<hash>` — the 29GB blob is the
  weights; copy it, no re-download. Identify via `ollama list` + `ls -la` by size.
- `import fitz` is deprecated → use `import pymupdf` (1.28.2). execute_code sandbox Python
  may differ from user pip Python — install inside the sandbox: `subprocess.run([sys.executable,"-m","pip","install","pymupdf"])`.

## 3. Mathlib `deriv` genuine proof (upgrading an axiom to a theorem)

P0-6 pattern: an `axiom V_prime_formula` wrapping the chain rule was upgraded to a real
`theorem` using Mathlib's `deriv` lemmas. Working lemma set (signatures confirmed in
`Mathlib/Analysis/Calculus/Deriv/`):

```
deriv_const_mul (c) (d) (x) (hd)   -- deriv (fun y => c * f y) x = c * deriv f x
deriv_fun_pow   (f) (x) (h) (n)    -- power rule (via @[to_fun] attribute)
deriv_fun_sub   (f) (g) (x) (hf) (hg)
deriv_exp       (f) (x) (hc)       -- chain rule for exp (root namespace, NOT Real.deriv_exp)
deriv_const_mul_id (c) (x)         -- deriv (fun y => c * y) x = c
```

Pitfalls that cost iterations:
- Pass implicit args EXPLICITLY (`(c := V0) (d := fun y => ...) (x := φ) (hd := by fun_prop)`)
  — bare `rw [lemma (by fun_prop)]` leaves metavariables `fun_prop` can't solve.
- `norm_num` in this Lean version rewrites `Real.sqrt (2/3) → √2/√3`, breaking downstream
  `rw` matches. Use `simp only [M_Pl, div_one]` instead when you need to keep the sqrt form.
- `def M_Pl : ℝ := 1.0` (float) breaks `div_one` (which is for integer `1`); change to
  `def M_Pl : ℝ := 1` — mathematically identical, makes the proof go through.
- `(2 - 1 : ℕ)` does NOT reduce definitionally under `simp`; use
  `have hpow : (2-1:ℕ) = 1 := by norm_num` first.

## 4. PDF → Lean batch pipeline (validated 100% end-to-end)

Two-stage hybrid beats either LLM alone:
1. **llama-server (local, multi-GPU, thinking off)** generates the theorem statement —
   fast but ~40% one-pass compile rate (uses wrong `fderiv` API: `.1`/`.2` on a continuous
   linear map is wrong; partial derivatives are `fderiv ℝ u p (1,0)`).
2. **compile with `lake env lean`** (reuse the MathCode lakefile + mathlib olean).
3. **failures → DeepSeek v4-pro (`thinking:{"type":"disabled"}`) fix** → 100% fix rate.

Result: 5/5 theorems compile (2 direct + 3 deepseek-fixed). Generated files are
"statement type-correct + `sorry` body" quality — honest about what they are.

Prompt improvement that eliminated the fderiv class of errors: tell the model to declare
partial derivatives as AXIOMS (`axiom du_dx : ℝ × ℝ → ℝ`) instead of using `fderiv`/`.1`,
and remind it `axiom` has NO `:= by sorry` (that's a syntax error).
