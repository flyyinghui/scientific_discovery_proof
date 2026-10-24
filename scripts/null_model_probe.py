#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数值层置换检验 — 假阳性检测 (P1-1, from Kosmos null_model.py).

对抗 LLM 数值验证的「sycophancy loop」：一个数值「发现」必须在随机扰动下
**消失**（即对参数扰动敏感），否则它就是平凡的恒等式 / 数值巧合 / 假阳性，
而非真正的数值印证。

与 planted_truth_gate (v2.13.0) 互补：
  - planted_truth_gate: 验证数值引擎能恢复已知答案(正对照) + 抓住污染输入(负对照)
  - null_model_probe:   验证「数值发现」是否对参数扰动敏感(对抗数值巧合/平凡恒等)

物理场景示例：
  真发现:  g_TC²(λ) 只在 λ=35/3 时 = 24π²/35，扰动 λ 后显著偏离
  假发现:  f(x) ≡ 24π²/35（常数函数），扰动后仍 = 24π²/35（平凡恒等式/定义重言）

用法：
  python null_model_probe.py --self-test
  python null_model_probe.py --script probe.py --output report.json
      # probe.py 需定义 f(params: dict) -> float 和 params: dict
"""
import argparse
import json
import random
import statistics
import sys
import importlib.util
from dataclasses import dataclass, field, asdict
from typing import Callable, Dict, List, Optional


@dataclass
class NullModelResult:
    observed: float
    claim: float
    n_permutations: int
    null_mean: float
    null_stdev: float
    persistence_rate: float          # 扰动后仍 ≈ claim 的比例（越高越可疑）
    p_value: float                   # 经验 p 值（观测落在零分布内的比例）
    persists_in_noise: bool          # True = 假阳性（发现对扰动不敏感）
    tolerance: float
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


def perturb(params: Dict[str, float], scale: float = 0.1,
            rng: random.Random = None) -> Dict[str, float]:
    """对参数做相对扰动（默认 ±10% 高斯），返回扰动后参数。"""
    rng = rng or random.Random()
    out = {}
    for k, v in params.items():
        out[k] = v * (1.0 + rng.gauss(0.0, scale))
    return out


def null_model_probe(
    f: Callable[[Dict[str, float]], float],
    params: Dict[str, float],
    claim: Optional[float] = None,
    n_permutations: int = 1000,
    tolerance: float = 1e-6,
    perturb_scale: float = 0.1,
    seed: int = 42,
) -> NullModelResult:
    """置换检验：验证数值发现是否对参数扰动敏感。

    Returns:
        persists_in_noise=True 表示发现是「假阳性」（扰动后仍 ≈ claim）。
    """
    warnings: List[str] = []
    rng = random.Random(seed)

    observed = f(params)
    if claim is None:
        claim = observed

    null_values: List[float] = []
    for _ in range(n_permutations):
        p = perturb(params, scale=perturb_scale, rng=rng)
        try:
            null_values.append(f(p))
        except Exception as e:
            warnings.append(f"permutation failed: {e}")
            continue

    if not null_values:
        return NullModelResult(observed, claim, 0, 0.0, 0.0, 1.0, 1.0, True,
                               tolerance, warnings)

    # 扰动后仍 ≈ claim 的比例
    persistence = sum(1 for v in null_values if abs(v - claim) <= tolerance)
    persistence_rate = persistence / len(null_values)

    # 经验 p 值：观测落在零分布内的比例（|null - claim| >= |observed - claim|）
    obs_dev = abs(observed - claim)
    n_extreme = sum(1 for v in null_values if abs(v - claim) >= obs_dev)
    p_value = (n_extreme + 1) / (len(null_values) + 1)

    # 判据：若扰动后仍有 >50% 落在 claim 附近（关系平凡），则假阳性
    persists = persistence_rate > 0.5

    return NullModelResult(
        observed=observed,
        claim=claim,
        n_permutations=len(null_values),
        null_mean=statistics.mean(null_values),
        null_stdev=statistics.stdev(null_values) if len(null_values) > 1 else 0.0,
        persistence_rate=persistence_rate,
        p_value=p_value,
        persists_in_noise=persists,
        tolerance=tolerance,
        warnings=warnings,
    )


# ============================================================================
# self-test
# ============================================================================
def _true_discovery(params):
    """真发现：值 = λ 本身，只在一个点满足 claim。"""
    return params["lambda"]


def _fake_discovery(params):
    """假发现：常数函数（平凡恒等式），任何扰动都不变。"""
    return 24.0 * 3.14159**2 / 35.0


def self_test() -> bool:
    ok = True
    # 真发现：f=λ，claim=35/3，只在 λ=35/3 满足，扰动后偏离 → 不应 persists
    r1 = null_model_probe(_true_discovery, {"lambda": 35.0/3.0},
                          claim=35.0/3.0, n_permutations=200, seed=1)
    print(f"[{'PASS' if not r1.persists_in_noise else 'FAIL'}] 真发现(f=λ): "
          f"persistence={r1.persistence_rate:.1%} persists={r1.persists_in_noise}")
    if r1.persists_in_noise:
        ok = False

    # 假发现：f=常数，扰动后仍 = claim → 应 persists（假阳性）
    c = 24.0 * 3.14159**2 / 35.0
    r2 = null_model_probe(_fake_discovery, {"x": 1.0}, claim=c,
                          n_permutations=200, seed=1)
    print(f"[{'PASS' if r2.persists_in_noise else 'FAIL'}] 假发现(f=常数): "
          f"persistence={r2.persistence_rate:.1%} persists={r2.persists_in_noise}")
    if not r2.persists_in_noise:
        ok = False

    print(f"self-test {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--script", default="", help="定义 f(params) 和 params 的 Python 文件")
    ap.add_argument("--claim", type=float, default=None, help="声明的数值（默认=观测值）")
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--tolerance", type=float, default=1e-6)
    ap.add_argument("--scale", type=float, default=0.1)
    ap.add_argument("--output", default="")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(0 if self_test() else 1)

    if not args.script:
        print("错误：需提供 --script（定义 f(params) 和 params）或 --self-test")
        sys.exit(1)

    spec = importlib.util.spec_from_file_location("probe", args.script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    f = getattr(mod, "f")
    params = getattr(mod, "params")

    r = null_model_probe(f, params, claim=args.claim, n_permutations=args.n,
                         tolerance=args.tolerance, perturb_scale=args.scale)

    print("=" * 60)
    print("数值层置换检验 — 假阳性检测")
    print("=" * 60)
    print(f"观测值: {r.observed:.10g}  声明: {r.claim:.10g}")
    print(f"置换 {r.n_permutations} 次：零分布均值 {r.null_mean:.6g} ± {r.null_stdev:.6g}")
    print(f"扰动后仍≈声明 的比例: {r.persistence_rate:.1%}")
    print(f"经验 p 值: {r.p_value:.4f}")
    verdict = ("❌ 假阳性（发现对扰动不敏感，可能是平凡恒等式/数值巧合）"
               if r.persists_in_noise
               else "✅ 真发现（发现对扰动敏感，数值印证可信）")
    print(f"判定: {verdict}")
    for w in r.warnings:
        print(f"  [warning] {w}")
    print("=" * 60)

    if args.output:
        json.dump(r.to_dict(), open(args.output, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"DONE -> {args.output}")


if __name__ == "__main__":
    main()
