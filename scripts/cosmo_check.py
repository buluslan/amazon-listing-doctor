#!/usr/bin/env python3
"""cosmo_check.py — COSMO 意图覆盖度评估（doctor 独占维度）。

读取 references/cosmo_ontology.json, 按 category 取本体 (缺类目时 fallback _common),
扫描 listing 全文, 算 use_case / audience / goal / constraint 四维度的概念覆盖度。

COSMO (亚马逊电商常识知识图谱, WWW 2024) 无官方质检权重 —— 本脚本是基于公开论文精神的
"概念覆盖率" 诊断, 不是官方 COSMO 分。输出:
  - score: 达标线加权 0-100 (对标 alexa, 友好可比)
  - coverage_ratio: 精确覆盖率 matched/total (诚实反映概念覆盖)
  - covered/missing_concepts: 每维已覆盖与缺失的概念清单 (可操作)
  - suggestions: 补概念建议

设计要点: goal 维度故意偏难 —— listing 通常堆属性词而不写"用户目标",
goal 覆盖率低正是诊断价值所在 (指出 listing 缺少意图层表达)。
"""

import sys
import json
import re
import argparse
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
ONTOLOGY_PATH = SKILL_ROOT / "references" / "cosmo_ontology.json"

# 四维度 (COSMO 论文常识分类; goal 为 COSMO 区别于 Alexa 的核心维度)
DIMENSIONS = ("use_case", "audience", "goal", "constraint")

# 各维度达标线: 命中 N 个不同概念 → 该维度满分
TARGET_USE_CASE = 3
TARGET_AUDIENCE = 2
TARGET_GOAL = 2
TARGET_CONSTRAINT = 2

# 四维权重 (和为 1.0); use_case 权重最高 (场景/用途是意图匹配主信号)
W_USE_CASE = 0.30
W_AUDIENCE = 0.25
W_GOAL = 0.25
W_CONSTRAINT = 0.20

_WEIGHTS = {
    "use_case": W_USE_CASE,
    "audience": W_AUDIENCE,
    "goal": W_GOAL,
    "constraint": W_CONSTRAINT,
}
_TARGETS = {
    "use_case": TARGET_USE_CASE,
    "audience": TARGET_AUDIENCE,
    "goal": TARGET_GOAL,
    "constraint": TARGET_CONSTRAINT,
}


# --------------------------- 工具函数 ---------------------------

def _load_ontology():
    """加载 cosmo_ontology.json。"""
    if not ONTOLOGY_PATH.exists():
        return {}
    return json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8"))


def _get_category_ontology(ontology, category):
    """按 category 取本体; category 优先, 缺失维度回退 _common。

    返回 (merged_dict, used_fallback_flag)。
    merged_dict keys: use_case / audience / goal / constraint。
    """
    common = ontology.get("_common", {}) if isinstance(ontology.get("_common"), dict) else {}
    cat_entry = ontology.get(category, {}) if isinstance(ontology.get(category), dict) else {}

    merged = {}
    fallback_used = False
    for dim in DIMENSIONS:
        cval = cat_entry.get(dim)
        bval = common.get(dim)
        if cval:
            merged[dim] = list(cval)
        elif bval:
            merged[dim] = list(bval)
            fallback_used = True
        else:
            merged[dim] = []
    return merged, fallback_used


def _collect_listing_text(data):
    """合并 COSMO 意图来源全文: title/highlights/bullets/description/backend/attributes。"""
    parts = []
    for key in ("title", "item_highlights", "description", "backend_search_terms"):
        v = data.get(key)
        if v:
            parts.append(str(v))
    bullets = data.get("bullets") or []
    for b in bullets:
        if isinstance(b, dict):
            parts.append(str(b.get("header", "")))
            parts.append(str(b.get("body", "")))
        elif isinstance(b, str):
            parts.append(b)
    attrs = data.get("attributes") or {}
    if isinstance(attrs, dict):
        for v in attrs.values():
            if v:
                parts.append(str(v))
    return " ".join(parts).lower()


def _word_in_text(word, text):
    """概念词是否在文本中出现 (substring 匹配, 覆盖单复数/词形变化; 大小写不敏感)。

    COSMO 概念是用户意图/利益词, listing 常以变形出现
    (comfortable/comforting/comforts, commute/commutes/commuting),
    用 substring 比严格词边界更能捕获意图表达。概念词已精选避免短词歧义。
    """
    return word.lower() in text


def _scan_dimension(words, text):
    """扫描一个维度的概念词表, 返回 (matched, missing)。"""
    matched, missing = [], []
    for w in words:
        (matched if _word_in_text(w, text) else missing).append(w)
    return matched, missing


# --------------------------- 核心纯函数 ---------------------------

def run(data):
    """COSMO 意图覆盖度评估。

    Args:
        data: listing dict (需含 category 与若干文本字段)。

    Returns:
        dict, 含:
          score(0-100 达标线评分), coverage_ratio(0-1 精确覆盖率),
          covered_concepts(dict per dim), missing_concepts(dict per dim),
          per_dimension(dict per dim {covered,total,ratio}),
          suggestions(list), category, ontology_source, used_fallback,
          targets, weights。
    """
    if not isinstance(data, dict):
        data = {}

    ontology = _load_ontology()
    category = (data.get("category") or "").strip()
    cat_ont, fallback = _get_category_ontology(ontology, category)
    text = _collect_listing_text(data)

    covered = {}
    missing = {}
    per_dim = {}
    total_matched = 0
    total_concepts = 0

    for dim in DIMENSIONS:
        words = cat_ont.get(dim, [])
        matched, miss = _scan_dimension(words, text)
        covered[dim] = matched
        missing[dim] = miss
        total = len(words)
        cnt = len(matched)
        total_matched += cnt
        total_concepts += total
        per_dim[dim] = {
            "covered": cnt,
            "total": total,
            "ratio": round(cnt / total, 4) if total else 0.0,
        }

    # 达标线子分 (命中目标数即满分), 加权 → score
    dim_score = {}
    for dim in DIMENSIONS:
        words = cat_ont.get(dim, [])
        target = _TARGETS[dim]
        if not words:
            dim_score[dim] = 0.0
        else:
            dim_score[dim] = min(len(covered[dim]) / target, 1.0)
    score = sum(dim_score[d] * _WEIGHTS[d] for d in DIMENSIONS) * 100
    score = round(score)

    # 精确覆盖率 (诚实指标: 实际命中 / 概念总数)
    coverage_ratio = round(total_matched / total_concepts, 4) if total_concepts else 0.0

    # 补概念建议 (缺失维度, 每类最多 4 个示例)
    suggestions = []
    label_map = {
        "use_case": "use-case / scenario",
        "audience": "audience / persona",
        "goal": "user goal / outcome (why people buy)",
        "constraint": "constraint / qualifier",
    }
    for dim in DIMENSIONS:
        if missing[dim]:
            suggestions.append(
                f"add {label_map[dim]} concept e.g. {'/'.join(missing[dim][:4])}"
            )

    # 本体来源标签
    if category and category in ontology:
        source = category
    elif fallback:
        source = "_common (fallback)"
    else:
        source = "_common" if "_common" in ontology else "none"

    return {
        "score": score,
        "coverage_ratio": coverage_ratio,
        "covered_concepts": covered,
        "missing_concepts": missing,
        "per_dimension": per_dim,
        "suggestions": suggestions,
        "category": category or None,
        "ontology_source": source,
        "used_fallback": fallback,
        "targets": dict(_TARGETS),
        "weights": dict(_WEIGHTS),
    }


# --------------------------- CLI ---------------------------

def load_input():
    parser = argparse.ArgumentParser(description="COSMO intent-coverage check")
    parser.add_argument("--data", help="inline JSON")
    parser.add_argument("--file", help="path to JSON file")
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
    # 评分类脚本始终退出 0
    sys.exit(0)


if __name__ == "__main__":
    main()
