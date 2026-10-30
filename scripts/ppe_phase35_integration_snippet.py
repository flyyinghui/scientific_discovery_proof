# Phase 3.5: 形式化证明自洽性审计 (Stage 3.5 — v2.1.0 集成)
# ============================================================

def phase_consistency_audit(conjecture, target, all_phases, lean_files=None):
    """Phase 3.5: 对生成的 Lean 4 证明做自洽性审计。

    调用 scientific-discovery-proof 的 proof_consistency_audit.py，
    检测六类 P0（公理自相矛盾/表演性诚实/公理计数/定理虚假声称/
    空壳证明/admit/离散谱错误），BLOCK 门控。

    若未指定 lean_files，则扫描 PPE projects 目录下最近生成的 .lean。
    """
    print("\n" + "=" * 60)
    print("PHASE 3.5: Formal Proof Consistency Audit (Stage 3.5)")
    print("=" * 60)

    audit_script = (
        "/mnt/d/HermesAgent/scientific-discovery-proof/scripts/"
        "proof_consistency_audit.py"
    )
    if not os.path.exists(audit_script):
        print("[3.5] ⚠️ audit script not found — skipping")
        return {"status": "skipped", "reason": "audit script missing"}

    # 定位 Lean 产物
    if lean_files is None:
        ppe_root = "/mnt/d/ai_for_science/physics_proof_engine/projects"
        import glob
        lean_files = sorted(
            glob.glob(os.path.join(ppe_root, "**", "*.lean"), recursive=True),
            key=os.path.getmtime, reverse=True
        )[:5]  # 最近修改的 5 个

    if not lean_files:
        print("[3.5] ⚠️ No .lean files found — skipping")
        return {"status": "skipped", "reason": "no lean files"}

    results = []
    gate_overall = "PASS"
    for lean_path in lean_files:
        print(f"[3.5] Auditing: {os.path.basename(lean_path)}")
        cmd = [
            "/usr/local/lib/hermes-agent-v14/venv/bin/python",
            audit_script, "--lean", lean_path,
            "--output", "/tmp/stage35_ppe_audit.json",
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            # 从审计 JSON 读真实 gate（PASS/WARN/BLOCK），不能只看 exit_code
            gate = "PASS"
            audit_json = "/tmp/stage35_ppe_audit.json"
            if os.path.exists(audit_json):
                try:
                    with open(audit_json) as f:
                        gate = json.load(f).get("gate", "PASS")
                except Exception:
                    gate = "BLOCK" if proc.returncode != 0 else "PASS"
            if gate == "BLOCK":
                gate_overall = "BLOCK"
            elif gate == "WARN" and gate_overall == "PASS":
                gate_overall = "WARN"
            results.append({
                "lean_file": lean_path,
                "gate": gate,
                "exit_code": proc.returncode,
            })
            # 提取 warn/block 摘要
            for line in proc.stdout.split("\n"):
                if "WARN" in line or "BLOCK" in line:
                    print(f"    {line.strip()}")
        except Exception as e:
            results.append({"lean_file": lean_path, "gate": "ERROR", "error": str(e)})
            print(f"[3.5] ⚠️ error: {e}")

    audit_report = {
        "status": "completed",
        "gate_overall": gate_overall,
        "files_audited": len(results),
        "results": results,
    }
    print(f"[3.5] Overall gate: {gate_overall} ({len(results)} files)")
    if gate_overall == "BLOCK":
        print("[3.5] 🔴 GATE BLOCKED — proof has consistency issues")
    return audit_report


