#!/usr/bin/env python3
"""alexa_check.py — Alexa 可发现性评估。

读取 references/alexa_lexicon.json, 按 category 取词库 (缺类目时 fallback _common),
扫描 listing 全文, 算场景/人群/限制词三维度覆盖 → Alexa 可发现性 0-100 + 建议补充词。
"""

import sys
import json
import re
import argparse
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
LEXICON_PATH = SKILL_ROOT / "references" / "alexa_lexicon.json"

# 各维度达标线: 匹配到 N 个不同词 → 该维度满分 (Alexa 发现只需少量场景/人群信号即可命中)
TARGET_SCENE = 2
TARGET_AUDIENCE = 1
TARGET_LIMIT = 2

# 三维度权重 (和为 1.0); 场景权重最高 (Alexa 问答多基于 "what should I use X for")
W_SCENE = 0.40
W_AUDIENCE = 0.30
W_LIMIT = 0.30


# --------------------------- 工具函数 ---------------------------

def _load_lexicon():
    """加载 alexa_lexicon.json。"""
    if not LEXICON_PATH.exists():
        return {}
    return json.loads(LEXICON_PATH.read_text(encoding="utf-8"))


def _get_category_lexicon(lexicon, category):
    """按 category 取词库; category 优先, 缺失维度回退 _common。

    返回 (merged_dict, used_fallback_flag)。
    merged_dict keys: scene / audience / limitation。
    """
    common = lexicon.get("_common", {}) if isinstance(lexicon.get("_common"), dict) else {}
    cat_entry = lexicon.get(category, {}) if isinstance(lexicon.get(category), dict) else {}

    merged = {}
    fallback_used = False
    for dim in ("scene", "audience", "limitation"):
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
    """合并 Alexa 可发现来源全文: title/highlights/bullets/description/backend/attributes。"""
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
    """词/短语是否在文本中出现 (词边界匹配, 大小写不敏感)。"""
    pattern = r"\b" + re.escape(word.lower()) + r"\b"
    return re.search(pattern, text) is not None


def _scan_dimension(words, text):
    """扫描一个维度的词表, 返回 (matched, missing)。"""
    matched, missing = [], []
    for w in words:
        (matched if _word_in_text(w, text) else missing).append(w)
    return matched, missing


# --------------------------- 核心纯函数 ---------------------------

def run(data):
    """Alexa 可发现性评估。

    Args:
        data: listing dict (需含 category 与若干文本字段)。

    Returns:
        dict, 至少含:
          score(0-100), scene_coverage(list), audience_coverage(list),
          limit_coverage(list), missing_scene(list), suggestions(list)。
    """
    lexicon = _load_lexicon()
    category = (data.get("category") or "").strip()
    cat_lex, fallback = _get_category_lexicon(lexicon, category)
    text = _collect_listing_text(data)

    scene_words = cat_lex.get("scene", [])
    audience_words = cat_lex.get("audience", [])
    limit_words = cat_lex.get("limitation", [])

    scene_matched, scene_missing = _scan_dimension(scene_words, text)
    aud_matched, aud_missing = _scan_dimension(audience_words, text)
    lim_matched, lim_missing = _scan_dimension(limit_words, text)

    # 各维度 0-1 子分 (命中达标线即满分)
    scene_score = min(len(scene_matched) / TARGET_SCENE, 1.0) if scene_words else 0.0
    aud_score = min(len(aud_matched) / TARGET_AUDIENCE, 1.0) if audience_words else 0.0
    lim_score = min(len(lim_matched) / TARGET_LIMIT, 1.0) if limit_words else 0.0

    score = (scene_score * W_SCENE + aud_score * W_AUDIENCE + lim_score * W_LIMIT) * 100
    score = round(score)

    # 建议补充词 (按缺失维度, 每类最多给 3 个示例, 用 "/" 拼接)
    suggestions = []
    if scene_missing:
        suggestions.append(f"add scene word e.g. {'/'.join(scene_missing[:3])}")
    if aud_missing:
        suggestions.append(f"add audience word e.g. {'/'.join(aud_missing[:3])}")
    if lim_missing:
        suggestions.append(f"add limitation word e.g. {'/'.join(lim_missing[:3])}")

    # 词库来源标签
    if category and category in lexicon:
        source = category
    elif fallback:
        source = "_common (fallback)"
    else:
        source = "_common" if "_common" in lexicon else "none"

    return {
        # 必填字段
        "score": score,
        "scene_coverage": scene_matched,
        "audience_coverage": aud_matched,
        "limit_coverage": lim_matched,
        "missing_scene": scene_missing,
        "suggestions": suggestions,
        # 诊断扩展字段
        "missing_audience": aud_missing,
        "missing_limit": lim_missing,
        "category": category or None,
        "lexicon_source": source,
        "used_fallback": fallback,
        "targets": {"scene": TARGET_SCENE, "audience": TARGET_AUDIENCE, "limit": TARGET_LIMIT},
        "weights": {"scene": W_SCENE, "audience": W_AUDIENCE, "limit": W_LIMIT},
    }


# --------------------------- CLI ---------------------------

def load_input():
    parser = argparse.ArgumentParser(description="Alexa discoverability check")
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
