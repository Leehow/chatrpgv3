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
- CoC 7e 调查员模板现在用 ID 链接字段和公式：`hp = floor((con + siz) / 10)`、`mp = floor(pow / 5)`、`sanity = min(99, pow)`、`personal_interest_points = int * 2`、`damage_bonus/build = str + siz` 分段表。
- `CocInvestigatorFactory` 改成先走模板与公式审计，再生成 `CharacterState`。
- 新增 `trpg-coc7e create-investigator`，可直接把调查员创建为 `CharacterCreated` 事件写入 session。

## 验证

本次提交前已验证：

- `uv run ruff check .`：通过。
- `uv run mypy src tests`：通过。
- `uv run pytest`：31 个测试通过。
- `uv run trpg quality guard`：通过。
- `uv run alembic upgrade head && uv run trpg db check`：通过。
- `uv run trpg-sim run ... --report-path artifacts/sim-scene-after-rebase.md`：通过。第一回合战报已出现中文开场，包含波士顿、二十世纪二十年代、Mr. Knott 和 Corbitt House 委托，并提交 `FrontierUnlocked`。
