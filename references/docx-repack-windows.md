# DOCX Repack on Windows (MSYS/No-zip Workaround)

## Problem

Subagents (via `delegate_task`) may need to edit DOCX files but cannot do so with `patch` directly on the binary `.docx`. They unzip the DOCX to `_docx_tmp/`, edit `word/document.xml`, but then cannot repack because MSYS/bash on Windows has no `zip` command. The original `.docx` may be deleted or left as a broken directory.

## Symptoms

- Main DOCX file missing: `ls *.docx` returns only `*_BACKUP.docx` or nothing
- `_docx_tmp/` directory exists with `word/document.xml` (modified)
- Subagent reports "DOCX fixes applied to XML but needs repacking"

## Fix: Python zipfile repacking

```python
import zipfile, os, shutil

def repack_from_backup(backup_path, target_path, tmp_xml_dir):
    """Create target DOCX from backup, replacing entries with modified versions"""
    modified_xml = os.path.join(tmp_xml_dir, 'word', 'document.xml')
    if not os.path.exists(modified_xml):
        print(f"ERROR: {modified_xml} not found")
        return False
    
    # Read all entries from backup
    with zipfile.ZipFile(backup_path, 'r') as zin:
        all_files = zin.namelist()
    
    # Write new DOCX, using modified files where available
    with zipfile.ZipFile(target_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for fname in all_files:
            mod_path = os.path.join(tmp_xml_dir, fname)
            if os.path.exists(mod_path):
                print(f"  Modified: {fname}")
                zout.write(mod_path, fname)
            else:
                with zipfile.ZipFile(backup_path, 'r') as zin2:
                    zout.writestr(fname, zin2.read(fname))
    
    return True

# Usage example:
backup = r"C:\...\paper_V17_BACKUP.docx"
target = r"C:\...\paper_V17.docx"
tmp_dir = r"C:\...\_docx_tmp"

repack_from_backup(backup, target, tmp_dir)
```

## Critical Checks After Repacking

1. Verify the new DOCX opens in Word/LibreOffice
2. `grep` for fixed values to confirm edits took effect
3. Compare line counts: `wc -l` on extracted `word/document.xml` should differ from pre-fix
4. Delete `_docx_tmp/` after successful repacking

## Prevention

Before spawning subagents for DOCX edits, note in the task context:
"Use Python zipfile (not shell `zip`) to repack DOCX after XML edits. If you cannot repack, leave the modified XML at `_docx_tmp/word/document.xml` and I will repack after you finish."
