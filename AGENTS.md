# AGENTS.md

本文件适用于整个仓库。目标是先定位、后读取、逐级扩展，避免每次把源码、
长篇规范和近 1 GB 的 `workspace/` 一起全文扫描。

## 开始前

- 从仓库根目录工作；优先复用本文件的路径地图，不要先生成全仓库目录树。
- 先判断任务属于“共享代码、某个制作部门、规范、测试、运行产物”中的哪一类。
- 只读取当前任务需要的文件。执行或修改某个部门时，先完整读取该部门的
  `skills/<department>/SKILL.md`，再按其中的直接链接读取必要参考资料。
- `workspace/` 是可变任务数据和二进制媒体目录，不是源码检索入口。

## 最短定位流程

按以下顺序检索，命中后停止扩大范围：

1. 根据下方路径地图选 1 个主目录，必要时再加 `tests/unit/`。
2. 找文件名：

   ```bash
   rg --files <scope> | rg '名称或关键词'
   ```

3. 找 Python 定义、调用或文档标题：

   ```bash
   rg -n 'class |def |函数名|字段名' <scope> -g '*.py'
   rg -n '^#{1,4} |关键词' <scope> -g '*.md'
   ```

4. 只读取命中附近的行，例如 `sed -n '80,150p' FILE`；不要因一次命中就读取
   同目录所有文件。
5. 未命中时，先加入一个相邻范围或同义词，再检索；最后才扩大到全仓库文本。

不要使用 `find .`、`grep -R`、`tree`、`rg PATTERN .` 作为默认起手式。不要反复
执行全仓库 `rg --files`；本文件已经给出稳定目录结构。全局检索确有必要时至少
排除：

```bash
rg -n 'PATTERN' . \
  -g '!workspace/**' -g '!.git/**' -g '!.pytest_cache/**' \
  -g '!**/__pycache__/**' -g '!dist/**' -g '!build/**'
```

## 路径地图

| 要找的内容 | 首选位置 | 常见相邻位置 |
| --- | --- | --- |
| 总流程、全局门禁、人工确认 | `SKILL.md` | `README.md`、`references/` |
| 路径、项目上下文、JSON、通用校验、语速 | `src/narrated_fable_drama/core/` | `tests/unit/` |
| 剧本 schema、解析、对白/表演契约 | `src/narrated_fable_drama/contracts/screenplay/` | `skills/screenplay-writer/` |
| Storyboard 契约 | `src/narrated_fable_drama/contracts/storyboard.py`、`src/narrated_fable_drama/contracts/segment/storyboard.py` | `skills/previsualize-cinematography/` |
| Segment prompt、handoff、execution、media 契约 | `src/narrated_fable_drama/contracts/segment/` | `skills/virtual-production/` |
| 资产目录、角色范围 | `src/narrated_fable_drama/contracts/asset_catalog.py`、`src/narrated_fable_drama/contracts/role_scope.py` | `skills/direct-production-design/` |
| Seedance、Seedream、SeedAudio 适配 | `src/narrated_fable_drama/providers/` | `src/narrated_fable_drama/providers/README.md` |
| 剧本生成与校验 | `skills/screenplay-writer/scripts/` | 对应 `references/` |
| 生产设计、图片和声音资产 | `skills/direct-production-design/scripts/` | 对应 `references/` |
| 分镜与摄影预演 | `skills/previsualize-cinematography/scripts/` | 对应 `references/` |
| 视频生成、尝试记录、边界预检 | `skills/virtual-production/scripts/` | 对应 `references/` |
| 视频审查证据 | `skills/video-review/scripts/` | `skills/video-review/SKILL.md` |
| 装配、字幕、修复、最终 QC | `skills/finish-postproduction/scripts/` | 对应 `references/`、`assets/` |
| CLI 入口 | `src/narrated_fable_drama/cli.py` | `pyproject.toml` |
| 仓库结构校验 | `scripts/validate_repository.py` | `pyproject.toml` |
| 回归测试 | `tests/unit/` | 与测试名对应的 `src/` 或 `skills/` 文件 |

## 创作内容的权威链

定位故事事实时按以下顺序查找，不要从运行日志或媒体文件反推：

```text
workspace/tasks/<task>/story.md
-> screenplay-writer/screenplay.md
-> direct-production-design/production-design-plan.json
   + workspace/assets/assets.json
-> previsualize-cinematography/storyboard.md
-> .pending/virtual-production/seedance-segment-scripts/segment-NNN.md
-> 已接受的 Segment 媒体
-> finish-postproduction/ 最终交付
```

- 故事、说话人、对白、镜头和剪辑语义以 Markdown 创作链为准。
- 生产设计 JSON 只管理资产规划与查找；provider/QC JSON 只记录技术事实。
- 修改某一阶段时，尊重其上游权威和部门产物所有权，不在下游重复维护另一份
  创作真相。

## `workspace/` 的窄范围规则

- 先用 `ls -1 workspace/tasks` 确定任务名，不要递归列出整个目录。
- 已知任务和阶段后，只列文本元数据：

  ```bash
  rg --files --hidden workspace/tasks/<task>/<stage> \
    -g '*.md' -g '*.json' -g '*.srt' -g '*.vtt'
  ```

- 查共享资产时先读 `workspace/assets/assets.json`；只有任务确实涉及某个资产时，
  才查看对应的 `workspace/assets/<kind>/<id>/`。
- 不要对 PNG、WAV、MP4 等二进制文件运行文本搜索或批量读取；使用仓库已有的
  media probe、审查或 finishing 脚本检查它们。
- `.pending/` 是流程中的有效隐藏目录。只在已知任务和阶段内用 `--hidden`，
  不要用 `rg --hidden` 扫全仓库。
- 除非用户明确要求处理运行产物，否则不要修改 `workspace/`。

## 修改与验证

- 修改前先搜索目标符号的定义、直接调用点和对应测试；不要凭文件名猜测影响面。
- 优先做最小改动，并在现有测试文件中补充最贴近行为的测试。
- 先运行最窄验证，再扩大：

  ```bash
  python3 -m pytest tests/unit/test_relevant_file.py -q
  python3 -m pytest tests/unit -q
  python3 scripts/validate_repository.py
  ```

- 涉及阶段产物时，使用对应部门脚本的校验命令；常用入口见 `README.md` 的
  “基本命令”，不要自行重写一套校验逻辑。
- 仅文档或检索规则改动不需要运行媒体生成，也不要调用远程 provider。
