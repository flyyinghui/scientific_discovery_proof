#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jev_arbiter_bridge — Jev-Omni 判别器桥接（**只做排序，绝不做判定**）

定位（写死在代码里，不是文档里的君子协定）：
  Jev-Omni 是 Gemma 4 12B 微调的多模态**决策分类器**，输入「状态 + 问题 + 选项」，
  输出每个选项的概率。它在 harness2 里的角色是 **Compose 阶段的候选排序器**——
  因为 harness2 刻意没有 ground-truth 打分器，只能靠判别器在多个交付物之间排先后。

  ⚠️ 本技能的 Jev-Omni 用法有**两条硬红线**（代码级强制，见 `_assert_not_gate`）：
    ① 概率**禁止**写成 verifier score 注入任何 gate/BLOCK 判定
    ② 只允许 **choice 型**（"哪个候选更好"）；score 型在 decision-bench 上仅 12.8%，
       本机实测（skill: harness2）——用了就是自欺

本机实测能力边界（不要越界）：
    choice 型 80.0%  ✅ 可用于候选排序（这正是我们的用法）
    noul   型 74.0%  ⚠️ 仅辅助
    score  型 12.8%  ❌ 禁用（系统性选最后一档，是位置偏置不是能力）

与 Lean 的分工（不可混）：
    Lean 编译 + Stage 3.5 审计  →  说「对不对」（Arbiter 独占）
    Jev-Omni                    →  说「几个都对的候选里，哪个证据链更像完整」

用法：
    from jev_arbiter_bridge import probe_health, rank_candidates
    if probe_health():
        order = rank_candidates(state, ["h_a 的完整轨迹", "h_b 的完整轨迹"])
        # order 只用于展示/归档

自测：
    python jev_arbiter_bridge.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.request

DEFAULT_HOST = os.environ.get("JEV_HOST", "http://127.0.0.1:9411")


class JevMisuseError(RuntimeError):
    """Jev-Omni 被误用为判定器时抛出。"""


def _assert_not_gate(purpose: str) -> None:
    """红线守卫：任何试图把 Jev 输出当 gate/verifier 的调用路径都必须在这里被拦下。"""
    banned = ("gate", "verdict", "block", "verifier", "accept_reject", "pass_fail")
    low = (purpose or "").lower()
    for b in banned:
        if b in low:
            raise JevMisuseError(
                "Jev-Omni 只能做候选排序，不可用作 %r（会把无 verifier 前提与 Lean 硬验证混为一谈）"
                % b)


def probe_health(host: str = DEFAULT_HOST, timeout: float = 3.0) -> bool:
    """探端点是否就绪。不可用不是错误 —— 整个流程要能在无 Jev 的情况下跑完。"""
    try:
        with urllib.request.urlopen(host.rstrip("/") + "/health", timeout=timeout) as r:
            d = json.loads(r.read().decode())
            return bool(d.get("ready", False))
    except Exception:
        return False


def rank_candidates(state: str, options: list, host: str = DEFAULT_HOST,
                    timeout: float = 60.0, question: str = None,
                    purpose: str = "rank_candidates") -> dict:
    """对候选做 choice 型概率排序。

    返回：
        可用   -> {"available": True, "order": [(label, prob), ...], "mode": "jev"}
        不可用 -> {"available": False, "order": [(label, 0.0), ...], "mode": "degraded",
                   "reason": "..."}

    ⚠️ 无论哪种模式，`order` 都**只用于展示与归档**。调用方不得把它写成 gate 输入。
    """
    _assert_not_gate(purpose)
    if not options:
        return {"available": False, "order": [], "mode": "empty", "reason": "no options"}
    if len(options) > 20:
        # harness2 技能记录的边界：选项 ≤20 才有质量保证（head 支持到 256）
        options = options[:20]

    q = question or "Which candidate shows the more complete, trustworthy evidence chain?"
    body = json.dumps({"state": state, "question": q, "options": options}).encode()
    try:
        req = urllib.request.Request(host.rstrip("/") + "/rank", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode())
        probs = d.get("probabilities") or d.get("scores") or {}
        if isinstance(probs, list):                       # 兼容 list 形式
            probs = {options[i]: p for i, p in enumerate(probs) if i < len(options)}
        order = sorted(((k, float(v)) for k, v in probs.items()), key=lambda kv: -kv[1])
        return {"available": True, "order": order, "mode": "jev",
                "question": q, "n_options": len(options)}
    except Exception as e:
        return {"available": False,
                "order": [(o, 0.0) for o in options],
                "mode": "degraded",
                "reason": "%s: %s" % (type(e).__name__, str(e)[:120]),
                "question": q, "n_options": len(options)}


def rank_runs(runs: list, host: str = DEFAULT_HOST) -> dict:
    """便利封装：直接对 list[ProofRun] 排序（按轨迹摘要文本，不传图）。

    文本轨迹是 harness2 实测里最可靠的一条路（图像模态概率分散，只作交叉验证）。
    """
    state = "多个 harness 在同一物理猜想上的证明轨迹对比。评分只看证据链完整度描述，不判对错。"
    opts = []
    for r in runs:
        by = {s.step_id: s for s in r.steps}
        closed = by.get("E06").ok if by.get("E06") else False
        honesty = by.get("H05").ok if by.get("H05") else False
        opts.append("%s: %d 步, 链闭合=%s, 诚实性=%s, verdict=%s" % (
            r.harness_name, len(r.steps), closed, honesty, r.audit_verdict))
    if not opts:
        return {"available": False, "order": [], "mode": "empty", "reason": "no runs"}
    res = rank_candidates(state, opts, host=host)
    res["harness_names"] = [r.harness_name for r in runs]
    return res


# ── 自测 ──────────────────────────────────────────────────────────
def _self_test() -> int:
    print("host:", DEFAULT_HOST)
    ok = probe_health()
    print("health:", "ready" if ok else "unavailable（将走降级路径）")

    # 1) 红线守卫
    try:
        _assert_not_gate("use as gate verdict")
        print("✗ 红线未拦截")
        return 1
    except JevMisuseError as e:
        print("[1] 红线守卫 OK ->", str(e)[:60], "...")

    # 2) 正常排序（可用或降级）
    res = rank_candidates("测试状态", ["候选 A", "候选 B", "候选 C"])
    print("[2] 排序 mode=%s available=%s" % (res["mode"], res["available"]))
    for lab, p in res["order"]:
        print("    %-10s %.3f" % (lab, p))
    if not res["available"]:
        print("    reason:", res.get("reason"))

    # 3) 降级不抛异常（断网模拟：不存在的端口）
    res2 = rank_candidates("x", ["a", "b"], host="http://127.0.0.1:59999", timeout=1.0)
    assert res2["available"] is False and res2["mode"] == "degraded"
    print("[3] 降级路径 OK（端点不可用时不阻塞主流程）")

    # 4) 选项上限
    res3 = rank_candidates("x", ["o%d" % i for i in range(30)], timeout=1.0)
    assert res3.get("n_options") <= 20
    print("[4] 选项裁剪 OK（n_options=%d ≤ 20）" % res3["n_options"])

    print("\n[OK] jev_arbiter_bridge self-test 全部通过")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="jev_arbiter_bridge — Jev-Omni 排序桥（非 verifier）")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--health", action="store_true")
    ap.add_argument("--state", default="测试状态")
    ap.add_argument("--options", nargs="*", default=["候选 A", "候选 B"])
    a = ap.parse_args()
    if a.self_test:
        raise SystemExit(_self_test())
    if a.health:
        print("ready" if probe_health() else "unavailable")
    else:
        print(json.dumps(rank_candidates(a.state, a.options), ensure_ascii=False, indent=1))
