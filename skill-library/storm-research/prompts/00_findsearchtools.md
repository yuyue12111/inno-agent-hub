# Step 0 — 检索能力探测 (Find Search Tools)

> 作用：研究开始前一次性盘点环境里**所有**能取回外部公开信息的检索通道，避免后续视角空有立场却无处取证。这是接地研究的地基。

## 内核

正式研究前先做一次性的环境探测，**发现并列出当前可用的所有检索能力**。这是全局、与主题无关的准备，整个研究过程只做一次（不要每轮检索都重做）。

> ⚠️ **核心纪律：靠回忆必然遗漏。必须实际遍历当前环境的真实工具/skill/agent 清单，逐项过筛——不是凭印象按类联想。**

## 第一步：拉出真实全集（遍历，不是回忆）

目标是发现**三类检索资产**，且因为 storm 本质是 research，发现优先级是 **搜索 ＞ 调研**（搜索类是核心，调研类是辅助；调研类内部再优先带联网搜索能力的）：

1. **搜索/检索工具**（最高优先）——当前 agent 直接挂载的网络搜索、网页抓取、AI 搜索、领域检索工具
2. **搜索/调研类 skill**——承担「搜索 / 联网研究 / 网页抓取 / 调研」职责的 skill
3. **搜索/调研类子 agent**——可派发的、带联网搜索能力或职责为调研的 agent

> 🌐 **跨平台**：storm 要能在主流 agent 平台上工作。各平台把 skill/agent 放在不同位置，**方法不变（读 name+description / tools，只在描述字段里筛搜索/调研关键词），只把目录换成当前平台的**。常见布局（存在才用，按当前 runtime 实际为准）：
>
> | 平台 | skills | agents |
> |---|---|---|
> | Claude Code | `~/.claude/skills/` `~/.claude/plugins/**/skills/` 项目 `.claude/skills/` | `~/.claude/agents/` `~/.claude/plugins/**/agents/` 项目 `.claude/agents/` |
> | Codex | `~/.codex/skills/` `~/.codex/vendor_imports/skills/` | `~/.codex/skills/*/agents/` |
> | OpenClaw | `~/.openclaw/skills/` `~/.openclaw/workspace*/skills/` | `~/.openclaw/agents/` |
> | Hermes | `~/.hermes/skills/` | （同平台 agents 目录） |
> | Cursor | `~/.cursor/skills/` `~/.cursor/plugins/` | `~/.cursor/agents/`（如有） |
> | Cline | `~/.cline/skills/` | — |
> | Gemini | `~/.gemini/skills/` `~/.gemini/antigravity/skills/` | — |
> | OpenCode / WorkBuddy / 其他 | `~/.opencode/...`、`~/.config/<platform>/skills/`、`~/.agents/skills/` 等（如有） | 对应 `agents/` |
>
> 不确定当前平台路径时，先发现候选目录：`find ~ -maxdepth 4 -type d \( -name skills -o -name agents \) 2>/dev/null`。一台机器常混有多平台目录——**只纳入当前 runtime 确实能调用的**，其余标"他平台、当前不可用"，别假装能跨平台调用。

**发现方法（核心：看描述，不是看目录名）**

- **工具**：直接列出当前会话挂载的全部工具名，逐个看哪些是搜索/抓取/检索类（平台无关，这步最直接）。
- **skill**：**别只列目录名**（目录名不告诉你能不能检索）。要读出每个 skill 的 `name`+`description`，**只在 description 字段里筛**搜索/调研关键词——全文 grep 会把正文随口提到 "web/research" 的无关 skill 全捞进来，噪声爆炸。参考做法（按平台换目录）：
  ```bash
  for f in ~/.claude/skills/*/SKILL.md; do
    n=$(grep -m1 '^name:' "$f" | sed 's/name: *//')
    d=$(grep -m1 '^description:' "$f" | sed 's/description: *//')
    printf '%-26s %s\n' "$n" "$d"
  done | grep -iE '搜索|检索|抓取|爬|联网|网页|调研|search|scrape|crawl|fetch|retriev|browse|research|url'
  ```
  机器粗筛后**逐个用描述精判**。实测能精准捞出 `mywebsearch`、`perplexity-search`、`scrape`、`url-reader`/`baoyu-url-to-markdown`、`browse`、`youtube-transcript`、`paper-reader` 等。
- **子 agent**：同理**读 `description` 和 `tools` 字段**，不是只列文件名。判定标准（平台无关）：**`tools` 含网络搜索/抓取（WebSearch/WebFetch 或等价物），或 `description` 提"调研/research/搜索"** → 纳入（实测 `content-researcher`、`research-analyst`、`trend-analyst` 都带 WebSearch+WebFetch）。内置工具撞墙时，派发这类 agent 往往是最强、最现成的检索路径。

**收口**
- 三类（工具 + skill + 子 agent）都遍历过才算完。某一类无法枚举，**如实标注"该类未完整遍历"**，不许假装查全；子 agent 实在枚举不到时，默认通用 agent（general-purpose / 等价物）可承担检索兜底。
- 可选：用 `Bash` 探一下命令行间接通道（`which curl`、`gh --version`）。平台无 shell 时跳过。

## 第二步：逐项过筛（宽口径，别只认通用网页搜索）

对清单里**每一个**工具/skill/命令/子 agent，逐个问："它能不能用来搜索网络、抓取网页、或检索某个领域的**外部公开**语料？"能就入库。检索能力的口径要宽，至少覆盖：

- **通用网页搜索**：网络搜索、AI 搜索类工具
- **网页抓取**：抓 URL、读网页、转 markdown 类工具
- **领域专用检索**：法律判例/法条、学术论文、库/框架文档、专利、代码等**特定领域的检索工具**——对口主题时往往比通用搜索更强，最容易被漏掉，重点查
- **调研类 / 带搜索的 skill 与子 agent**：第一步遍历到的、承担「搜索 / 联网研究 / 抓取 / 调研」的 skill，以及可派发的检索子 agent（researcher / content-research / deep-research / general-purpose 等）。当前 agent 自己没搜索工具、**或内置工具撞墙（搜索不返回结果、抓取频繁 404/403/429）时**，这往往是最强、最现成的路径，别撞墙就停
- **命令行/间接通道**：`curl`、`gh api`、wget、各类 CLI——能抓网络内容的间接路径，不是"检索工具"但算检索通道
- **浏览器自动化**：能驱动浏览器打开网页、搜索、抓取的工具或 skill
- **需认证才能启用的工具**：存在但要 OAuth/登录的（如某些法律/数据 MCP）——**也要列出**，标注"需用户授权后可用"，别当成不存在

> **排除项（不算接地能力）**：只检索**本地/私域**内容的工具（本地记忆库、本地代码索引、私人网盘/聊天记录等）不能用来满足接地红线——接地研究要的是"能取回**外部公开来源**"的能力。这类本地/私域检索可忽略，不入接地清单。

## 第三步：分类登记成清单

把入库的能力按"通用搜索 / 领域检索 / 抓取 / 调研类 skill / 检索子 agent / 间接通道 / 需授权"分类列出，整个研究过程复用。**本地/私域检索不入此清单。** 清单随环境而变（Claude Code、Codex、其他 agent 各不相同），以**当下实际遍历到的**为准。

## 第四步：按主题排优先级

研究主题对口某个领域检索工具时（如法律主题→判例/法条检索，技术主题→文档检索），**优先用它**，通用网页搜索退为补充。

## 早失败

若遍历后确认环境里没有任何联网/检索/抓取通道，立刻据实告知用户"无法做接地研究"，不要先跑完视角和提问再到检索阶段才暴露。

## 为什么这样设计

接地研究的命根子是检索，而检索的前提是"知道自己手里有哪些检索通道"。这一步最大的失败模式是**凭记忆列举**——会系统性漏掉领域检索工具、调研类 skill、带搜索的子 agent（实测中 `perplexity-search`、`content-researcher` 都因此被漏）。所以纪律是"实际遍历 + 给每类配具体枚举动作"，而非"按类联想"。把它独立成 Step 0，是因为它与主题无关、全程只做一次，且一旦发现无检索能力应当立刻早失败，不浪费后续步骤。
