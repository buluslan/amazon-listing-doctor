<div align="center">

<!-- Banner: drop a banner image at assets/banner.png and uncomment the next line -->
<!-- <img src="assets/banner.png" alt="Amazon Listing Doctor" width="100%"> -->

# 🩺 Amazon Listing Doctor

**An open-source Amazon Listing health-check & scoring Skill built on four engines: CDQ, A9, COSMO, and Alexa**

**For the latest AI industry trends, AI × e-commerce/advertising practices, and thoughts on human-AI collaboration, follow the WeChat Official Account: 【新西楼】(Xinxi Lou AI)**

![qrcode_for_gh_e3b954bd3859_258](https://github.com/user-attachments/assets/d8f068d9-c4f8-46c7-914c-fbcab5d52f2a)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-0.1.0-black.svg)]()
[![中文](https://img.shields.io/badge/lang-中文-red.svg)](README.md)

**CDQ Quality Score · A9 Indexability · COSMO Intent Coverage · Alexa Discoverability · Compliance · Title Triage**

**Created By Buluu@新西楼**

</div>

---

## Introduction

Amazon Listing Doctor is an **Agent-native** Amazon Listing quality-check Skill for Claude Code, OpenCode, and other AI coding agents. It runs a full health check + scoring on any listing across four knowledge engines (CDQ / A9 / COSMO / Alexa for Shopping) and outputs a multi-dimensional health report. **Zero dependencies, zero API keys** — pure Python standard library, clone and run.

**Diagnosis only, no rewriting** — it tells you *what's wrong and what to fix*; the rewriting is up to you.

**Compatibility**: CLI-based, works in any agent that can run shell commands — Claude Code (loaded as a Skill) / OpenCode / Cursor / Windsurf / plain terminal.

---

## ✨ What it does

One command, one multi-dimensional health report for your listing:

| Dimension | Engine | Question it answers |
|---|---|---|
| **CDQ Quality Score** (main) | Amazon's internal 6-metric ASIN quality score | How good is my content quality? |
| **A9 Indexability** | A9 search indexing logic | Can my listing be found in search? |
| **COSMO Intent Coverage** | Amazon commonsense knowledge graph (WWW 2024) | Does my listing match user intent? |
| **Alexa Discoverability** | Alexa for Shopping (AI shopping assistant) | Can the AI shopping assistant understand and recommend me? |
| **Compliance** | July-2026 new rules | Any violations? |
| **Title Triage** | Part-of-speech + compliance signals | Which title words to keep / move / drop? |

## 🚫 What it doesn't do

- **No copy rewriting** — only a "what to fix" suggestion list; rewriting is up to you
- **No built-in browser scraping** — zero dependencies; paste your data (recommend pro tools like sorftime / 卖家精灵 for data)
- **No fake official COSMO score** — COSMO has no public weight; this skill's COSMO dimension is a community diagnosis based on the public paper, honestly labeled

## 🚀 Quick Start

```bash
# 1. Normalize your listing into JSON (see schema below), save as listing.json
# 2. Run the full health check
python scripts/compliance_report.py --file listing.json > report.json

# 3. (Or run a single dimension)
python scripts/cdq_score.py --file listing.json        # CDQ quality score
python scripts/cosmo_check.py --file listing.json      # COSMO intent coverage
python scripts/indexability.py --file listing.json     # A9 indexability
python scripts/title_triage.py --file listing.json     # title triage
```

Output is structured JSON; render via `assets/report-template.md` into a human-readable report.

### Minimal listing JSON

```json
{
  "market": "US", "language": "en", "mode": "strict_75", "category": "Electronics",
  "brand": "Anker", "is_parent": false, "is_variation": true,
  "title": "...", "item_highlights": "...",
  "bullets": [{"header": "...", "body": "..."}],
  "description": "...", "backend_search_terms": "...",
  "attributes_filled": ["brand", "color"],
  "has_a_plus": true
}
```

Missing fields are fine — corresponding checks auto-skip, no errors. See `SKILL.md`.

## 🧠 How the four engines work

- **CDQ**: 6-dimension weighted (attributes 30% / title 25% / variation 20% / image 15% / bullets 5% / A+ 5%) → 0-100 score + grade
- **A9**: core keyword position + backend hygiene + attribute completeness + effective index terms
- **COSMO**: scans full text against `references/cosmo_ontology.json` commonsense concepts, 4-dimension coverage (use_case / audience / goal / constraint) + missing list
- **Alexa**: scene / audience / limitation word coverage (10 category lexicons + common lexicon, auto-selected by category)
- **Title Triage**: splits the title into semantic phrases, gives placement advice per phrase (keep in title / move to highlights / move to bullets / drop violation) — diagnosis, not rewriting

## 📁 Structure

```
amazon-listing-doctor/
├── SKILL.md                  # Quality-check router (workflow + principles)
├── scripts/                  # 12 pure-stdlib Python scripts
│   ├── compliance_report.py  # Aggregator (main entry)
│   ├── cdq_score.py          # CDQ 6-dimension scoring
│   ├── cosmo_check.py        # COSMO intent coverage (this project)
│   ├── title_triage.py       # Title triage (placement advice)
│   ├── indexability.py       # A9 indexability
│   ├── alexa_check.py        # Alexa discoverability
│   ├── image_check.py        # Image defects
│   ├── lint_title/highlights/bullets/backend.py  # Compliance checks
│   └── check_keyword_layering.py
├── references/               # Rules & lexicons (public)
│   ├── cosmo_ontology.json   # COSMO concept ontology (4 dimensions)
│   ├── cdq_weights.json      # CDQ weights
│   ├── rules.json            # Compliance hard rules
│   └── ...
└── assets/                   # Output templates
    ├── output-template.json
    └── report-template.md
```

## 📜 License

MIT — use freely, PRs welcome to extend lexicons/categories.

---

<div align="center">

**If this tool helped you, please ⭐ Star it. For more AI × cross-border e-commerce practices, follow the WeChat Official Account 「新西楼」.**

</div>
