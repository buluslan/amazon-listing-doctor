<div align="center">

<!-- Banner: 把一张 banner 图放进 assets/banner.png 后,去掉下一行的注释即可显示 -->
<!-- <img src="assets/banner.png" alt="Amazon Listing Doctor" width="100%"> -->

# 🩺 Amazon Listing Doctor

**基于 CDQ / A9 / COSMO / Alexa 四大底座的亚马逊 Listing 全身体检 + 打分 Skill**

**想了解更多最新AI行业动态,AI+电商/广告的行业实践方法,人与AI如何协作共生的思考,请关注公众号:【新西楼】**

![qrcode_for_gh_e3b954bd3859_258](https://github.com/user-attachments/assets/d8f068d9-c4f8-46c7-914c-fbcab5d52f2a)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-0.1.0-black.svg)]()

**CDQ 质量分 · A9 收录 · COSMO 意图覆盖 · Alexa 可发现性 · 合规体检 · 标题词组分诊**

**Created By Buluu@新西楼**

</div>

---

## 项目简介

Amazon Listing Doctor 是一款 **Agent 原生** 的亚马逊 Listing 质检 Skill,适配 Claude Code、OpenCode 等主流 AI Coding Agent。基于四大知识底座(CDQ / A9 / COSMO / Alexa for Shopping)对任意 Listing 做全身体检 + 打分,输出多维度健康报告。**零依赖、零 API Key**,纯标准库 Python,clone 下来就能跑。

**只诊断不改写** —— 告诉你"哪里有问题、该改什么",改写由你自己决定。

**兼容性**:基于命令行调用,任何能执行 shell 的 Agent 都能用 —— Claude Code(作为 Skill 加载)/ OpenCode / Cursor / Windsurf / 直接终端。

---

## ✨ 它做什么

一条命令,给你的 Listing 出一份多维度体检报告:

| 维度 | 底座 | 回答的问题 |
|---|---|---|
| **CDQ 质量分**(主总分) | 亚马逊内部 6 维 ASIN 质量评分 | 我的内容质量能打几分? |
| **A9 收录健康度** | A9 搜索收录逻辑 | 我的 Listing 能不能被搜到? |
| **COSMO 意图覆盖度** | 亚马逊常识知识图谱(WWW 2024) | 我的 Listing 对不对得上用户意图? |
| **Alexa 可发现性** | Alexa for Shopping（AI 购物助手） | AI 购物助手能理解并推荐我吗? |
| **合规体检** | 2026-07-27 新规 | 我有没有违规? |
| **标题词组分诊** | 词性 + 合规信号 | 标题里每个词该留 / 该挪 / 该删? |

## 🚫 它不做什么

- **不改写文案** —— 只给"该改什么"的改进建议清单,改写交给你自己
- **不内置浏览器抓取** —— 零依赖,数据靠你粘贴(推荐用 sorftime / 卖家精灵等专业工具取数)
- **不冒充官方 COSMO 分** —— COSMO 无公开权重,本 skill 的 COSMO 维度是基于公开论文精神的社区诊断,如实标注

## 🚀 快速开始

```bash
# 1. 把你的 listing 归一化成 JSON(见下方 schema),存为 listing.json
# 2. 跑全量体检
python scripts/compliance_report.py --file listing.json > report.json

# 3.(或单独跑某一维)
python scripts/cdq_score.py --file listing.json        # CDQ 质量分
python scripts/cosmo_check.py --file listing.json      # COSMO 意图覆盖
python scripts/indexability.py --file listing.json     # A9 收录
python scripts/title_triage.py --file listing.json     # 标题词组分诊
```

输出是结构化 JSON;按 `assets/report-template.md` 渲染成人类可读报告。

### listing JSON 最小结构

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

字段不全也没关系——缺的字段对应检查自动跳过,不会报错。详见 `SKILL.md`。

## 🧠 四大底座怎么落地

- **CDQ**:6 维加权(属性 30% / 标题 25% / 变体 20% / 图片 15% / 五点 5% / A+ 5%)→ 0-100 分 + 档位
- **A9**:核心词前置位置 + backend 卫生度 + 属性完整度 + 有效索引词
- **COSMO**:扫全文匹配 `references/cosmo_ontology.json` 的常识概念,四维覆盖(use_case / audience / goal / constraint)+ 缺失清单
- **Alexa**:场景 / 人群 / 限制词覆盖(10 类目分词库 + 通用词库,按 category 自动取)
- **标题词组分诊**:把标题拆成语义词组,按词性 + 合规信号给去向建议(标题必留 / 下移亮点 / 下移五点 / 删除违规),告诉你每个词该去哪——诊断不是改写

## 📁 结构

```
amazon-listing-doctor/
├── SKILL.md                  # 质检路由(工作流 + 原则)
├── scripts/                  # 12 个纯标准库 Python 脚本
│   ├── compliance_report.py  # 汇总器(核心入口)
│   ├── cdq_score.py          # CDQ 6 维评分
│   ├── cosmo_check.py        # COSMO 意图覆盖(本项目独占)
│   ├── title_triage.py       # 标题词组分诊(去向建议)
│   ├── indexability.py       # A9 收录
│   ├── alexa_check.py        # Alexa 可发现性
│   ├── image_check.py        # 图片缺陷
│   ├── lint_title/highlights/bullets/backend.py  # 合规校验
│   └── check_keyword_layering.py
├── references/               # 规则与词库(公开版)
│   ├── cosmo_ontology.json   # COSMO 概念本体(4 维)
│   ├── cdq_weights.json      # CDQ 权重
│   ├── rules.json            # 合规硬规则
│   └── ...
└── assets/                   # 输出模板
    ├── output-template.json
    └── report-template.md
```

## 📜 License

MIT — 随便用,欢迎 PR 扩展词库/类目。

---

<div align="center">

**如果这个工具帮到了你,欢迎 ⭐ Star 支持。更多 AI × 跨境电商实操内容,关注公众号「新西楼」。**

</div>
