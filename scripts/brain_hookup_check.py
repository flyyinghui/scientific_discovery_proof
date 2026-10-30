#!/usr/bin/env python3
"""神经记忆大脑挂接健康自检（真实 181K 神经元 recall + J-score 冒烟）

用法: <带numpy的python> brain_hookup_check.py
需先挂接数据: <WORK_DIR>\\neural_memory_data\\ + 代码 neural_memory_brain.py
"""
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # 与本脚本同目录的 jspace_bridge

from jspace_bridge import JSpaceBridge, resolve_brain_dir, resolve_brain_code_dir

print("resolved data_dir :", resolve_brain_dir(), flush=True)
print("resolved code_dir :", resolve_brain_code_dir(), flush=True)

t0 = time.time()
bridge = JSpaceBridge()          # 懒加载真实大脑
brain = bridge.brain             # 触发加载
print(f"brain loaded in {time.time()-t0:.1f}s", flush=True)
print("brain_loaded flag :", bridge.brain_loaded, flush=True)

# 神经元规模
try:
    n = len(brain.graph.neurons) if hasattr(brain, "graph") else "n/a"
except Exception as e:
    n = f"err:{e}"
print("neuron count      :", n, flush=True)

# 真实语义召回
for q in ["KLS spectral gap", "Ricci curvature"]:
    t1 = time.time()
    res = brain.recall(q, top_k=3)
    ids = [(r.get("id"), round(float(r.get("similarity", r.get("activation", 0.0))), 4)) for r in res]
    print(f"recall({q!r}) in {time.time()-t1:.1f}s -> {ids}", flush=True)

# 端到端 J-score（真实大脑）
js = bridge.j_score_pair("Ricci curvature", "KLS spectral gap")
print("J-score pair:", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in js.items()}, flush=True)
print("HOOKUP_OK", flush=True)
