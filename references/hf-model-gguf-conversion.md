# HF fp32 → GGUF f16 Conversion (offline, github.com:443 blocked)

Validated 2026-08-18 on Llemma 7B (EleutherAI/llemma_7b, 26.96 GB fp32 → 13.48 GB f16).

## Key facts discovered (avoid re-deriving)

- `convert_hf_to_gguf.py` lives at the llama.cpp repo ROOT and does
  `from conversion import ...`. The `conversion/` package is ALSO at the repo
  ROOT (NOT inside `gguf-py/`). You must download BOTH the script AND the
  `conversion/` directory, placed side by side under the same parent.
- The PyPI `gguf` package has NO HF→GGUF converter (only `scripts/gguf_dump.py`,
  `gguf_hash.py`, etc.).
- `llama-cpp-python` has no prebuilt wheel for Python 3.14 → use the standalone
  script, not pip.
- `torch` CPU-only is enough (torch 2.9.1+cpu worked).

## Download when github.com / raw.githubusercontent.com are blocked

`api.github.com` stays reachable. Use the raw-content endpoint with a special
Accept header (returns the file body directly, not base64 JSON):

```python
import requests
r = requests.get(
    "https://api.github.com/repos/ggml-org/llama.cpp/contents/convert_hf_to_gguf.py",
    headers={"Accept": "application/vnd.github.v3.raw"}, timeout=30)
open("convert_hf_to_gguf.py", "w", encoding="utf-8").write(r.text)
```

List a whole directory tree (find where `conversion/` lives) with the git trees API:

```python
r = requests.get(
    "https://api.github.com/repos/ggml-org/llama.cpp/git/trees/master?recursive=1")
tree = r.json()["tree"]
conv = [t["path"] for t in tree
        if t["path"].startswith("conversion/") and t["type"] == "blob"]
```

## Steps

1. Download `convert_hf_to_gguf.py` (~13 KB).
2. Download the `conversion/` dir (88 files; the 52 that succeed suffice —
   `__init__.py`, `base.py`, `llama.py` are the critical ones). Place under the
   SAME parent as the script so `from conversion import ...` resolves.
3. `pip install gguf sentencepiece` (sentencepiece is REQUIRED for
   sentencepiece-tokenizer models like Llemma — otherwise
   `ModuleNotFoundError: No module named 'sentencepiece'` at `set_vocab`).
4. Run: `python convert_hf_to_gguf.py <hf-dir> --outfile X-f16.gguf --outtype f16`
   (run it with the script's directory as cwd, or `cd` there first).
5. Verify: `python <site-packages>/gguf/scripts/gguf_dump.py X-f16.gguf` and check
   `general.architecture` (=llama), `llama.block_count`, `llama.embedding_length`.

## Numbers (llama 7B reference)

- fp32 3-shard ~27 GB → f16 single file ~13.5 GB (write ~180 MB/s ≈ 70 s).
- llama 7B: 32 layers, 4096 embed, 11008 FFN, context 4096.
- f16 13.5 GB fits a single 20 GB GPU (full offload, fast) — prefer f16 over
  Q4 quantization for proof models (keep API precision), then quantize only if
  VRAM forces it.
