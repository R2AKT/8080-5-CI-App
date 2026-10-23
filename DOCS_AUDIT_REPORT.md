# Documentation Audit Report — i8080-5 CI v2.1.15
**Date:** 2026-10-23 | **Auditor:** AI subagent

## 1. README.md
- **Version:** ✅ 2.1.15 — matches `version.py`.
- **Test count (WRONG):** README states *"964 passed, 0 failed"*. Actual test run: **978 passed, 0 failed** across **38 test files**. Needs update.
- **"60+ test files":** The `tests/` directory does contain 60+ `.py` files (helpers, GUI smoke, etc.), but only **38** are executed by `run_tests.py`. The phrasing is technically defensible but misleading.
- **"256 instructions":** Refers to the combined i8080+i8085 set. OPCODE_REFERENCE.md says 246 for 8080 alone. Not wrong, but potentially confusing without clarification.

## 2. ASSEMBLER_GUIDE.md
- **Section 3.4.1 (STAX H / LDAX H aliases):** ✅ **CORRECT**. Verified against:
  - `OPCODE_REFERENCE.md`: 0x22=SHLD, 0x2A=LHLD; STAX/LDAX exist only for B (0x02/0x0A) and D (0x12/0x1A). No H variant in the canonical table.
  - `assemble8080/assembler.py` L1391-1394: STAX H → 0x77 (MOV M,A), LDAX H → 0x7E (MOV A,M). Exact match with the doc.
- All other described features (directives, preprocessor, linker, librarian, map files, CLI) match actual code structure.

## 3. USER_GUIDE.md
- **Version mismatch (WRONG):** Header says *"Version / Версия: 2.8, Date / Дата: 2026-09-29"*. Actual project version is **2.1.15** (2026-10-23). The "2.8" appears to be a stale internal document revision number, not aligned with the project version. **Must be updated.**
- **EN/RU consistency:** ✅ Sections are parallel and consistent (verified overview, features list, notes for v2.1–v2.8).
- **"256 instructions":** Same as README — combined 8080+8085 count.

## 4. CHANGES.md (v2.1.15 entry)
- **Test count (WRONG):** Entry states *"956/0 (run_tests, 36 files)"*. Actual: **978/0 (38 files)**. The 22-test gap (test_watch_ds.py: 14, test_hex_tail.py: 8) and 2 extra files were added after the changelog entry was written.
- **Feature descriptions:** ✅ Accurate — librarian, linker library resolution, sequential ORIGIN layout, DATA/CODE classification in map, auto-watch variables all verified against code.
- **Documentation references:** Correctly notes updates to ASSEMBLER_GUIDE.md, USER_GUIDE.md, README.md.

## 5. OPCODE_REFERENCE.md
- **SINGLE SOURCE OF TRUTH marking:** ✅ Clearly stated in the header and reinforced in ASSEMBLER_GUIDE.md.
- **Internal inconsistency (MINOR):** L20 says *"243 инструкций 8080"* (verification method), L50 says *"246 команд"* (table title). The difference of 3 is unexplained — likely counting of undocumented/illegal opcodes. Should be harmonized.
- **STAX/LDAX/SHLD/LHLD entries:** ✅ Correct (L255-267).

## 6. Cross-References
- ✅ All referenced documents exist: USER_GUIDE.md, MCP_GUIDE.md, SCRIPTS_GUIDE.md, ASSEMBLER_GUIDE.md, OPCODE_REFERENCE.md, ANALYSIS.md, CHANGES.md, I18N_AUDIT.md, Addendum.txt, assembler_example/README.md.
- ✅ ASSEMBLER_GUIDE.md → OPCODE_REFERENCE.md: valid, correctly labeled as canonical source.

## Summary of Issues Found
| # | File | Severity | Issue |
|---|------|----------|-------|
| 1 | README.md | **HIGH** | Test count wrong: "964" → should be **978** |
| 2 | CHANGES.md | **HIGH** | Test count wrong: "956/0, 36 files" → should be **978/0, 38 files** |
| 3 | USER_GUIDE.md | **HIGH** | Version header "2.8 / 2026-09-29" → should be **2.1.15 / 2026-10-23** |
| 4 | OPCODE_REFERENCE.md | LOW | Internal: "243" (L20) vs "246" (L50) — unexplained discrepancy |
