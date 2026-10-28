# PEBS 完整使用手册

[中文首页](../README.zh-CN.md) · [English](usage.md) · [API 清单](api.md)

## 1. 安装与首次体验

需要 Git、Python 3.11+，建议 Python 3.12。所有命令均在仓库根目录执行。
当前采用源码运行方式，不提供 `pip install pebs` 安装包。

```bash
git clone https://github.com/Beritwu/psychology-education-skills.git
cd psychology-education-skills
python -m venv .venv
```

Windows PowerShell 执行 `.venv\Scripts\Activate.ps1`；macOS/Linux 执行
`source .venv/bin/activate`。若系统限制激活脚本，可直接运行虚拟环境中的 Python，
无需修改整台电脑的安全策略。

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m compileall -q pebs
python -m pebs.cli serve --port 8710
```

访问 **http://127.0.0.1:8710**。工作台主要为中文。四语言首页与示例不等于整个工作台已完成四语言翻译。

只想看效果时，直接用浏览器打开 `examples/classical-conditioning/index.html`，无需安装 Python 或配置密钥。
真实生成课程则需要下一步的模型与研究服务。

## 2. 配置模型与研究服务

编辑 `config/providers.yaml` 后重启服务。配置在进程启动时读取，程序不会自动加载 `.env` 文件。

默认 `llm.kind: codex_exec` 使用本机已安装并登录的 Codex CLI。PEBS 调用 CLI，不读取账号密钥；
每次调用消耗该账号配额。请按 Codex 官方说明完成安装和登录，并确保 `codex` 可在 PATH 中找到。

使用其他兼容服务时，将 `llm` 配置替换为自己的服务信息：

```yaml
llm:
  id: default-llm
  kind: openai_compatible
  enabled: true
  base_url: https://YOUR-PROVIDER.example/v1
  api_key_env: PEBS_LLM_API_KEY
  require_api_key: true
  model: YOUR_MODEL_ID
  timeout_seconds: 180
  temperature: 0.2
```

保留适用的 `send_scope` 声明。将真实密钥放入启动 PEBS 的终端环境变量 `PEBS_LLM_API_KEY`，
不要写入 YAML、文档、公开终端记录或 Git。示例 URL 和模型名必须换成真实服务参数。

研究层支持 Crossref、OpenAlex、Semantic Scholar、PubMed，包含可选的开放全文检索和 Unpaywall 查询。
在研究配置中填写合适的 `contact_email`；可选研究密钥使用 `PEBS_RESEARCH_API_KEY`。
ERIC、PsycINFO 和 CNKI 连接器尚未实现。来源是否可访问、是否足以支持论断需要逐条判断。

```bash
python -m pebs.cli status
```

此命令检查可用性，不保证实际请求成功，也不保证配额足够。本地运行仍可能向配置的外部模型和研究服务发送资料。

## 3. 创建课程和查看变更

```bash
python -m pebs.cli build --project demo --planner dynamic --max-model-calls 20 --max-research 20 --max-seconds 1200 --request "设计一节心理学入门课，包含虚构案例与形成性评价题，不需要PPT，不要动画。"
```

默认规划器为 `static`；`dynamic` 根据技能输入输出契约组织依赖图。
中文的“不需要 PPT”“不要动画”、字数限制等确定性约束优先于模型路由。
约束解析主要面向中文，英文、日文和韩文的所有否定表达不保证都能识别，应查看实际生成的计划。

可添加 `--template path/to/template.docx`；多个参考材料可重复使用 `--material path/to/material.md`。
上传前先移除真实姓名、联系方式和可识别个体的信息。

运行输出包含 `run_id` 与 `changeset_id`。工作台可查看计划、产物、来源、变更差异、质量检查、预览和评价。
候选版本需要检查后接受：

```bash
python -m pebs.cli decide --project demo --changeset cs_实际编号
```

拒绝时加 `--reject`。接受变更只是确定课程版本，不等于正式交付合格。
运行可能因预算、来源或模型失败而 BLOCKED/FAILED；应检查原因，不能用空内容或测试数据冒充完成。
研究核验可能为一条论断预留多次请求，因此预算上限不保证足够完成整节课。

## 4. 局部修改、重跑和续跑

对于确有两节内容的课程，先查看修改计划：

```bash
python -m pebs.cli conversation --project demo --message "第2节案例换成大学宿舍情境，第1节不要动" --plan-only
```

去掉 `--plan-only` 执行。保留部分在修改期间受到锁定保护；下游相关材料可能变为过期，
需要重新检查。完成后审阅并接受新变更集。

```bash
python -m pebs.cli rerun --project demo --step gates
python -m pebs.cli resume --project demo --run run_实际编号 --max-model-calls 40 --max-research-requests 40 --run-seconds 1800
```

重跑的步骤 ID 必须存在于计划中。`resume` 针对预算阻塞，不会修复服务凭据，也不会让缺乏依据的论断自动通过。

## 5. 草稿、正式导出和教师签署

```bash
python -m pebs.cli export --project demo --mode draft
```

草稿标记为“草稿—未通过 QA”，位于 `projects/demo/outputs/draft/`。
正式导出要求适用的 G1–G8 检查通过且对应当前版本，并满足相应的接受与教师复核要求。

真实教师完成复核后才记录签署：

```bash
python -m pebs.cli signoff --project demo --changeset cs_已接受版本 --reviewer "实际复核人" --basis "实际检查过的内容与依据"
python -m pebs.cli export --project demo --mode formal
```

签署不能代替证据。人工确认某条论断为 supported 时，需要保存来源中的可定位原文：

```bash
python -m pebs.cli claim-review --project demo --claim clm_实际编号 --version 1 --decision supported --reviewer "实际复核人" --basis "真实判断依据" --source src_实际编号 --source-version 1 --quote "来源中的准确原文" --quote-location "实际位置"
```

其他决定包括 `qualify`、`unsupported`、`disputed` 和 `human_review`。
不要直接修改检查结果、数据库或产物 JSON 来绕过门禁。

## 6. PPT、图示与动画

PPTX 使用可编辑的原生元素。正式交付需要 LibreOffice Impress 或支持的 PowerPoint 渲染器，
并检查缩略图、证据索引与制作规划。缺少渲染器时应保留草稿状态。

PPT Foundry 交付检查器需独立安装并通过技能生命周期审核、固定版本。
运行名称必须为 `ppt-foundry`，其目录或一级子目录须包含 `scripts/pptx_delivery_check.py`。
本仓库不打包上游程序；仅克隆仓库不代表该检查器已可用。开发环境使用的固定版本见第三方声明。
请依据实际门禁结果判断交付状态。

SVG 需通过安全检查。动画先判断教学必要性，再生成与讲解同步的分镜；生产流程标记
`rendered=false`，不调用视频/TTS/ASR。仓库附带的网页动画属于独立示范实现。

## 7. 安装、管理与迁移技能

22 个内置技能可以直接使用。外部 14 个教学技能需要下载固定上游版本：

```bash
python -c "from pebs.provider_edu import install; install()"
python -c "from pebs.provider_edu import verify; r=verify(); print(r); raise SystemExit(0 if r['ok'] else 1)"
```

安装器采用 provider 清单中记录的审核政策，会修改本地注册表并创建忽略入库的运行资源。
采用前应阅读清单。已有安装需要重装时，先备份本地修改，再使用 `install(force=True)`；
该选项会移除并重建对应的派生技能缓存。

自定义技能按以下生命周期处理：

1. `skills import <可信归档地址> --name <名称> --sha <固定提交>`。
2. `skills review <名称> --decision in_review --reviewer <审核人> --evidence <依据>`。
3. 实际完成审核后，使用 `--decision approve --adoption ADOPT`。
4. `skills publish <名称> --version <版本>`；`skills pin <名称> --version <版本>`。
5. 在 `registry/allowlist.json` 明确允许显式调用，执行 `skills enable <名称>` 与 `skills verify <名称>`。

以上子命令均以 `python -m pebs.cli` 开头。下载来源受 `config/skills_sources.yaml` 限制。
补丁参数见 `python -m pebs.cli skills patch --help`；上游 SHA 不匹配时应停止。
候选脚本必须先通过 `python -m pebs.cli sandbox --probe`，不允许退回宿主机直接运行。

迁移到另一台电脑：克隆仓库 → 安装 Python 依赖 → 配置模型 → 安装可选技能 → 验证 → 配置渲染器。
不要通过 Git 搬运密钥和机器绝对路径。**pi 不是必要依赖**；交叉审计可用其他 CLI/API 或模型界面完成，
审计报告与真人教师评分分开保存。

## 8. 基准测试与真实教师评价

离线查看计划与运行测试：

```bash
python -m pebs.cli benchmark --cases A,B,C --modes builtin,dynamic --plan-only
python -m pytest tests -q -m benchmark_smoke
```

真实模型对比会消耗配额：

```bash
python -m pebs.cli benchmark --cases B --modes direct_codex,builtin,dynamic --max-model-calls 40 --max-research 40 --max-seconds 1800 --strict
python -m pebs.cli benchmark --report
python -m pebs.cli benchmark --gate-audit
python -m pebs.cli benchmark --promotions
```

比较时保持预算、代码、门禁、模型和技能版本可比。`--promotions` 只输出观察结果，不自动改路由。
对抗与媒体场景各有目标，不能把所有 case 当成同一种课程构建。

```bash
python -m pebs.cli benchmark --export-eval-kit
python -m pebs.cli benchmark --submit-eval "实际已填评分表.yaml" --project "对应项目ID"
```

将冻结课程包交给真实教师；保留 `run`、`target` 和版本字段，填写必需评分及真实评论。
修改比例只能来自实际修改记录。AI 打分不能计入 Human Score。课程变更后重新导出新包，
旧版评分不得挪给新版。细节见[评价流程](evaluation-workflow.md)。

## 9. API、存储与备份

启动后访问 http://127.0.0.1:8710/docs 查看可交互的 OpenAPI 文档，
http://127.0.0.1:8710/openapi.json 获取完整字段。接口清单见 [API 文档](api.md)。

服务没有多用户身份认证，应只供可信本机用户使用。`projects/<id>/` 保存输入、SQLite 状态、
不可变版本、快照、日志和导出。备份前停止构建和服务，再复制完整项目目录及相关配置/技能版本。
备份应保持私密。不要公开上传原始课程库。

删除课程项目是破坏性操作，请确认 ID 并先备份：

```bash
python -m pebs.cli delete --project 确认要删除的项目 --yes
```

## 10. 常见故障与验证

| 问题 | 处理 |
|---|---|
| 模型不可用 | 检查 YAML、PATH、环境变量和登录状态，修改后重启 |
| 配额/超时 | 查看失败步骤，合理调整预算或等待服务恢复 |
| 技能在列表里但不能运行 | 本机安装固定版本并执行 `verify()` |
| 证据索引为空 | 检查 pending/unsupported 论断和来源，不能绕过 |
| PII 拦截 | 脱敏；明显误报时提交不含个人资料的复现示例 |
| 正式导出失败 | 按门禁、版本、签署错误逐项处理，先导出草稿复核 |
| 缺少 PPT 缩略图 | 检查渲染器与渲染错误 |
| 教师评分过期 | 重新评价准确版本，不修改旧评分归属 |
| 控制台乱码 | PowerShell 设置 `$env:PYTHONIOENCODING='utf-8'` |

```bash
python -m compileall -q pebs
python -m pytest tests -q -m "not integration and not live_research"
python -m pytest tests -q -m integration
python -m pytest tests -q -m live_research
```

后两组检查需要相应渲染工具或外部服务。软件测试通过、真实构建成功、正式交付合格、教学有效，
是四个不同的判断。当前 M6 的真实教师评价和完整基准尚未完成。
