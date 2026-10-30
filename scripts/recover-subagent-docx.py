#!/usr/bin/env python3
"""Subagent DOCX Recovery Script — Engineering Cybernetics Pattern

Recovers DOCX files left broken by subagents that:
(a) Unzipped DOCX to _docx_tmp/ and deleted the .docx
(b) Corrupted ZIP with missing [Content_Types].xml
(c) Applied duplicate text via sed on XML

Usage: python recover-subagent-docx.py

Pattern: find clean backup → apply python-docx patches → verify
"""

from docx import Document
from docx.shared import Pt
import os, shutil, glob

def find_clean_backup(docx_dir, pattern_hint):
    """Find the cleanest backup DOCX in a directory."""
    candidates = []
    for f in sorted(glob.glob(os.path.join(docx_dir, "*.docx"))):
        basename = os.path.basename(f)
        # Prefer: v4flash_final > patched > bak_*
        if "v4flash_final" in basename:
            candidates.insert(0, f)  # highest priority
        elif "bak" not in basename.lower() and "backup" not in basename.lower():
            if os.path.getsize(f) > 100000:  # >100KB = real DOCX
                candidates.append(f)
    return candidates[0] if candidates else None


if __name__ == "__main__":
    import sys
    
    # Configuration — edit these paths per session
    CONFIGS = {
        "v63": {
            "dir": r"<YOUR_HOME>\Desktop\右手中微子凝聚与时间荷对偶论文",
            "target": "Unified_Neutrino_Condensation_V63.docx",
            "pattern": "V63"
        },
        "v17": {
            "dir": r"<YOUR_HOME>\Desktop\六维流形时空理论",
            "target": "6D_Spacetime_Phase_Differentiation_Expanded_V17.docx",
            "pattern": "V17"
        },
        "v16": {
            "dir": r"<YOUR_HOME>\<PAPER_DIR>",
            "target": "paper_triple_gw_v16.docx",
            "pattern": "v16"
        },
    }
    
    target = sys.argv[1] if len(sys.argv) > 1 else "v63"
    cfg = CONFIGS.get(target, CONFIGS["v63"])
    
    target_path = os.path.join(cfg["dir"], cfg["target"])
    
    # Step 1: Check if target is valid
    is_valid = False
    if os.path.exists(target_path):
        try:
            doc = Document(target_path)
            is_valid = len(doc.paragraphs) > 5
            print(f"Target OK: {target_path} ({len(doc.paragraphs)} paragraphs)")
        except Exception as e:
            print(f"Target CORRUPT: {e}")
            is_valid = False
    
    if not is_valid:
        # Step 2: Find clean backup
        backup = find_clean_backup(cfg["dir"], cfg["pattern"])
        if backup:
            print(f"Restoring from backup: {backup}")
            shutil.copy2(backup, target_path)
            # Verify
            doc = Document(target_path)
            print(f"Restored: {len(doc.paragraphs)} paragraphs")
        else:
            print(f"ERROR: No clean backup found in {cfg['dir']}")
            sys.exit(1)
    
    print(f"Recovery complete: {target_path}")
    print(f"Ready for python-docx patch application.")
