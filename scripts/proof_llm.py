#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
proof_llm — P01/T07 的真 LLM 后端（stdlib urllib，无 openai 依赖）

为什么单独一层：
  harness 精炼的价值只体现在**生成类** agent 上（P01 出命题、T07 补证明）。
  审计类 agent 判的是文件事实，harness 改不动。所以这两步必须真调模型，
  否则 `prompt_style` / `memory_policy` 全是空转（MVP-1 实测已证）。

设计要点：
  ① **零新依赖**：stdlib urllib + json。不引 openai SDK（本项目一贯 stdlib-only 风格）。
  ② **磁盘缓存**：key = sha256(model + prompt + params)，命中直接返回。
     同一 harness 变体重复跑不再收费，也是让 --self-test 可重复的前提。
  ③ **优雅降级**：无 key / 网络失败 / 空响应 → 返回 None，调用方转静态路径，
     **绝不抛出**（否则一个 API 抖动会毁掉整轮回环）。
  ④ **响应清洗**：剥 ```lean 围栏、剥解释性前后缀，只留可编译的声明块。

模型选择（沿用用户既定偏好）：
  · 形式化证明论证 → `deepseek-v4-pro`（max_tokens=32768）
  · V4 Flash 的 thinking 会吃掉 0 chars 输出，不用它做形式化。

用法：
    from proof_llm import llm, extract_lean
    text = llm(prompt, max_tokens=8192)          # None 表示不可用
    code = extract_lean(text or "")
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request

# ── 配置 ──────────────────────────────────────────────────────────
DEFAULT_MODEL = os.environ.get("PROOF_LLM_MODEL", "deepseek-v4-pro")
DEFAULT_MAX_TOKENS = int(os.environ.get("PROOF_LLM_MAX_TOKENS", "32768"))
API_BASE = os.environ.get("PROOF_LLM_BASE", "https://api.deepseek.com/v1")
CACHE_DIR = os.environ.get("PROOF_LLM_CACHE", os.path.join(
    os.environ.get("TEMP", "/tmp"), "proof_llm_cache"))

_ENV_CANDIDATES = [
    r"<LEAN_PROJECT>\.env",
    os.path.expanduser(r"~\.env"),
]


def _find_key() -> str:
    """按顺序找 key：环境变量 → .env 文件。不打印、不外泄。"""
    for var in ("DEEPSEEK_API_KEY", "PROOF_LLM_KEY"):
        v = os.environ.get(var, "").strip()
        if v.startswith("sk-"):
            return v
    for p in _ENV_CANDIDATES:
        try:
            if not os.path.exists(p):
                continue
            txt = open(p, encoding="utf-8", errors="ignore").read()
            m = re.search(r"sk-[A-Za-z0-9]{20,}", txt)
            if m:
                return m.group(0)
        except Exception:
            continue
    return ""


_KEY = None


def available() -> bool:
    global _KEY
    if _KEY is None:
        _KEY = _find_key()
    return bool(_KEY)


def _cache_path(model: str, prompt: str, max_tokens: int, temperature: float) -> str:
    h = hashlib.sha256(
        ("%s|%s|%d|%.2f" % (model, prompt, max_tokens, temperature)).encode()
    ).hexdigest()[:24]
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, h + ".txt")


def llm(prompt: str, max_tokens: int = None, temperature: float = 0.0,
        model: str = None, retries: int = 2, timeout: float = 180.0,
        use_cache: bool = True) -> str | None:
    """调 LLM，返回纯文本；不可用时返回 None（调用方需降级）。"""
    model = model or DEFAULT_MODEL
    max_tokens = max_tokens or DEFAULT_MAX_TOKENS
    cp = _cache_path(model, prompt, max_tokens, temperature)
    if use_cache and os.path.exists(cp):
        try:
            return open(cp, encoding="utf-8").read()
        except Exception:
            pass

    if not available():
        return None

    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode()

    last_err = ""
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                API_BASE + "/chat/completions", data=body,
                headers={"Authorization": "Bearer " + _KEY,
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read().decode())
            ch = (d.get("choices") or [{}])[0]
            txt = (ch.get("message", {}) or {}).get("content") or ""
            usage = d.get("usage") or {}
            rtok = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)
            if txt.strip():
                if use_cache:
                    try:
                        open(cp, "w", encoding="utf-8").write(txt)
                    except Exception:
                        pass
                return txt
            # ★ reasoning 模型特有：finish=length 且 reasoning_tokens≈max_tokens
            #   说明 think 把预算吃光，正文一个字没吐。实测 16 tok 全给 reasoning。
            #   处理：把 max_tokens 翻倍重试（最多 2 次），绝不返回空串。
            if ch.get("finish_reason") == "length" and rtok >= max_tokens * 0.9:
                if attempt < retries:
                    max_tokens = min(max_tokens * 4, 65536)
                    body = json.dumps({
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    }).encode()
                    last_err = "thinking consumed all %d tokens → retry with %d" % (rtok, max_tokens)
                    continue
            last_err = "empty content (finish=%s, reasoning=%d)" % (
                ch.get("finish_reason"), rtok)
        except urllib.error.HTTPError as e:
            last_err = "HTTP %s" % e.code
            if e.code in (401, 402, 403):        # key 无效/欠费 —— 重试无意义
                break
        except Exception as e:
            last_err = "%s: %s" % (type(e).__name__, str(e)[:80])
        time.sleep(1.5 * (attempt + 1))
    return None


# ── 响应清洗 ──────────────────────────────────────────────────────
_FENCE = re.compile(r"```(?:lean4?|Lean4?)?\s*\n(.*?)```", re.S)
_DECL = re.compile(r"^\s*(?:theorem|lemma|axiom|def|abbrev|import|open|noncomputable|section|namespace)\b")


def extract_lean(text: str) -> str:
    """从模型回复里抽出 Lean 代码块（优先围栏，退化为按声明行切）。"""
    if not text:
        return ""
    m = _FENCE.findall(text)
    if m:
        return "\n\n".join(x.strip() for x in m if x.strip())
    lines = text.splitlines()
    keep, started = [], False
    for l in lines:
        if _DECL.match(l):
            started = True
        if started:
            keep.append(l)
    return "\n".join(keep).strip() if keep else text.strip()


def has_decl(code: str) -> bool:
    return bool(re.search(r"^\s*(?:theorem|lemma|axiom|def|abbrev)\s+[A-Za-z_]",
                          code or "", re.M))


def has_sorry(code: str) -> bool:
    return bool(re.search(r"\bsorry\b", code or ""))


_SUBSTANTIVE = re.compile(
    r"\b(calc|have|obtain|refine|apply|exact|rw|simp|ring|ring_nf|field_simp|"
    r"linarith|nlinarith|positivity|norm_num|omega|induction|cases|rcases|"
    r"by_contra|contradiction|constructor|intro|use|exists)\b")


def has_substantive_tactic(code: str) -> bool:
    return bool(_SUBSTANTIVE.search(code or ""))


# ── 自测 ──────────────────────────────────────────────────────────
def _self_test() -> int:
    print("可用:", available(), "| model:", DEFAULT_MODEL, "| cache:", CACHE_DIR)
    assert extract_lean("```lean\ntheorem a : True := trivial\n```").startswith("theorem")
    assert "theorem" in extract_lean("说明如下：\ntheorem a : True := trivial")
    assert has_decl("theorem a : True := trivial")
    assert not has_sorry("theorem a : True := trivial")
    assert has_sorry("theorem a : True := by sorry")
    assert has_substantive_tactic("theorem a : 1+1=2 := by ring")
    assert not has_substantive_tactic("theorem a : True := trivial")
    print("[1] 清洗/判据 OK")

    if not available():
        print("[2] 无 key → llm() 必须返回 None（降级路径）")
        assert llm("ping", max_tokens=8) is None
        print("[OK] proof_llm self-test 通过（降级模式）")
        return 0

    print("[2] 真实调用（短）...")
    t0 = time.time()
    out = llm("Reply with exactly: PONG", max_tokens=256, use_cache=False)
    print("    ->", repr((out or "")[:40]), "%.1fs" % (time.time() - t0))
    assert out is not None, "有 key 但调用失败"
    print("[OK] proof_llm self-test 通过（在线模式）")
    return 0


if __name__ == "__main__":
    raise SystemExit(_self_test())
