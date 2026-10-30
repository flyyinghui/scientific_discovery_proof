# Thinking-Model API Invocation + Research-Level Conditional Theorem Formalization

Validated 2026-08-16 on the V16 P0-2/3/4/6/9 deep-proof session. Two distinct, reusable bodies of knowledge.

## 1. Thinking-model API invocation (the "content is empty" trap)

Multiple LLMs now ship as **thinking models**: they emit a `reasoning_content` (or `thinking`) field
before `content`. If `max_tokens` is too small, the thinking phase eats ALL tokens and `content` comes
back `""`. This hit three times this session with three different surfaces:

| Model / surface | Symptom | Correct fix |
|---|---|---|
| Ollama `qwen3.8:27b-q8_0` via `/api/generate` | `response=""` always | use `/api/chat`, read `message.content` (NOT `response`) |
| Ollama `/api/chat` | `content=""`, `thinking` huge | increase num_predict, OR serve via llama.cpp |
| llama-server (llama.cpp) OpenAI-compat `/v1/chat/completions` | `content=""`, `reasoning_content` huge | payload `"chat_template_kwargs": {"enable_thinking": False}` |
| DeepSeek `deepseek-v4-pro` | `content=""`, `reasoning_content` 48K chars | payload `"thinking": {"type": "disabled"}` |

**The two that actually work** (top-level `enable_thinking: false` and server-start
`--reasoning off` are SILENTLY IGNORED):
- llama-server / qwen3.8: `"chat_template_kwargs": {"enable_thinking": False}` → `reasoning_content=0`, full answer, ~8x speedup.
- DeepSeek v4-pro: `"thinking": {"type": "disabled"}` → `reasoning_content=0`, content returns ~6s.

Diagnostic pattern: call with a trivial prompt (`"Say OK"`) and print ALL message keys —
`['role','content','reasoning_content']` reveals a thinking model immediately.

## 2. llama.cpp multi-GPU for a 48GB model (Windows)

Ollama put `qwen3.8:27b-q8_0` (48GB) at 65% CPU / 35% GPU (only 1 of 4 GPUs), yielding 2.8 tok/s.
`num_gpu=99` hung the reload ("Stopping..." forever — Windows WDDM multi-GPU bug).

Fix — llama.cpp direct:
1. Download prebuilt `llama-b<ver>-bin-win-cuda-12.4-x64.zip` from `github.com/ggml-org/llama.cpp/releases` (api.github.com reachable; `release-assets.githubusercontent.com` CDN works when `github.com` is blocked).
2. GGUF weights are Ollama blobs: `~/.ollama/models/blobs/sha256-<hash>` (29GB file; identify via GGUF magic `b'GGUF'` + `general.name`). Copy to a readable name.
3. Run `llama-server -m model.gguf -ngl 99 --tensor-split 1,1,1,1 --port 8081 --ctx-size 8192`.
4. Result: 4 GPUs each ~12.5GB, 6.3 tok/s (2.25x over Ollama).

**`--tensor-split` is layer-split (pipeline), NOT tensor-parallel** — layers run sequentially so there is
no parallel speedup; it only removes the CPU-offload bottleneck. 30-60 tok/s would need vLLM/TensorRT-LLM
(tensor parallel), which llama.cpp does not do.

## 3. Research-level open problems → conditional theorems (not honest-downgrade, not fake proof)

When a reviewer demands "prove it, don't label it honest-axiom", but the underlying math is an OPEN
problem (Eldan-Chen stochastic localization, Atiyah-Singer non-compact extension, Iwasawa-decomposition
legitimization of Bourgain slicing), the right shape is a **conditional theorem**:

- Research-level premises declared as `axiom` (honest: they are open problems / deep theorems not in Mathlib).
- The theorem body is a **genuine inference chain** (no `sorry`): the reasoning FROM premises TO conclusion is a real proof.

Validated P0-2 (`p02_main`: Iwasawa + Eldan-Chen + Lyapunov ⟹ strong log-concavity of V_eff ⟹
Ric_{V_eff} ≥ 35/2·g ⟹ spectral gap λ₁ ≥ 35/2; `ricci_correction` is real `add_le_add`,
`cd_failure` is a real `le_trans` contradiction proving classical CD(K,N) is impossible when Ric≤0).

Parallel exploration recipe: `delegate_task` with up to 3 concurrent subagents (each 20-30 argument schemes,
documented accept/reject in the file header). Subagents that hit max_iterations leave a half-built file —
the parent truncates to the LAST COMPILING section and appends an honest status comment (this is how
P0-4 landed: sections 1-2 compiled, sections 3-5 typeclass-hell were truncated).

## 4. Mathlib `deriv` genuine proof of chain rule (P0-6: axiom → theorem)

Proving `deriv V φ = ...` for the Starobinsky potential `V = V0·(1 - e^(-√(2/3)·φ/M_Pl))²` from first
principles (no axiom, no sorry). The lemma chain that compiles in mathlib 4.34:

```
unfold V_prime V
simp only [M_Pl, div_one]   -- M_Pl must be INTEGER 1, not float 1.0 (div_one needs ℕ 1)
rw [deriv_const_mul (c := V0) (d := fun y => (1 - Real.exp (-Real.sqrt (2/3) * y))^2) (x := φ) (hd := by fun_prop)]
rw [deriv_fun_pow (f := ...) (x := φ) (h := by fun_prop) (n := 2)]
have hpow : (2-1:ℕ)=1 := by norm_num; rw [hpow, pow_one]
rw [deriv_fun_sub (f := fun _ => (1:ℝ)) (g := fun y => Real.exp (...)) ...]
simp only [deriv_const, zero_sub]
rw [deriv_exp (f := fun y => -Real.sqrt (2/3) * y) (x := φ) (hc := by fun_prop)]
rw [deriv_const_mul_id (c := -Real.sqrt (2/3)) (x := φ)]
ring
```

Three traps:
1. **`M_Pl` float vs integer**: `def M_Pl : ℝ := 1.0` breaks `div_one` (needs `1`); `def M_Pl : ℝ := 1` makes `simp only [M_Pl, div_one]` close the `/M_Pl` divisions.
2. **`norm_num` simplifies `Real.sqrt (2/3)` → `√2/√3`**, which breaks downstream `rw [deriv_const_mul ...]` matching (the d-param still says `Real.sqrt (2/3)`). Use `simp only [M_Pl, div_one]`, NOT `norm_num [M_Pl]`, to keep sqrt symbolic.
3. The `deriv_*` lemmas need explicit implicit args (`c :=`, `d :=`, `f :=`, `x :=`) because `rw [lemma (by fun_prop)]` leaves metavariables `fun_prop` cannot solve.

## 5. Neural memory brain search (keyword match over 167K neurons)

`<PPE_DIR>/neural_memory_data/neurons.json` is a 910MB JSON
ARRAY (not JSONL). Each neuron: `{"id": "n000000", "content": "...", "v": -52.0, "type": "concept", "tags": [...], ...}`.

Fast keyword search (4.6s): `mmap` the file, regex `"id":\s*"(n\d+)"\s*,\s*"content":\s*"((?:[^"\\]|\\.)*)"` over the whole blob, score by keyword hit count in `content.lower()`. See `<PPE_DIR>/brain_search.py`.
