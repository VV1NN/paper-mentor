# PaperMentor

AI 驅動的學術論文調研 — 輸入研究主題，自動搜尋頂會 / Q1 期刊論文，產出有觀點、有態度的深度分析筆記，直接存進 Obsidian。

一個 [Claude Code](https://docs.anthropic.com/claude-code) skill pack。

## 這是什麼

給一個研究主題（例如「indirect prompt injection in LLM agents」），PaperMentor 會：

1. **搜尋**：從 Semantic Scholar、DBLP、arXiv 三個來源並行查詢
2. **品質篩選**：只保留頂會（NeurIPS、CVPR、CCS、S&P、ICRA、CoRL...）和 Q1 期刊（TPAMI、TRO、JMLR、Nature MI...）論文
3. **排序**：依 venue 層級 + 引用數 + 時效性排序
4. **用戶確認**：呈現候選清單，讓你決定要分析哪幾篇
5. **深度分析**：對每篇產出 [sectools.tw](https://sectools.tw/archives/798) 風格的分析文章 — 不是學術摘要，是有觀點有態度的評析
6. **存進 Obsidian**：以 `.md` + wikilink 格式，完美融入你的知識庫
7. **調研總覽**：最後產出一篇整合文章，梳理研究脈絡、方法分類、開放問題

## 風格範例

輸出不是這種乾巴巴的學術筆記：

> 本文提出了一種基於多 agent 的 SAST 檢測方法，在 benchmark 上取得 SOTA，證明了多 agent 協作的有效性。

而是像這樣有觀點的分析：

> Argus 這篇的切入點很不一樣：它不是在問「agent 會不會被打穿」，而是在問另一個更工程、也更現實的問題——當 LLM 真正被放進靜態弱點分析流程裡，為什麼常常不是不夠聰明，而是整條工作流根本排錯位置？
>
> 「從 tool-centered、LLM-assisted，改成 LLM-centered、tools-and-context-assisted」

風格參考：[sectools.tw 論文閱讀分析系列](https://sectools.tw/archives/799)

## 安裝

### 前置需求

- [Claude Code](https://docs.anthropic.com/claude-code) 已安裝並登入
- Python 3.9+（macOS / Linux 通常內建）
- 一個 Obsidian vault（或任何你想存 `.md` 筆記的目錄）

### 一鍵安裝

```bash
git clone https://github.com/YOUR_USERNAME/paper-mentor.git
cd paper-mentor
./install.sh
```

安裝腳本會把 `skills/paper-survey/` symlink 到 `~/.claude/skills/paper-survey/`，之後 `git pull` 會自動更新，不用重跑 installer。

### 設定 Obsidian vault 路徑

複製範例設定：

```bash
cp skills/paper-survey/pm-config.local.json.example \
   skills/paper-survey/pm-config.local.json
```

編輯 `pm-config.local.json`，把 `obsidian_vault` 改成你的實際路徑：

```json
{
  "paths": {
    "obsidian_vault": "~/Documents/MyVault",
    "survey_folder": "Papers/Surveys"
  }
}
```

## 使用

在 Claude Code 裡直接說：

```
論文調研 indirect prompt injection in LLM agents
```

或英文：

```
survey multi-agent reinforcement learning for robotic manipulation
```

PaperMentor 會：
1. 跑搜尋 + 品質篩選（約 10-30 秒）
2. 給你一張候選論文表格，等你確認
3. 逐篇 WebFetch + 分析（每篇約 1-3 分鐘）
4. 全部存進 `{vault}/{survey_folder}/{topic}/`
5. 最後產出 `_調研總覽.md`

## 設定檔說明

`pm-config.json` 預設值（可用 `pm-config.local.json` 覆寫）：

| 欄位 | 預設 | 說明 |
|------|------|------|
| `paths.obsidian_vault` | `~/ObsidianVault` | Obsidian vault 根目錄 |
| `paths.survey_folder` | `论文調研` | 調研筆記存放的子目錄 |
| `survey.max_papers_final` | `15` | 每次調研最多保留幾篇 |
| `survey.min_citation_count` | `5` | 預印本最低引用門檻 |
| `survey.year_range_default` | `5` | 預設搜尋最近幾年 |
| `survey.include_preprints` | `false` | 是否允許高引用的 arXiv 預印本通過篩選 |
| `survey.language` | `zh-TW` | 輸出語言：`zh-TW` / `zh-CN` / `en` |
| `survey.semantic_scholar_api_key` | `""` | （選配）Semantic Scholar API key，拿了有更高的 rate limit |
| `automation.git_commit` | `false` | 是否自動 git commit 到 vault（需 vault 是 git repo） |

## 擴充 venue 資料庫

`skills/paper-survey/venue_db.json` 內建了約 60+ 頂會 + 40+ Q1 期刊。如果你的領域有沒收錄的頂會，在 `pm-config.local.json` 加 `venue_overrides`：

```json
{
  "venue_overrides": {
    "conferences": {
      "tier1": {
        "your_field": ["YourTopConf"]
      }
    },
    "journals": {
      "q1": ["Your Top Journal"]
    },
    "venue_aliases": {
      "YourTopConf": ["Full Conference Name", "YourTopConf", "Proc. YTC"]
    }
  }
}
```

## 架構

```
paper-mentor/
├── install.sh                              # 一鍵安裝（symlink 到 ~/.claude/skills/）
├── README.md
├── LICENSE                                 # MIT
└── skills/
    └── paper-survey/
        ├── SKILL.md                        # Claude Code skill 主入口
        ├── search_papers.py                # 搜尋 + 品質篩選 + 排序
        ├── venue_db.json                   # 頂會 / Q1 期刊資料庫
        ├── pm_config.py                    # 配置 loader
        ├── pm-config.json                  # 預設配置
        ├── pm-config.local.json.example    # 個人覆寫範例
        └── assets/
            └── survey-note-template.md     # 分析筆記模板
```

## 工作流詳解

```
用戶: "論文調研 XXX"
    ↓
Claude Code 觸發 paper-survey skill
    ↓
Step 1: 解析主題、年份、數量
    ↓
Step 2: python3 search_papers.py
        ├── Semantic Scholar API（主要：引用數 + venue）
        ├── DBLP API（頂會名稱權威來源）
        └── arXiv API（最新預印本）
        ↓ 去重 + venue_db 品質篩選 + 排序
    ↓ /tmp/pm_survey_candidates.json
Step 3: 呈現候選論文清單，等用戶確認
    ↓
Step 4: 逐篇 WebFetch arXiv HTML → 按 template 產出分析
    ↓
Step 5: 補交叉連結（「本次調研的相關論文」）
    ↓
Step 6: 產生 _調研總覽.md（研究脈絡 + 方法分類 + 對比表）
    ↓
Step 7: 存進 Obsidian
```

## 常見問題

**Q: 為什麼只搜尋頂會？**

A: 因為學術界水論文非常多，預設嚴格篩選保證你看到的都是同行認可的高品質工作。如果想放寬，在 `pm-config.local.json` 開 `"include_preprints": true` 允許高引用的 arXiv 預印本。

**Q: 中國的 CCF 分級適用嗎？**

A: `venue_db.json` 的 tier1 大致對應 CCF-A / CORE A*，tier2 對應 CCF-B / CORE A。如果你需要 CCF-C 級別的會議，自己加到 `venue_overrides`。

**Q: Semantic Scholar 要申請 API key 嗎？**

A: 不用（免費 API 每 5 分鐘 100 次請求，足夠用）。但如果想跑更多論文，[申請一個](https://www.semanticscholar.org/product/api) 放進 config 會更穩。

**Q: 可以不用 Obsidian 嗎？**

A: 可以。`paths.obsidian_vault` 可以指到任何目錄，產出的就是純 `.md` 檔，用 VS Code / Typora / 任何編輯器都能看。wikilink（`[[...]]`）在 Obsidian 外不會自動連結，但可讀性不受影響。

## 授權

MIT License — 見 [LICENSE](./LICENSE)

## 致謝

風格參考：[sectools.tw](https://sectools.tw) 的論文閱讀分析系列
