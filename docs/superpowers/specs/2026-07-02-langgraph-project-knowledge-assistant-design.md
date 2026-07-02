# LangGraph 项目知识助手设计

日期：2026-07-02

## 背景

当前 `/Users/cltx/projects/langgraph` 是一个 LangGraph 基础项目，现有流程偏向 `planner -> coder -> tester -> reviewer` 的自动代码生成流水线。目标是将其系统化重构为 `~/projects/escort_server/doll_escort_game_svr` 的半自动项目知识助手，并增加 SQLite 持久化。

目标 C++ 项目 `doll_escort_game_svr` 位于 `~/projects/escort_server/doll_escort_game_svr`，是公司项目，所在 git worktree 根目录为 `~/projects/escort_server`。首期助手对该项目默认只读索引和分析；任何编辑、构建、提交、推送或影响工作区状态的操作都必须先获得用户确认。

目标 C++ 项目 `doll_escort_game_svr` 是老项目，存在早期不规范开发带来的问题：注释可能过时，文档可能与实现不一致，属性名、函数名、文件名可能不能准确表达真实功能。因此本助手必须优先依据实际实现、调用关系、数据读写、控制流和副作用判断行为，不能把注释、文档、命名直接当作事实。

首期采用方案 A：SQLite Checkpointer + 文件摘要索引表。

## 目标

首期目标是半自动化助手，支持三类工作：

1. 项目问答：解释模块、文件、调用链、数据结构、启动流程、历史设计文档。
2. 需求调研：围绕业务问题检索代码和文档，整理影响范围、风险和待确认点。
3. 开发建议：理解需求，调研代码，生成方案、补丁建议、验证命令，但不直接修改 C++ 项目文件。

首期不追求自动闭环改代码。真正编辑 `doll_escort_game_svr` 文件、运行高成本构建、引入依赖、发布或提交都需要用户确认。

## 非目标

首期不实现以下内容：

- 不直接自动修改 `doll_escort_game_svr`。
- 不自动提交、推送、发布。
- 不引入向量检索或 embedding。
- 不实现完整 C++ AST 解析。
- 不引入 Deep Agents 或 Hermes Agent 作为首期核心运行时。
- 不把文档和注释当成权威事实。

## 核心原则

1. 实现优先于命名和注释。
2. 文档、注释、文件名、函数名只能作为线索。
3. 回答必须区分“实现证据”和“命名/注释/文档线索”。
4. 低置信度结论必须明确标注。
5. 发现代码与文档或命名冲突时，应记录 consistency flag，并在回答中提示。
6. 状态中不保存完整大文件内容，只保存摘要、相关路径、必要片段和结论，避免 checkpoint 膨胀。
7. 索引必须可增量更新，不能每次无差别全量重建。

## 总体架构

系统分为两条 LangGraph 流程：项目索引图和助手问答/调研图。

### 项目索引图 `index_graph`

负责将 `~/projects/escort_server/doll_escort_game_svr` 转成可查询的 SQLite 知识库。

流程：

```text
scan_project
  ↓
detect_changed_files
  ↓
classify_files
  ↓
extract_symbols
  ↓
summarize_implementation
  ↓
detect_consistency_flags
  ↓
write_index
```

职责：

- 扫描目标项目文件。
- 跳过构建产物、缓存、第三方目录。
- 根据 content hash 检测新增、变化、删除文件。
- 对文档、C++ 头文件、C++ 源文件、构建脚本和配置生成摘要。
- 粗粒度提取 C++ 符号。
- 基于实现总结行为和副作用。
- 检测注释、命名、文档与实现之间的疑似不一致。
- 写入 SQLite 项目知识库。

### 助手问答/调研图 `assistant_graph`

负责处理用户自然语言请求。

流程：

```text
classify_request
  ↓
retrieve_project_context
  ↓
analyze_request
  ↓
synthesize_response
  ↓
persist_research_note
```

请求类型：

- `project_qa`：项目问答。
- `requirement_research`：需求调研。
- `development_advice`：开发建议。
- `index_request`：索引或刷新索引请求。
- `unclear`：信息不足，需要澄清。

输出内容：

- 结论。
- 依据和相关文件。
- 影响范围。
- 风险点和不确定性。
- 建议修改位置。
- 建议验证命令。
- 需要用户确认的问题。

## 模块边界

建议重构后的目录结构：

```text
src/
  config.py
  state.py

  graph.py                  # 对外导出 assistant graph
  index_graph.py             # 项目索引图
  assistant_graph.py         # 问答/调研图

  storage/
    sqlite.py                # SQLite 连接、初始化、基础查询
    schema.sql               # 表结构
    project_index.py         # 项目索引读写 repository

  indexer/
    scanner.py               # 文件扫描
    classifier.py            # 文件分类
    summarizer.py            # 实现摘要
    symbol_extractor.py      # C++ 粗粒度符号提取
    consistency.py           # 命名/注释/文档不一致检测

  retriever/
    keyword_search.py        # 基于路径/摘要/符号的检索
    context_builder.py       # 组装给 LLM 的上下文

  nodes/
    classify_request.py
    retrieve_context.py
    analyze_request.py
    synthesize_response.py
    persist_research_note.py
```

旧的 `planner -> coder -> tester -> reviewer` 不作为首期主流程。可以暂时保留，也可以迁移到 legacy 区域，但新核心路径应围绕项目知识助手展开。

## SQLite 持久化设计

使用两个 SQLite 文件：

```text
checkpoints/langgraph.sqlite
checkpoints/project_index.sqlite
```

`langgraph.sqlite` 用于 LangGraph checkpointer。`project_index.sqlite` 用于项目知识库。两者分离，便于重建项目索引而不影响会话历史。

### LangGraph checkpointer

所有 `assistant_graph.invoke()` 都必须带 `thread_id`：

```python
config = {
    "configurable": {
        "thread_id": "doll_escort_game_svr:research:route-recalc"
    }
}
```

用途：

- 隔离不同会话。
- 支持中断后恢复。
- 支持后续 human-in-the-loop。
- 支持历史调研过程回放。

### 项目知识库表

#### `files`

```sql
CREATE TABLE files (
    path TEXT PRIMARY KEY,
    abs_path TEXT NOT NULL,
    file_type TEXT NOT NULL,
    language TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    mtime REAL NOT NULL,
    content_hash TEXT NOT NULL,
    indexed_at TEXT NOT NULL,
    status TEXT NOT NULL
);
```

#### `file_summaries`

```sql
CREATE TABLE file_summaries (
    path TEXT PRIMARY KEY,
    summary TEXT NOT NULL,
    responsibilities TEXT,
    key_points TEXT,
    dependencies TEXT,
    risks TEXT,
    evidence TEXT,
    inconsistencies TEXT,
    confidence TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(path) REFERENCES files(path)
);
```

#### `symbols`

```sql
CREATE TABLE symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL,
    symbol_type TEXT NOT NULL,
    name TEXT NOT NULL,
    signature TEXT,
    line_start INTEGER,
    line_end INTEGER,
    summary TEXT,
    observed_behavior TEXT,
    side_effects TEXT,
    confidence TEXT,
    FOREIGN KEY(path) REFERENCES files(path)
);
```

首期符号类型：

- `class`
- `struct`
- `enum`
- `function`
- `method`
- `macro`

#### `doc_summaries`

```sql
CREATE TABLE doc_summaries (
    path TEXT PRIMARY KEY,
    title TEXT,
    summary TEXT NOT NULL,
    topics TEXT,
    mentioned_files TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(path) REFERENCES files(path)
);
```

#### `research_notes`

```sql
CREATE TABLE research_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    request_type TEXT NOT NULL,
    question TEXT NOT NULL,
    answer_summary TEXT NOT NULL,
    related_paths TEXT,
    open_questions TEXT,
    created_at TEXT NOT NULL
);
```

#### `index_runs`

```sql
CREATE TABLE index_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_root TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    scanned_files INTEGER DEFAULT 0,
    changed_files INTEGER DEFAULT 0,
    summarized_files INTEGER DEFAULT 0,
    status TEXT NOT NULL,
    error TEXT
);
```

#### `consistency_flags`

```sql
CREATE TABLE consistency_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL,
    line_start INTEGER,
    line_end INTEGER,
    flag_type TEXT NOT NULL,
    subject TEXT NOT NULL,
    claimed_behavior TEXT,
    observed_behavior TEXT NOT NULL,
    evidence TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(path) REFERENCES files(path)
);
```

`flag_type` 示例：

- `comment_mismatch`
- `name_mismatch`
- `doc_mismatch`
- `side_effect_hidden`
- `stale_logic`
- `ambiguous_owner`

## State 设计

### `IndexState`

用于项目索引图：

```python
class IndexState(TypedDict):
    project_root: str
    run_id: int
    scanned_files: Annotated[list[ProjectFile], operator.add]
    changed_files: Annotated[list[ProjectFile], operator.add]
    skipped_files: Annotated[list[str], operator.add]
    summaries: Annotated[list[FileSummary], operator.add]
    symbols: Annotated[list[Symbol], operator.add]
    consistency_flags: Annotated[list[ConsistencyFlag], operator.add]
    errors: Annotated[list[str], operator.add]
```

List 字段必须使用 reducer，避免节点更新互相覆盖。

### `AssistantState`

用于问答/调研图：

```python
class AssistantState(TypedDict):
    project_root: str
    question: str
    request_type: str
    retrieved_context: Annotated[list[RetrievedContext], operator.add]
    related_paths: Annotated[list[str], operator.add]
    analysis: str
    answer: str
    open_questions: Annotated[list[str], operator.add]
    suggested_commands: Annotated[list[str], operator.add]
    research_note_id: int | None
```

`AssistantState` 不保存完整大文件内容，只保存检索摘要、相关路径、必要片段和最终结论。

## 索引节点设计

### `scan_project`

扫描目标项目，重点纳入：

```text
src/**/*.h
src/**/*.cpp
doc/**/*.md
doc/**/*.txt
CMakeLists.txt
linux_prj/*.sh
linux_prj/*.ini
*.AFCfile
```

默认跳过：

```text
.git/
build/
cmake-build-*/
__pycache__/
.venv/
venv/
.cache/
*.o
*.so
*.a
*.tar.gz
```

### `detect_changed_files`

计算 content hash，对比 `files` 表，只处理新增或变化文件，标记已删除文件。mtime 只作为快速判断辅助，content hash 是最终依据。

### `classify_files`

为文件打类型和语言：

- `source`
- `header`
- `doc`
- `build_config`
- `script`
- `config`
- `other`

也可以打业务 hint，例如 `map`、`route`、`escort`、`battle`、`resource`、`redis`、`db`、`network`、`startup`。这些 hint 只作为检索辅助，不作为事实。

### `extract_symbols`

轻量提取 C++ 符号和副作用线索。副作用线索包括：

- Redis / DB 写入。
- 对 `mutable_*` 的访问。
- `insert`、`erase`、`push_back`、`clear` 等状态修改。
- 发包、广播、通知。
- 挂帧、帧后、定时器。
- 线程切换、任务投递、异步处理。

### `summarize_implementation`

基于实际实现总结文件职责、关键数据结构、主要流程、外部依赖、副作用、风险点和置信度。注释和命名只能作为线索。若只看到注释或文档，置信度必须为 `low`。

### `detect_consistency_flags`

识别潜在不一致：

- 注释与代码不符。
- 文档与代码不符。
- 名字像只读，实际有写操作。
- manager 类承担多个跨模块职责。
- 函数名或字段名与副作用不符。
- 老文档流程与代码现状不一致。

### `write_index`

初始化表结构并写入索引数据。写入失败时当前 `index_runs` 标记为 `failed`，不能声称索引完成。

## 助手节点设计

### `classify_request`

分类用户请求。信息不足时输出澄清问题，不臆测。

### `retrieve_project_context`

从 SQLite 检索：

- 文件摘要。
- 文档摘要。
- 符号。
- consistency flags。
- 历史 research notes。

首期使用路径、关键词、中文业务词、符号名、文件类型和历史调研记录检索。不使用向量检索，但 retriever 模块要预留接口。

### `analyze_request`

根据请求类型分析。

项目问答输出结论、依据文件、置信度和不确定点。

需求调研输出影响模块、相关文件、可能改动点、风险点和待确认问题。

开发建议输出建议修改范围、推荐实施顺序、不建议直接动的区域和验证方式。

### `synthesize_response`

生成最终中文回答。必须包含：

- 结论。
- 依据。
- 相关文件。
- 风险和不确定性。
- 下一步建议。

如果存在命名、注释、文档不一致风险，必须明确提示。如果只基于摘要而非原始代码，必须说明置信度。

### `persist_research_note`

保存有复用价值的项目问答或需求调研结果。普通闲聊或无项目价值的问题不保存。

## 用户交互边界

### 可以自动执行

- 扫描项目。
- 增量索引。
- 读取代码和文档。
- 生成摘要。
- 检索相关文件。
- 解释模块。
- 做需求影响面分析。
- 给出修改建议。
- 给出验证命令。

### 不自动执行

- 不直接修改 `doll_escort_game_svr`。
- 不自动运行破坏性命令。
- 不自动删除项目文件。
- 不自动提交、推送、发布。
- 不把注释、文档、命名当作事实。

### 需要用户确认

- 编辑 C++ 项目文件。
- 大范围重建索引。
- 长时间运行构建。
- 引入新依赖。
- 采用低置信度结论作为实现依据。
- 涉及线上配置、发布、数据修复的建议。

## 错误处理

### 文件扫描错误

记录到 `IndexState.errors`，跳过该文件，索引 run 标记为 `partial_success`。

### LLM 摘要失败

有限重试。失败文件保留 `files` 元数据，摘要缺失或标记低置信，不阻塞整个索引。

### SQLite 写入失败

当前 run 标记为 `failed`，返回明确错误，不声称索引完成。

### 检索无结果

回答索引中未找到足够信息，建议刷新索引或给出具体目录/关键词，不编造项目结构。

### 代码和文档冲突

代码实现优先，记录冲突，给出冲突证据，降低置信度，并建议人工核对原始代码。

## 验证计划

首期实现完成后必须验证：

1. `assistant_graph` 和 `index_graph` 能 compile。
2. SQLite 表能初始化。
3. LangGraph SQLite checkpointer 能使用 `thread_id` 保存状态。
4. 能扫描 `doll_escort_game_svr`。
5. 能写入至少一批 `files` 记录。
6. 能对 `doc/readme.md`、`CMakeLists.txt` 和若干 `src/*.h/.cpp` 建立摘要。
7. 能通过自然语言问题检索相关文件。
8. 重复索引时能跳过未变化文件。
9. 对疑似命名或副作用不一致的函数能产生 `consistency_flags`。
10. 回答中能区分实现证据和注释/命名线索。

## 演进路线

### 阶段 1：文件级知识库

完成首期方案 A：SQLite checkpointer、项目索引库、文件级摘要、粗粒度符号、项目问答、需求调研、开发建议。

### 阶段 2：函数/类级细粒度索引

增加 chunk 或 symbol summary，支持函数级解释和更精准影响面分析。

可新增表：

- `chunks`
- `call_edges`
- `data_accesses`

### 阶段 3：向量检索

在 SQLite 关键词检索基础上加入 embedding 或外部 vector store，用于模糊语义问题。可新增 `embeddings` 表或接入 Chroma、FAISS、LanceDB 等。

### 阶段 4：开发任务生命周期记录

增加轻量任务记录：需求、方案、补丁建议、人工审批、验证结果、最终结论。

可新增表：

- `tasks`
- `approvals`
- `verification_runs`

### 阶段 5：Deep Agents / Hermes Agent 演进

稳定迭代期后，将部分 Worker 节点替换为 Hermes Agent，获得自改进能力。候选节点：

- `summarize_implementation`
- `detect_consistency_flags`
- `analyze_request`

预期能力：

- 自动反思摘要质量。
- 根据新问题修正旧索引。
- 记录成功和失败调研经验。
- 发现过时文档和命名误导。
- 沉淀项目专属开发经验。

Hermes Agent 不进入首期实现，仅作为后期架构预留。
