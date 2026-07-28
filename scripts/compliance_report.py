#!/usr/bin/env python3
# compliance_report.py —— 汇总检查脚本，输出最终体检报告。
#
# 行为：通过 import 同目录其他脚本的 run() 函数汇总（不用 subprocess）。
# 依赖（运行时解析，缺一不崩溃，对应字段回退到 output-template.json 空值）：
#   lint_title / lint_highlights / lint_bullets / lint_backend
#   cdq_score / indexability / alexa_check / check_keyword_layering
#
# 输入：完整 listing（stdin JSON 优先 / --data / --file）
# 输出：stdout 一个 JSON 对象（完整 output-template.json 结构）
# 退出码：0=总体合规 / 1=有 FAIL

import sys
import json
import argparse
import importlib
from datetime import datetime
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent

# 插入脚本目录到 sys.path，便于 import 同目录其他脚本
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _try_import(name):
    """安全 import 一个同目录脚本模块，失败返回 None（其他脚本可能尚未生成）。"""
    try:
        return importlib.import_module(name)
    except Exception:
        return None


def _safe_run(module, data):
    """调用 module.run(data)；模块缺失或抛错返回 None，不中断汇总。"""
    if module is None:
        return None
    run_fn = getattr(module, "run", None)
    if run_fn is None:
        return None
    try:
        return run_fn(data)
    except Exception as e:
        return {"error": f"{module.__name__}.run failed: {e}"}


def _load_template():
    """读取 assets/output-template.json 作为空值骨架。"""
    tpl_path = SKILL_ROOT / "assets" / "output-template.json"
    if tpl_path.exists():
        return json.loads(tpl_path.read_text(encoding="utf-8"))
    return {}


def _count_checks(report_sections):
    """统计 lint 段 checks 中 PASS / FAIL / WARN 数量。

    只统计 dict 型 check 的 status 字段；顶层 compliant 不在此处计。
    """
    passed = failed = warnings = 0
    for sec in report_sections:
        if not isinstance(sec, dict):
            continue
        checks = sec.get("checks", {})
        if not isinstance(checks, dict):
            continue
        for chk in checks.values():
            if not isinstance(chk, dict):
                continue
            status = str(chk.get("status", "")).upper()
            if status == "PASS":
                passed += 1
            elif status == "FAIL":
                failed += 1
            elif status == "WARN":
                warnings += 1
    return passed, failed, warnings


def _overall_compliant(sections):
    """所有含 compliant 字段的 lint 段全部 True，才算总体合规。

    attributes/variation 段也参与：attributes.compliant 看 filled_ratio。
    """
    for sec in sections:
        if isinstance(sec, dict) and "compliant" in sec:
            if not sec["compliant"]:
                return False
    return True


def _collect_critical(lint_sections):
    """收集 FAIL 级别检查项作为 critical_issues。"""
    critical = []
    for sec in lint_sections:
        if not isinstance(sec, dict):
            continue
        label = sec.get("field", "unknown")
        checks = sec.get("checks", {})
        if not isinstance(checks, dict):
            continue
        for chk_name, chk in checks.items():
            if isinstance(chk, dict) and str(chk.get("status", "")).upper() == "FAIL":
                critical.append({
                    "field": label,
                    "check": chk_name,
                    "detail": chk,
                })
    return critical


def _collect_action_items(title_r, hl_r, bul_r, bak_r, cdq_r, idx_r, alexa_r, kw_r):
    """汇总各段的 fix/improve/suggestion/risks/duplicates 为 action_items 列表。"""
    items = []
    # lint 段的 fix_suggestions
    for label, sec in (
        ("title", title_r), ("highlights", hl_r),
        ("bullets", bul_r), ("backend", bak_r),
    ):
        if isinstance(sec, dict):
            for s in sec.get("fix_suggestions", []) or []:
                items.append({"source": label, "action": str(s)})
    # cdq 改进建议
    if isinstance(cdq_r, dict):
        for s in cdq_r.get("improve_suggestions", []) or []:
            items.append({"source": "cdq", "action": str(s)})
    # indexability 风险
    if isinstance(idx_r, dict):
        for r in idx_r.get("risks", []) or []:
            items.append({"source": "indexability", "action": str(r)})
    # alexa 建议
    if isinstance(alexa_r, dict):
        for s in alexa_r.get("suggestions", []) or []:
            items.append({"source": "alexa", "action": str(s)})
    # 关键词分层重复
    if isinstance(kw_r, dict):
        for d in kw_r.get("duplicates_across_layers", []) or []:
            items.append({"source": "keyword", "action": str(d)})
    return items


def run(data):
    """汇总 8 个检查脚本，返回完整 output-template 结构。

    Args:
        data: 完整 listing dict。

    Returns:
        dict: 与 assets/output-template.json 结构对齐的最终报告。
        任一依赖脚本缺失或报错，对应字段回退到模板空值，不中断汇总。
    """
    # 延迟 import：运行时解析，其他脚本可能尚未生成
    lint_title = _try_import("lint_title")
    lint_highlights = _try_import("lint_highlights")
    lint_bullets = _try_import("lint_bullets")
    lint_backend = _try_import("lint_backend")
    cdq_score = _try_import("cdq_score")
    indexability = _try_import("indexability")
    alexa_check = _try_import("alexa_check")
    check_keyword_layering = _try_import("check_keyword_layering")
    image_check = _try_import("image_check")
    cosmo_check = _try_import("cosmo_check")
    title_triage = _try_import("title_triage")

    title_r = _safe_run(lint_title, data)
    hl_r = _safe_run(lint_highlights, data)
    bul_r = _safe_run(lint_bullets, data)
    bak_r = _safe_run(lint_backend, data)

    # 图片检查：先跑，把真实缺陷评分注入 data 供 cdq_score 使用
    has_images = isinstance(data, dict) and bool(data.get("images"))
    img_r = _safe_run(image_check, data) if has_images else None
    # 始终用副本，避免注入污染原始 data
    data_for_cdq = dict(data) if isinstance(data, dict) else {}
    if isinstance(img_r, dict) and "cdq_image_score" in img_r:
        data_for_cdq["image_cdq_score"] = img_r["cdq_image_score"]
        data_for_cdq["image_defects"] = img_r.get("defects", [])
        data_for_cdq["images_count"] = img_r.get("image_count", data.get("images_count", 0))
    # CDQ 注入：把 lint 合规结果喂给 cdq_score，避免它对 title/bullets 保守假设合规
    # （forge 精度损失点修复：标题违规时 CDQ title 子分此前仍给满分）
    if isinstance(title_r, dict) and "compliant" in title_r:
        data_for_cdq["title_compliant"] = title_r["compliant"]
    if isinstance(bul_r, dict) and "compliant" in bul_r:
        data_for_cdq["bullets_compliant"] = bul_r["compliant"]

    cdq_r = _safe_run(cdq_score, data_for_cdq)
    idx_r = _safe_run(indexability, data)
    alexa_r = _safe_run(alexa_check, data)
    kw_r = _safe_run(check_keyword_layering, data)
    cosmo_r = _safe_run(cosmo_check, data)
    triage_r = _safe_run(title_triage, data)

    template = _load_template()

    # ---- 元信息（透传 listing 头部字段）----
    meta = {
        "market": data.get("market", ""),
        "language": data.get("language", ""),
        "mode": data.get("mode", ""),
        "category": data.get("category", ""),
        "brand": data.get("brand", ""),
        "is_parent": data.get("is_parent", False),
        "is_variation": data.get("is_variation", False),
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    # ---- 合规段：优先脚本结果，否则模板空值 ----
    title_out = title_r if isinstance(title_r, dict) else template.get("title", {})
    hl_out = hl_r if isinstance(hl_r, dict) else template.get("highlights", {})
    bul_out = bul_r if isinstance(bul_r, dict) else template.get("bullets", {})
    bak_out = bak_r if isinstance(bak_r, dict) else template.get("backend", {})

    # ---- 属性完整度（从 listing 原始数据推导）----
    attrs_filled = list(data.get("attributes_filled", []) or [])
    attrs_expected = list(data.get("attributes_top10_expected", []) or [])
    band_a = list(data.get("band_a_critical_6", []) or [])
    filled_ratio = (len(attrs_filled) / len(attrs_expected)) if attrs_expected else 0.0
    band_a_filled = [a for a in attrs_filled if a in band_a]
    # band_a 关键 6 项缺漏过半视为严重缺陷；此处 compliant 用 60% 门槛
    attributes_out = {
        "filled": attrs_filled,
        "top10_expected": attrs_expected,
        "filled_ratio": round(filled_ratio, 4),
        "band_a_critical_6": band_a,
        "band_a_filled": band_a_filled,
        "compliant": filled_ratio >= 0.6,
    }

    # ---- 变体结构（透传）----
    variation_base = dict(template.get("variation", {}))
    variation_base.update({
        "is_parent": data.get("is_parent", False),
        "is_variation": data.get("is_variation", False),
    })

    cdq_out = cdq_r if isinstance(cdq_r, dict) else template.get("cdq_score", {})
    idx_out = idx_r if isinstance(idx_r, dict) else template.get("indexability_report", {})
    alexa_out = alexa_r if isinstance(alexa_r, dict) else template.get("alexa_discoverability", {})
    kw_out = kw_r if isinstance(kw_r, dict) else template.get("keyword_coverage", {})
    img_out = img_r if isinstance(img_r, dict) else {}
    cosmo_out = cosmo_r if isinstance(cosmo_r, dict) else {}
    triage_out = triage_r if isinstance(triage_r, dict) else template.get("triage_report", {})

    # ---- description 透传 ----
    desc = data.get("description", "")
    description_out = {
        "value": desc if isinstance(desc, str) else "",
        "char_count": len(desc) if isinstance(desc, str) else 0,
    }

    # ---- compliance_report 汇总段 ----
    lint_sections = [title_out, hl_out, bul_out, bak_out, attributes_out, variation_base]
    # 图片的 compliant 参与总体判定
    if isinstance(img_out, dict) and "compliant" in img_out:
        lint_sections.append(img_out)
    passed, failed, warnings = _count_checks(lint_sections)
    # 图片无 checks dict，但其 compliant=False 也要计入 failed
    if isinstance(img_out, dict) and img_out.get("compliant") is False:
        failed += 1
    overall = _overall_compliant(lint_sections)
    critical = _collect_critical(lint_sections)
    actions = _collect_action_items(
        title_out, hl_out, bul_out, bak_out, cdq_out, idx_out, alexa_out, kw_out
    )
    # 图片的行动项
    if isinstance(img_out, dict):
        for s in img_out.get("fix_suggestions", []) or []:
            actions.append({"source": "image", "action": str(s)})
    # COSMO 意图覆盖建议
    if isinstance(cosmo_out, dict):
        for s in cosmo_out.get("suggestions", []) or []:
            actions.append({"source": "cosmo", "action": str(s)})
    # 标题词组分诊汇总（指向 triage_report 的去向建议）
    if isinstance(triage_out, dict) and triage_out.get("summary"):
        s = triage_out["summary"]
        parts = []
        if s.get("demote_highlights"):
            parts.append(f"{s['demote_highlights']} 个词组建议下移亮点")
        if s.get("demote_bullets"):
            parts.append(f"{s['demote_bullets']} 个词组建议下移五点")
        if s.get("remove"):
            parts.append(f"{s['remove']} 个词组建议删除（违规）")
        if s.get("prefer_title"):
            parts.append(f"{s['prefer_title']} 个词组倾向保留标题")
        if parts:
            actions.append({"source": "triage", "action": "标题词组分诊：" + "，".join(parts) + "（详见 triage_report）"})

    total_score = 0
    if isinstance(cdq_out, dict):
        total_score = cdq_out.get("total", 0)

    grade = ""
    if isinstance(cdq_out, dict):
        grade = cdq_out.get("grade", "")

    overall_status = "COMPLIANT" if overall else "NON-COMPLIANT"
    summary = (
        f"Overall {overall_status}; "
        f"{passed} passed, {failed} failed, {warnings} warn; "
        f"CDQ {total_score}/100 ({grade})".rstrip(" ()")
    )

    report_out = {
        "overall_compliant": overall,
        "total_score": total_score,
        "summary": summary,
        "passed_checks": passed,
        "failed_checks": failed,
        "warnings": warnings,
        "critical_issues": critical,
        "action_items": actions,
    }

    return {
        "meta": meta,
        "title": title_out,
        "highlights": hl_out,
        "bullets": bul_out,
        "description": description_out,
        "backend": bak_out,
        "attributes": attributes_out,
        "variation": variation_base,
        "cdq_score": cdq_out,
        "indexability_report": idx_out,
        "alexa_discoverability": alexa_out,
        "keyword_coverage": kw_out,
        "image_report": img_out,
        "cosmo_report": cosmo_out,
        "triage_report": triage_out,
        "compliance_report": report_out,
    }


def load_input():
    """统一 CLI：stdin JSON 优先 / --data '<json>' / --file <path>。"""
    parser = argparse.ArgumentParser(description="汇总所有检查脚本，输出最终体检报告")
    parser.add_argument("--data", help="inline JSON")
    parser.add_argument("--file", help="path to JSON file")
    a = parser.parse_args()
    if a.data:
        return json.loads(a.data)
    if a.file:
        return json.loads(Path(a.file).read_text(encoding="utf-8"))
    # 注：原模板写作 is_tty()，但 Python 标准库实际方法为 isatty()；
    # is_tty() 不存在会导致脚本无法运行，此处修正。
    if not sys.stdin.isatty():
        return json.loads(sys.stdin.read())
    return {}


def main():
    data = load_input()
    result = run(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    overall = result.get("compliance_report", {}).get("overall_compliant", True)
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
