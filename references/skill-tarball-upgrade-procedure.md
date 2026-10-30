# 技能 tar 包合并式升级程序（scientific-discovery-proof 本机安装专用）

适用：后续 v2.20+ 升级包（如 `<WORK_DIR>/scientific-discovery-proof.tar.gz`）落地时重复此流程。2026-10-12 已用此流程完成 v2.10.0 → v2.19.0。

## 为什么不能整目录覆盖

本机安装含升级包之外的长期资产，整目录删除覆盖会全部丢失：

- `maf_core/`、`config/`、`examples/`、`maf_bridge.py`（MAF 符号审计桥）
- scripts 特有：`jspace_bridge.py`、`mathlib_api_lookup.py`、`ppe_phase35_integration_snippet.py`、`recover-subagent-docx.py`
- references/ 约 95 个旧文档（升级包只携带最近 ~23 个）

## 步骤

1. **列包清单**：`tar -tzf <WORK_DIR>/scientific-discovery-proof.tar.gz`。MSYS 下必须用 `/d/` 风格路径，写 `D:/...` 会报 `Cannot connect to D`（tar 把盘符当远程主机名）。
2. **解压到临时目录**：`mkdir -p <WORK_DIR>/sdp_upgrade_tmp && tar -xzf <包> -C <WORK_DIR>/sdp_upgrade_tmp`
3. **交集盘点**：`comm -12 <(ls 旧/references | sort) <(ls 新/references | sort)`，scripts 同理。确定哪些同名文件会被新版覆盖。
4. **备份**：`cd /d/hermes_home/skills && tar --exclude=__pycache__ -czf scientific-discovery-proof.bak-<旧版本>.tar.gz scientific-discovery-proof`。注意 `--exclude` 必须放在操作数之前，否则报 "has no effect" 且退出失败。
5. **合并（严禁删除现有目录）**：
   ```bash
   SRC=<临时目录>/scientific-discovery-proof; DST=/d/hermes_home/skills/scientific-discovery-proof
   cp "$SRC/SKILL.md" "$SRC/README.md" "$DST/" && cp "$SRC"/scripts/* "$DST/scripts/" && cp "$SRC"/references/* "$DST/references/"
   ```
6. **验证**：
   - `grep -m1 "^version:" DST/SKILL.md` 确认版本号
   - 文件数核算：旧数 + 新包数 − 同名交集数 = 合并后数（例：scripts 7+25−3=29，references 96+23−1=118）
   - `cd DST/scripts && py -m py_compile *.py` 全量编译。本机 `python` 命令是 Microsoft Store stub（exit 49 静默假死），必须用 `py` launcher；编译后清 `__pycache__`
7. **回写本文件**：更新版本记录行；若特有资产清单变化（新脚本被上游收编、新增本地脚本），同步修正上表。

## 版本记录

- 2026-10-12: v2.10.0 → v2.19.0。备份 `scientific-discovery-proof.bak-v2.10.0.tar.gz`（279K）。新增 4 项 prove2me 二次评估落地（conjecture_spec_check / 退化输入检测 / disproof_probe / Scout 拒绝方记录）。29 脚本 py_compile 全通过。
