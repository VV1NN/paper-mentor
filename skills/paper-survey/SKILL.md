---
name: paper-survey
description: |
  AI 驅動的學術論文調研 — 輸入研究主題，自動從 Semantic Scholar + DBLP + arXiv 搜尋高品質論文
  （只保留頂會 CCS/S&P/NeurIPS/CVPR... 和 Q1 期刊 TPAMI/TRO/JMLR...），
  逐篇產出 sectools.tw 風格的深度分析筆記，存進 Obsidian。

  觸發詞: "論文調研"、"paper survey"、"幫我調研一下"、"survey this topic"、
  "文獻調研"、"research survey"、"調研一下 XXX 方向"、"survey XXX"
context: fork
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, WebFetch, WebSearch
---

# PaperMentor — 高品質論文調研

輸入研究主題 → 搜尋頂會/Q1 論文 → 產出 sectools.tw 風格分析 → 存進 Obsidian。

## Step 0: 讀取配置

讀取 `./pm-config.json`（+ 可選 `./pm-config.local.json` 覆寫）。
重要變數：
- `VAULT_PATH = paths.obsidian_vault`
- `SURVEY_DIR = VAULT_PATH / paths.survey_folder`
- `LANGUAGE = survey.language`（`zh-TW` / `zh-CN` / `en`）
- `MAX_PAPERS = survey.max_papers_final`
- `GIT_COMMIT_ENABLED = automation.git_commit`

## Step 1: 解析用戶需求

從用戶輸入提取：
- **研究主題**（required）：可以是中英文，但傳給 API 時**用英文**（API 對英文查詢效果最好）
- **年份範圍**（optional）：如「最近 3 年」→ `--years 3`，預設讀 config
- **領域提示**（optional）：如「安全領域」、「CV 方向」（用來確認 venue 篩選合理）
- **論文數量**（optional）：如「給我 10 篇就好」→ `--top 10`

如果主題不清楚，問用戶確認（例如「是要廣義的 prompt injection，還是特指 indirect prompt injection in agents？」）。

## Step 2: 執行搜尋

```bash
cd {skill_dir}
python3 search_papers.py --topic "{english_topic}" --years {years} --top {max_papers}
```

（如果用戶說要包含預印本，加 `--include-preprints`）

輸出：`/tmp/pm_survey_candidates.json`（已品質篩選 + 引用排序）

## Step 3: 呈現候選論文，等用戶確認

**不要直接開始分析** — 讀 `/tmp/pm_survey_candidates.json`，用表格呈現：

```markdown
## 調研候選論文（N 篇）

| # | 標題（前 60 字） | Venue | 年 | 引用數 | Tier |
|---|-----------------|-------|----|--------|------|
| 1 | ... | NeurIPS | 2024 | 107 | tier1 |
| 2 | ... | CCS | 2023 | 1072 | tier1 |
| ... |
```

然後問用戶：
- 這些論文看起來對嗎？要增減哪幾篇？
- 要不要調整年份範圍或加入預印本？
- 確認後我開始逐篇分析並存進 Obsidian

**關鍵**：調研很花 token，讓用戶先確認論文清單再分析。

## Step 4: 逐篇深度分析

對每篇確認的論文：

### 4.1 取得完整內容

優先順序：
1. **arXiv HTML**（最好）：`WebFetch https://arxiv.org/html/{arxiv_id}` — 結構化、可完整解析
2. **arXiv Abstract 頁**：`WebFetch https://arxiv.org/abs/{arxiv_id}` — HTML 版不存在時
3. **DOI 解析**：如果沒 arXiv ID 但有 DOI，嘗試 `WebFetch https://doi.org/{doi}`

WebFetch prompt：「完整提取論文的 Abstract、Introduction、Method、Experiments、Limitations、Conclusion 各章節內容，保留所有重要數據、對比方法、技術術語」

### 4.2 按模板產出分析

**嚴格遵循** `./assets/survey-note-template.md` 骨架，但**章節標題和數量依論文內容調整**。

#### 寫作風格規則（最重要 — 這是 sectools.tw 風格的靈魂）

**語氣**
- 像在跟一個聰明的同事解釋這篇論文為什麼值得看
- 不用學術論文的被動語態（禁止「本文提出了...」、「本工作實現了...」）
- 主動、直接、有立場、有判斷
- 用「我」表達觀點（「我怎麼看」「我認為」）

**結構**
- 必須有**敘事弧度**：問題 → 為什麼難 → 他們怎麼想 → 做了什麼 → 結果如何 → 對領域意味什麼
- 不是照搬論文 section 順序，而是重新組織成有邏輯的故事
- 開頭就要讓讀者知道「為什麼我該繼續讀這篇」

**核心技巧**
- **引號洞察**（風格靈魂）：每個章節至少一個 `> 「精煉觀察」`
- **粗體標記關鍵詞**：列表項的標題、重要名詞用 `**粗體**`
- **問題驅動章節**：章節標題盡量是問題或觀點（「為什麼 X 視角很重要？」），不是描述性標題（「方法介紹」）
- **對比定位**：說清楚這篇跟同期 / 同領域其他工作的關係
- **限制要具體**：不寫「需要更多實驗」這種廢話，要寫「驗證只限於 X 場景，因為 Y 原因」

**禁止**
- 禁止照抄 Abstract
- 禁止只列點不分析
- 禁止用「本文提出了」開頭
- 禁止所有觀點都正面（要有保留和批判）
- 禁止使用 emoji
- 禁止寫成教科書式的知識整理
- 禁止學術八股

#### 各章節具體指引

| 章節 | 內容要求 |
|------|---------|
| **標題** | `{短論文名} 論文閱讀分析：{1 句話 hook, <40 字}` — hook 要點出反直覺或最核心的洞察 |
| **核心論述** | 2-3 段, <300 字。第一段就點明為什麼這篇特別。結尾用引號帶出核心問題 |
| **這篇論文想解決什麼問題？** | 3-5 個具體瓶頸，每個說清楚為什麼是瓶頸，不只是「不夠好」 |
| **方法相關章節（1-3 個）** | 依論文內容調整，重點是「為什麼這樣設計」而非 step-by-step |
| **論文最值得注意的主張** | 3-5 個 claim，每個附評估（強 / 中 / 保留），區分有實驗支撐 vs 僅聲稱 |
| **這篇真正提供的啟發** | 拉高一層跟領域趨勢連結，提煉可帶走的框架 |
| **限制與保留** | 4-6 個具體限制 |
| **我怎麼看這篇論文？** | 明確定位和評價，點出最深的洞察 |
| **一句話總結** | <100 字, 要是看完能記住的話 |

### 4.3 存進 Obsidian

**檔名規則**：
- 優先用**方法名 / 模型名**（標題冒號前的部分通常就是）
- 例：`TaskShield_論文閱讀分析.md`、`AgentDojo_論文閱讀分析.md`
- 如果沒有明顯方法名，用短標題：`{ShortTitle}_論文閱讀分析.md`

**存放路徑**：
```
{SURVEY_DIR}/{sanitized_topic}/{MethodName}_論文閱讀分析.md
```

`sanitized_topic` = 把用戶的研究主題轉成可當資料夾名（去除特殊字元、空格變底線，保留中英文）。

如果資料夾不存在，建立它（`mkdir -p`）。

## Step 5: 補交叉連結

所有分析都完成後，**每篇筆記的「本次調研的相關論文」區塊**填入：
- 同批調研的其他論文 wikilink
- 每個加一句話說明關係（對比、延伸、反駁、互補等）

讀每篇筆記 → 用 Edit 工具在 `## 本次調研的相關論文` 區塊填入實際連結。

## Step 6: 產生調研總覽

在 `{SURVEY_DIR}/{sanitized_topic}/_調研總覽.md` 產出整合性文章：

```markdown
---
title: "{topic} 論文調研總覽"
topic: "{topic}"
paper_count: {N}
date_range: "{min_year}-{max_year}"
tags: [survey-overview, {topic_tags}]
type: survey-overview
created: {date}
---

# {topic} 論文調研總覽

## 研究背景與動機
{為什麼這個主題重要}

## 研究脈絡（時間線）
{按年份展開，說明研究如何演進}

- **{year}**: [[{Paper}]] — {一句話貢獻}
- **{year}**: [[{Paper}]] — {一句話貢獻}

## 方法分類
{把論文按 approach 分群，例如：}
### A 類方法: {classification_name}
- [[{Paper1}]]
- [[{Paper2}]]

### B 類方法: {classification_name}
- ...

## 核心發現對比

| 論文 | 核心 idea | 性能 | 限制 |
|------|-----------|------|------|
| [[Paper1]] | ... | ... | ... |

## 跨論文開放問題
{所有論文都沒解決的共同問題}

## 我的整體觀察（sectools.tw 風格）
{用一兩段話給出這個領域的現況判斷}

> 「{整體洞察引言}」
```

## Step 7: 可選自動化

如果 `GIT_COMMIT_ENABLED=true` 且 `{VAULT_PATH}/.git` 存在：
```bash
cd {VAULT_PATH} && git add "{survey_folder}/{sanitized_topic}/" && \
  git commit -m "paper survey: {topic} ({N} papers)"
```

## Step 8: 回報

告訴用戶：
1. 調研資料夾位置：`{SURVEY_DIR}/{sanitized_topic}/`
2. 每篇論文的檔名清單
3. 調研總覽的位置
4. 一句話問：還要針對哪篇深入討論嗎？

---

## 語言處理

- 如果 `LANGUAGE=zh-TW`（預設）：所有章節標題、正文用繁體中文，技術術語保留英文
- 如果 `LANGUAGE=zh-CN`：簡體中文
- 如果 `LANGUAGE=en`：全部英文，包含標題 hook 和引號洞察

API 查詢（給 Semantic Scholar / DBLP / arXiv 的 `--topic`）**永遠用英文**，不論輸出語言。

## 錯誤處理

- Semantic Scholar 429 rate limit → 等 5 秒重試一次；若還失敗，繼續用 DBLP + arXiv 結果
- arXiv HTML 404 → fallback 到 abstract 頁 + abstract 內文分析（品質會下降，提醒用戶）
- 用戶的主題太抽象（「AI 安全」）→ 問更具體：「是想看 prompt injection？jailbreak？還是 model theft？」

## 參考檔案

- `search_papers.py` — 搜尋引擎（Semantic Scholar + DBLP + arXiv + 品質篩選 + 引用排序）
- `venue_db.json` — 頂會和 Q1 期刊品質資料庫（可用 `pm-config.local.json` 的 `venue_overrides` 擴充）
- `assets/survey-note-template.md` — 分析筆記模板
- `pm_config.py` — 配置 loader
- `pm-config.json` — 預設配置
