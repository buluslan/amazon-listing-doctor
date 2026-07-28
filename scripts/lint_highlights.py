#!/usr/bin/env python3
"""lint_highlights.py — 校验 item_highlights 字段。

检查项：
  1. ≤ max_chars(125) 字符
  2. ≥ min_short_clauses(3) 短句（按 ; ； , ， | ｜ 换行 分隔）
  3. 不完全重复标题文本（标题已有词出现不算违规；完全重复标题文本则 WARN）

输入：{item_highlights, title, language}
输出：stdout 单个 JSON 对象；退出码 0=全通过 / 1=有 FAIL。
"""

import sys
import json
import argparse
import re
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# 配置加载
# --------------------------------------------------------------------------- #
def _load_rules():
    """从 references/rules.json 读取规则；缺失则返回空 dict（用默认值兜底）。"""
    rules_path = SKILL_ROOT / "references" / "rules.json"
    if rules_path.exists():
        return json.loads(rules_path.read_text(encoding="utf-8"))
    return {}


# --------------------------------------------------------------------------- #
# 纯工具函数
# --------------------------------------------------------------------------- #
def _normalize_text(s):
    """归一化文本：去除所有非字母数字/中文的字符（空格、标点、分隔符），并小写。

    用于判断 highlights 与 title 是否“实质相同”。
    """
    # 保留 a-z A-Z 0-9 与 CJK 统一汉字，其余全部去除
    return re.sub(r"[^a-zA-Z0-9一-鿿]", "", s).lower()


def _split_clauses(highlights):
    """按常见分隔符切分 highlights 为短句列表，过滤空段。

    支持分隔符：; ； , ， | ｜ 以及换行。
    """
    parts = re.split(r"[;；,，|｜\n\r]+", highlights)
    return [p.strip() for p in parts if p.strip()]


# --------------------------------------------------------------------------- #
# 核心纯函数
# --------------------------------------------------------------------------- #
def run(data):
    """校验 item_highlights，返回结果 dict（纯函数，无副作用）。

    Args:
        data: dict，含 item_highlights / title / language。

    Returns:
        dict 结构：
        {field, value, char_count, clause_count, checks, compliant, fix_suggestions}
    """
    rules = _load_rules()
    h_rules = rules.get("highlights", {})
    max_chars = h_rules.get("max_chars", 125)
    min_clauses = h_rules.get("min_short_clauses", 3)

    highlights = data.get("item_highlights", "") or ""
    title = data.get("title", "") or ""

    char_count = len(highlights)
    clauses = _split_clauses(highlights)
    clause_count = len(clauses)

    checks = {}
    suggestions = []

    # ---- 检查 1：字符数上限 ----
    char_status = "PASS" if char_count <= max_chars else "FAIL"
    checks["char_limit"] = {
        "status": char_status,
        "actual": char_count,
        "limit": max_chars,
    }
    if char_status == "FAIL":
        suggestions.append(
            f"item_highlights 超过 {max_chars} 字符（当前 {char_count}），"
            f"请精简至 {max_chars} 字符以内。"
        )

    # ---- 检查 2：最少短句数 ----
    clause_status = "PASS" if clause_count >= min_clauses else "FAIL"
    checks["min_clauses"] = {
        "status": clause_status,
        "actual": clause_count,
        "limit": min_clauses,
    }
    if clause_status == "FAIL":
        suggestions.append(
            f"item_highlights 短句数不足（当前 {clause_count}，要求 ≥{min_clauses}），"
            f"建议用分号/逗号分隔多个差异化卖点短句。"
        )

    # ---- 检查 3：与标题去重（WARN 级，不计入 compliant） ----
    distinct_status = "PASS"
    distinct_detail = {}
    if title and highlights:
        h_norm = _normalize_text(highlights)
        t_norm = _normalize_text(title)
        if h_norm and t_norm:
            # 完全相同，或一方完整包含另一方（即把标题整段搬过来/反之）
            same = h_norm == t_norm
            contained = (t_norm in h_norm) or (h_norm in t_norm)
            if same or contained:
                distinct_status = "WARN"
                distinct_detail = {
                    "reason": "item_highlights 与 title 文本高度重复，"
                              "建议改写为差异化的卖点短句，避免简单复述标题。"
                }
    checks["distinct_from_title"] = {
        "status": distinct_status,
        **distinct_detail,
    }

    # ---- 汇总合规：仅 FAIL 影响合规，WARN 不影响 ----
    compliant = all(c.get("status") != "FAIL" for c in checks.values())

    return {
        "field": "item_highlights",
        "value": highlights,
        "char_count": char_count,
        "clause_count": clause_count,
        "checks": checks,
        "compliant": compliant,
        "fix_suggestions": suggestions,
    }


# --------------------------------------------------------------------------- #
# IO 层（CLI）
# --------------------------------------------------------------------------- #
def load_input():
    """统一输入：--data > --file > stdin。"""
    parser = argparse.ArgumentParser(description="校验 item_highlights 字段")
    parser.add_argument("--data", help="inline JSON 字符串")
    parser.add_argument("--file", help="JSON 文件路径")
    a = parser.parse_args()
    if a.data:
        return json.loads(a.data)
    if a.file:
        return json.loads(Path(a.file).read_text(encoding="utf-8"))
    if not sys.stdin.isatty():
        return json.loads(sys.stdin.read())
    return {}


def main():
    data = load_input()
    result = run(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("compliant", True) else 1)


if __name__ == "__main__":
    main()
