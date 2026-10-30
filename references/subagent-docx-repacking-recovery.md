# Subagent DOCX Repacking — Parent-Side Recovery Pattern

**Discovered**: 2026-08-07 | V16×V17×V63 hybrid review fix session

## Problem

When `delegate_task` subagents edit DOCX files by unzipping them, modifying `word/document.xml`, and attempting to repack, they often hit `max_iterations` before completing the repack step. Common failure mode:

```
⚠️ File-mutation verifier: 1 file(s) were NOT modified this turn despite any wording
above that may suggest otherwise. [patch] Could not find a match for old_string in the file
```

And the DOCX file is left in a broken/unzipped state.

## Root Causes

1. **MSYS/git-bash lacks `zip`**: Windows MSYS terminal has no `zip` command — the subagent's `zip -r` call fails silently
2. **Subagent `max_iterations` exhaustion**: DOCX editing is token-intensive (reading binary, searching XML, patching). 50-iteration subagents commonly exhaust before repacking
3. **Unzipped state corruption**: After unzipping, the original `.docx` may be deleted, leaving only the extracted `_docx_tmp/` directory

## Recovery Pattern (parent-side)

After subagents complete, the parent agent must:

### 1. Check for broken DOCX files

```bash
# Look for backup files and unzipped temp directories
ls *_BACKUP.docx _docx_tmp/word/document.xml docx_temp/word/document.xml
```

### 2. Restore + Repack using Python zipfile

```python
import zipfile, os, shutil

def repack_from_backup(backup_path, target_path, tmp_xml_dir):
    modified_xml = os.path.join(tmp_xml_dir, 'word', 'document.xml')
    
    with zipfile.ZipFile(backup_path, 'r') as zin:
        all_files = zin.namelist()
    
    with zipfile.ZipFile(target_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for fname in all_files:
            mod_path = os.path.join(tmp_xml_dir, fname)
            if os.path.exists(mod_path):
                zout.write(mod_path, fname)  # use edited version
            else:
                zout.writestr(fname, zin.read(fname))  # from backup
    
# Usage
repack_from_backup(
    "6D_Spacetime_Phase_Differentiation_Expanded_V17_BACKUP.docx",
    "6D_Spacetime_Phase_Differentiation_Expanded_V17.docx",
    "_docx_tmp"
)
```

### 3. Verify repacked DOCX

```python
doc = Document(target_path)
# Check that key text changes are present
```

## Prevention (for subagent context)

When dispatching subagents for DOCX editing, add to their context:

> If `zip` is unavailable, do NOT attempt shell repacking. Instead, leave the modified `word/document.xml` in `_docx_tmp/` and report the path. The parent agent will repack using Python `zipfile`.

This lets subagents focus on XML editing (what they're good at) and delegates the platform-dependent repacking to the parent.
