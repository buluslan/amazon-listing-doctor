#!/usr/bin/env python3
"""alexa_question_gen.py — ALEXA AEO 买家问题生成/加载。

ALEXA AEO（Answer Engine Optimization）模式下，不再扫
"场景/人群/限制词覆盖"，而是模拟真实买家向 AI 购物助手（Alexa for Shopping /
Rufus）提问，判断 listing 能否被回答/推荐。本模块提供问题池。

两个来源：
  - load_question_bank(category)：读 references/alexa_question_bank.json，返回该
    类目手工精写的真实买家问句（缺类目 fallback _common）。
  - generate_from_lexicon(category)：读 references/alexa_lexicon.json 的类目分词
    （scene/audience/limitation）+ 口语模板扩写，作为自动补充/扩展机制。

alexa_check.py 的 get_agent_prompt() 调用本模块取问题池，喂给 Agent 做 AEO 判断。

用法：
  from alexa_question_gen import load_question_bank
  questions = load_question_bank("Electronics")

  # CLI: 打印某类目问题池
  python scripts/alexa_question_gen.py --category Electronics
"""

import sys
import json
import argparse
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
QUESTION_BANK_PATH = SKILL_ROOT / "references" / "alexa_question_bank.json"
LEXICON_PATH = SKILL_ROOT / "references" / "alexa_lexicon.json"

# 模板扩写：从种子词生成真实口吻问句（aspect × starter 模板）
_SCENE_TEMPLATES = [
    "Is this good for {seed}?",
    "Can I use this for {seed}?",
]
_AUDIENCE_TEMPLATES = [
    "Is this good for {seed}?",
    "Will this work well for {seed}?",
]
_LIMITATION_TEMPLATES = [
    "Is this really {seed}?",
]


def _load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_question_bank(category=None):
    """读 alexa_question_bank.json，按 category 取问题池。

    category 命中类目块 → 返回类目问句；否则返回 _common 通用问句。
    """
    bank = _load_json(QUESTION_BANK_PATH)
    common = bank.get("_common", []) if isinstance(bank.get("_common"), list) else []
    if category and isinstance(bank.get(category), list) and bank[category]:
        return list(bank[category])
    return list(common)


def generate_from_lexicon(category=None):
    """从 alexa_lexicon.json 类目分词扩写问句（自动补充机制）。

    把 scene/audience/limitation 种子词套入口语模板生成真实买家问句。
    与 load_question_bank 的手工精写问句互补，可用于扩展问题池或覆盖更多品类。
    """
    lexicon = _load_json(LEXICON_PATH)
    common = lexicon.get("_common", {}) if isinstance(lexicon.get("_common"), dict) else {}
    cat_entry = (
        lexicon.get(category, {})
        if category and isinstance(lexicon.get(category), dict)
        else {}
    )

    def _dim_words(dim_key):
        # 类目词优先 + _common 兜底，按小写去重
        cval = list(cat_entry.get(dim_key) or [])
        bval = list(common.get(dim_key) or [])
        seen, merged = set(), []
        for w in cval + bval:
            wl = w.lower()
            if wl not in seen:
                seen.add(wl)
                merged.append(w)
        return merged

    questions = []
    for seed in _dim_words("scene"):
        for tpl in _SCENE_TEMPLATES:
            questions.append(tpl.format(seed=seed))
    for seed in _dim_words("audience"):
        for tpl in _AUDIENCE_TEMPLATES:
            questions.append(tpl.format(seed=seed))
    for seed in _dim_words("limitation"):
        for tpl in _LIMITATION_TEMPLATES:
            questions.append(tpl.format(seed=seed))
    return questions


def main():
    parser = argparse.ArgumentParser(description="ALEXA AEO buyer-question pool")
    parser.add_argument("--category", help="类目（缺省取 _common）")
    parser.add_argument(
        "--from-lexicon", action="store_true",
        help="改用 alexa_lexicon 种子词模板扩写（而非 question_bank 手工问句）",
    )
    parser.add_argument("--max", type=int, help="最多输出 N 条")
    a = parser.parse_args()

    if a.from_lexicon:
        qs = generate_from_lexicon(a.category)
    else:
        qs = load_question_bank(a.category)
    if a.max:
        qs = qs[: a.max]

    print(json.dumps({
        "category": a.category or "_common",
        "count": len(qs),
        "questions": qs,
    }, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
