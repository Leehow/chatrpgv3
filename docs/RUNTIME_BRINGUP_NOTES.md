# Runtime bring-up notes

本文记录这次把 `runtime` 分支拉到本地、接入 coding relay、合入模拟玩家并跑通项目时遇到的问题。

## 环境问题

- 本地没有 `.python-version` 里声明的 Python 3.14.6，实际可用版本是 3.14.5。项目约束已放宽到 `>=3.14.5,<3.15`，README 也同步到 3.14.5。
- `psycopg[pool]` 在本地缺少可直接导入的二进制实现，启动数据库检查会失败。依赖已改为 `psycopg[binary,pool]`。
- 本机常用的 5432 端口容易被已有 Postgres 占用，项目 compose 端口改为 `54324:5432`，`.env.example` 也同步使用 `localhost:54324`。
- Postgres 镜像的数据目录应挂到 `/var/lib/postgresql`，否则会遇到镜像初始化和持久化目录不匹配的问题。

## LLM 配置

- Pi LLM 已按本地 coding relay 接入：`CHATRPG_PI_BASE_URL=http://127.0.0.1:18888/v1`，`CHATRPG_PI_MODEL=gpt-5.5`。
- 本地 `.env` 使用相同 relay 配置；`.env.example` 保留了可复现的默认值，方便重新 bring-up。

## 模拟玩家合入问题

- 本地 `runtime` 起点落后 `origin/runtime` 11 个提交，远端新增了模拟玩家、模拟记录表、模拟 runner 和报告构建器。
- 合入后补了一个报告状态问题：直接使用 `--report-path` 导出时，Markdown/JSON 报告会拿到运行结束前的旧状态，导致报告显示 `running`。现在报告使用最终 run 状态。
- 用户侧要求 GM 输出、模拟玩家输出和战报始终中文，因此已把 main agent prompt、模拟玩家 prompt、persona 模板和战报模板改为中文输出约束。
- 后续发现模拟玩家像“给调试器写分析报告”，不是真人玩家发言。现在 `SimulatedPlayerAction.action` 只代表发给 GM 的短发言；`private_reasoning` 和 `public_rationale` 不再作为普通战报中的玩家发言展示。
- 后续发现战报只显示角色创建摘要，不显示完整角色卡。原因是 `SimulationReportBuilder` 只渲染 `gm_result.narration` 和事件类型，没有读取 `CharacterCreated.payload`。现在战报会从已记录的 `committed_events` 中抽取角色卡，渲染身份、资源、属性全/半/五分之一值、派生值、完整技能阈值、背景、装备、武器和状态。

## 无开场场景问题

现象：模拟玩家连续要求开场描述，但 GM 回答“当前时间、地点、任务委托尚未明确”。

根因不是剧本缺内容，而是运行时没有把冒险开场注入 session：

- `the_haunting` 的 AdventureIR 里存在玩家可见的 `unit_setup`，摘要是 1920s Boston 接受 Mr. Knott 委托调查 Corbitt House。
- 新 session 只创建 `sessions` 行，没有写入任何 `FrontierUnlocked` 事件。
- `StateReducer.initial()` 默认 `unlocked_frontier=[]`。
- `AdventureEngine.frontier()` 只返回已解锁 unit 里的场景和线索。
- `PlayEngine.turn()` 原本只把 intent 和已提交事件交给 narrator，没有把开场 unit/location/NPC 作为玩家可见事实传入。

处理方式：

- 第一回合发现冒险有 `player_visible` unit 时，自动提交对应 `FrontierUnlocked` 事件。
- 在构造 `NarrationRequest.visible_facts` 时加入 `adventure_frontier`，包含玩家可见 units、关联 locations 和公开 NPC 信息。
- 新增回归测试覆盖第一回合会 bootstrap 开场 unit，并把 Boston 和 Mr. Knott 放入叙事上下文。

## 角色创建工作流

用户指出 TRPG 的真实流程通常是先创建角色，再进入剧情，并且检定必须引用角色参数。已补：

- 新增 `CharacterTemplate` / `FormulaSpec`，把字段、派生值、创建步骤、source refs 做成数据化 IR。
- 新增安全公式求值器，只支持白名单算术、函数和 banded table，不执行任意代码。
- CoC 7e 调查员模板现在用 ID 链接字段和公式：`hp = floor((con + siz) / 10)`、`mp = floor(pow / 5)`、`sanity = min(99, pow)`、`sanity_max = 99 - cthulhu_mythos`、`personal_interest_points = int * 2`、`move = coc7e_mov(str, dex, siz, age)`、`damage_bonus/build = str + siz` 分段表。
- `CocInvestigatorFactory` 改成先走模板与公式审计，再生成 `CharacterState`，并补齐基础技能、技能阈值、属性阈值、装备/武器/财务/背景字段。
- 新增 `trpg-coc7e create-investigator`，可直接把调查员创建为 `CharacterCreated` 事件写入 session。
- `PlayEngine` 现在在没有任何 party 角色时不再推进 AdventureIR frontier，而是返回 `character_creation_required` 工作流状态；这避免“无角色直接进剧情”。
- `trpg-sim run` 默认会在模拟开始前自动创建 CoC 7e quick-fire 调查员，记录为第 0 回合，并写入 `CharacterCreated` 事件；设置 `--no-auto-create-character` 才会跳过。
- 角色创建记录会进入模拟 transcript 和最终战报，后续 GM 回合会看到 `party_status`，包含角色资源、traits、skills 和 conditions。

## Agent Loop 工作流

用户指出 GM agent 本质应该是 ReAct/tool-using agent，而不是单次 intent + 单次 narration。已补：

- 新增 `AgentLoopEngine`，每个玩家回合进入 observe → decide → tool → observe 的循环，循环上下文包含 state、workflow、party、frontier、available procedures 和 loop history。
- `PlayEngine.turn()` 现在负责构造初始 Runtime state、workflow/frontier bootstrap、调用 `AgentLoopEngine`、提交 loop 事件、再把已提交事实交给 Narrator。
- Agent loop 会把 Pi 返回的 `skill_calls` 绑定为 Runtime procedure call；Runtime 仍是骰子和状态权威。
- Agent loop 会调用 CoC native procedures、线索语义工具、pending clue 工具和 handout reveal 工具；所有结果以 `DomainEvent` 提交。
- 循环包含重复工具调用保护，避免同一 procedure/input 无限打转。
- 普通成功完成的 procedure 会停止工具循环；需要玩家选择的 Luck spend、失败/无效工具、clarification 会停在对应 stop reason；SAN 后续疯狂等规则触发可以继续进入后续工具处理。
- `PlayTurnResult` 和 simulation report 现在保留 `agent_trace`，方便 AI 调试 observe/decide/tool/commit 的每一步。
- 为兼容旧测试和外部调试入口，`PlayEngine._intent_with_bound_skill_call()` 保留为代理 helper。

## 验证

本次提交前已验证：

- `uv run ruff check .`：通过。
- `uv run mypy src tests`：通过。
- `uv run pytest`：通过。
- `uv run trpg quality guard`：通过。
- `uv run alembic upgrade head && uv run trpg db check`：通过。
- CI run 562 已通过：ruff、mypy、alembic upgrade、quality guard、pytest 全绿。
