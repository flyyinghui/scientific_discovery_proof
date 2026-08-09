# Stage 4 — AI-Scientist V2: Paper Generation

**Fully autonomous scientific paper generation with BFTS experimentation.**

## Overview

Based on **Sakana AI's AI Scientist-v2** ([arXiv:2504.08066](https://arxiv.org/abs/2504.08066)) — the first system to produce peer-reviewed ML workshop papers with zero human intervention.

Four-phase pipeline:
1. **Ideation** — Novelty-checked research idea generation
2. **BFTS Experimentation** — Best-First Tree Search with agent-driven code generation
3. **Writeup** — Automatic LaTeX paper composition
4. **Review** — LLM peer review with iterative improvement

## Two Paths for Paper Generation

### Path A: Full BFTS (for ML experiments)

```bash
cd /mnt/d/AI_for_Science/AI-Scientist-v2
export DEEPSEEK_API_KEY="sk-..."

python launch_scientist_bfts.py \
  --load_ideas "ai_scientist/ideas/my_topic.json" \
  --idea_idx 0 \
  --model deepseek-v4-pro \
  --num_cite_rounds 20
```

### Path B: Direct DOCX (for theoretical physics / urban science)

When writeup pipeline is impractical (VLM incompatibility, LaTeX compilation issues):

```python
from openai import OpenAI
client = OpenAI(api_key="...", base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[{"role": "user", "content": paper_prompt}],
    max_tokens=16384, temperature=0.3,
    extra_body={"thinking": {"type": "disabled"}}
)

# Parse markdown → python-docx with embedded figures
```

## Key Pitfalls

| Pitfall | Symptom | Fix |
|:---|---|:---|
| v4-pro large-token hang | 12+ min with 0% CPU on 16K token generation | Use `deepseek-v4-flash` |
| VLM incompatibility | `ValueError: Model deepseek-v4-pro not supported` for VLM | Skip VLM chart review entirely |
| LaTeX code block missing | `return False` on regex match | Fallback to raw LaTeX detection |
| Chinese quote in f-string | `SyntaxError: invalid syntax` | Use `.format()` or Unicode escapes |

## Reference

- **Paper**: Sakana AI (2025). "AI Scientist-v2: Workshop-Level Automated Scientific Discovery." arXiv:2504.08066.
- **Repository**: [github.com/SakanaAI/AI-Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2)
