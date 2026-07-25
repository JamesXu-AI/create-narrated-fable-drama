# Narrated Fable Drama / 寓言解说剧

把一篇用户提供的 `story.md` 制作为最长 240 秒、16:9 的 AI 解说剧或寓言短片。
项目覆盖剧本改编、生产设计、分镜预演、Seedance 原生音画生成、逐段审查、
后期修复、精确字幕和最终交付。

它适合：

- 人物、动物、幻想角色、拟人化物体或混合角色；
- 外部旁白；
- 普通角色对白；
- 角色在画内说话后，以同一个声音转为画外讲述；
- 现实框架戏引出嵌套寓言，再返回框架戏；
- 同一段中混合角色对白、讲述、环境音、音效与克制配乐。

它不是“一条命令直接生成成片”的黑盒。Codex 负责按仓库契约创作和维护
Markdown 权威文件，Python 脚本负责校验、媒体调用、技术证据和确定性渲染；
真正的视频生成严格执行“一次人工确认只授权一个 Segment 的一次尝试”。

## 核心约束与默认值

| 项目 | 规则 |
| --- | --- |
| 唯一初始文件 | `TASK_DIR/story.md` |
| 目标国家 | 必填；当前对话未提供时，写剧本前只询问一次 |
| 目标语言 | 在国家确定后由剧本确定 |
| 画幅 | 固定 `16:9` |
| 视觉风格 | 使用对话中的最新要求；缺省为 `3D Healing Animation` |
| 分辨率 | `480p`、`720p`、`1080p` 或 `4k`；缺省为 `1080p` |
| 最长总时长 | 240 秒 |
| 单个 Generation Segment | 通常 4–15 秒 |
| 音频 | Seedance 原生同步对白、讲述、环境音、音效和克制配乐 |
| 字幕 | 生成阶段禁止画面文字；后期生成 SRT、VTT 和烧录字幕版 |
| 角色视觉类型 | 项目级最多 8 种 |
| 人工生成授权 | 一个 Segment、一次尝试；不会授权下一段或自动重试 |

## 工作流概览

```text
用户故事 + 目标国家
        |
        v
story.md
        |
        v
screenplay-writer/screenplay.md
        |
        +--> direct-production-design/production-design-plan.json
        |         + workspace/assets/assets.json
        |
        v
previsualize-cinematography/storyboard.md
        |
        v
.pending/virtual-production/seedance-segment-scripts/segment-NNN.md
        |
        v
逐段确认 -> Seedance 生成 -> 完整音画审查 -> 用户接受或重做
        |
        v
真实媒体证据 -> 模型编写修复计划 -> 最终装配与字幕
        |
        v
clean master + captioned master + SRT + VTT + delivery manifest
```

生产设计 JSON 和资产目录位于创作链旁侧，只负责可复用视觉、声音和媒体 URI。
它们不能重新解释谁在说话、谁在画面中、镜头如何运动或场景如何剪辑。

## 快速开始

### 1. 环境要求

- Python 3.11 或更高版本；
- 运行媒体审查和后期时，`ffmpeg`、`ffprobe` 必须在 `PATH` 中；
- 烧录字幕所用 FFmpeg 需要支持 `subtitles`/libass 滤镜和 H.264 编码；
- 只有图片、声音、视频生成阶段需要远程服务配置；
- 上传本地参考媒体或把结果持久化到 TOS 时，需要官方 TOS Python 包。

建议在仓库根目录创建独立环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

需要 TOS 时：

```bash
python3 -m pip install 'tos>=2.9,<3'
```

先确认仓库结构和共享包可用：

```bash
narrated-fable-drama validate-repository
```

也可以直接运行：

```bash
python3 scripts/validate_repository.py
```

### 2. 创建任务

任务目录位于 `workspace/tasks/`。根目录只放一个 UTF-8、非空的 `story.md`；
不要创建任务表单、旁白 JSON 或其他创作元数据。

```text
workspace/tasks/my-fable/
└── story.md
```

然后在对话中告诉 Codex：

```text
请把 workspace/tasks/my-fable/story.md 制作为寓言解说剧。
目标国家是沙特阿拉伯，视觉风格使用 3D Healing Animation，输出 1080p。
```

如果已经在对话中直接提供故事，Codex 会把它保存到当前任务的 `story.md`。
如果没有提供目标国家，Codex 会在写剧本前询问；风格和分辨率缺失时直接使用
默认值，不增加任务表单。

### 3. 协作方式

在全部首版 Segment Prompt 写完并通过第三次全量门禁以前，流程会自动继续完成
确定性的非媒体前置工作。通常只在以下情况暂停：

- 缺少目标国家；
- 无法安全推断的重要创作选择；
- 即将破坏性覆盖已有内容。

第三次全量门禁通过后，进入正式人工循环：

1. Codex 展示一个 Segment 的生成摘要；
2. 用户确认只生成这一段的一次尝试；
3. Codex 生成并完整观看带声音的视频；
4. 用户选择接受、修改后重做、原样重试或暂停；
5. 全部 Segment 接受后，用户再确认最终装配计划。

“继续到结束”也不会预先授权未来的视频调用或重试。

## 六个制作部门

| 部门 | 输入 | 拥有的输出与职责 |
| --- | --- | --- |
| `screenplay-writer` | `story.md`、对话中的国家/风格/分辨率 | 唯一 `screenplay.md`；故事改编、精确台词、说话方式、表演、状态变化、讲述切换 |
| `direct-production-design` | 故事、已验证剧本、共享资产库 | `production-design-plan.json`；角色、声音、服装、道具、场景和共享资产目录 |
| `previsualize-cinematography` | 剧本、生产设计、资产目录 | 唯一 `storyboard.md`；表演、摄影、灯光、剪辑、Segment 划分、引用绑定与连续性 |
| `virtual-production` | 已验证 Storyboard | 每段一个完整 `segment-NNN.md` Prompt；预检、Seedance 提交和当前生成媒体 |
| `video-review` | 权威文档或完整音画片段 | 独立审查结果；返回 `NO_ISSUES` 或最小、按责任部门路由的修正意见 |
| `finish-postproduction` | 全部已接受 Segment 和真实媒体证据 | 修复决策、装配、字幕、clean/captioned masters 与交付清单 |

各部门只修改自己拥有的产物。完整规则分别位于：

```text
skills/screenplay-writer/SKILL.md
skills/direct-production-design/SKILL.md
skills/previsualize-cinematography/SKILL.md
skills/virtual-production/SKILL.md
skills/video-review/SKILL.md
skills/finish-postproduction/SKILL.md
```

## 各阶段的准确行为

### 阶段 1：故事接收

任务根目录只允许 `story.md` 作为创作权威。故事可以是完整文本，也可以来自当前
对话。项目保持原故事的前提、人物关系、因果转折、高潮、后果和结尾；除非用户
明确授权改写，否则只改善表演、节奏、清晰度和可拍性。

### 阶段 2：剧本

Codex 根据剧本合同编写：

```text
TASK_DIR/screenplay-writer/screenplay.md
```

剧本必须记录目标国家、目标语言、视觉风格、分辨率、`16:9`、预计时长和
`seedance_native` 音频来源。每一句台词都包含：

```text
L-NNN; speaker=<entity>; mode=<delivery-mode>;
gate=<visible/audible trigger>;
transition=<breath/reaction/J-cut/L-cut/action/silence handoff>;
delivery=<performance>; text="<exact target-language words>"
```

允许的说话方式：

```text
on_camera_dialogue
on_camera_storytelling
off_camera_storytelling
external_voiceover
embedded_character_dialogue
```

校验命令不会代替 Codex 创作剧本；`build` 和 `check` 都是读取并验证当前
`screenplay.md`：

```bash
python3 skills/screenplay-writer/scripts/build_screenplay.py build \
  --task-dir TASK_DIR
python3 skills/screenplay-writer/scripts/build_screenplay.py check \
  --task-dir TASK_DIR
python3 skills/screenplay-writer/scripts/character_performance_map.py \
  role-asset-scope --task-dir TASK_DIR
```

剧本完成后必须通过第一次全量语速门禁和角色/资产范围门禁。

### 阶段 3：生产设计

生产设计先写：

```text
TASK_DIR/direct-production-design/production-design-plan.json
```

共享资产统一放在仓库根目录：

```text
workspace/assets/assets.json
workspace/assets/characters/
workspace/assets/role-groups/
workspace/assets/locations/
workspace/assets/props/
workspace/assets/costumes/
```

每个 `Kind=individual` 的角色都有独立身份图；只有
`Kind=anonymous_ensemble` 使用群组图。会说话的独立角色才生成声音参考；
沉默角色仍保留独立视觉身份，但不创建声音。角色兼任讲述者时，只保留一个角色
身份和一个声音，不额外创建“旁白角色”。

任何 Seedream 调用前必须先检查语义复用和未登记的现存文件：

```bash
python3 skills/direct-production-design/scripts/build_initial_production_design.py \
  --task-dir TASK_DIR --inspect-semantic-reuse
```

确认复用、重新生成或接受新图片后再执行构建。以下参数可以重复使用：

```bash
python3 skills/direct-production-design/scripts/build_initial_production_design.py \
  --task-dir TASK_DIR --max-workers 4 \
  --codex-reuse-asset TARGET_ASSET_ID=SOURCE_ASSET_ID \
  --codex-regenerate-visual-asset TARGET_ASSET_ID \
  --codex-accept-generated-visual-asset ASSET_ID=SOURCE_URI
```

最后验证：

```bash
python3 skills/direct-production-design/scripts/validate_production_design.py \
  --task-dir TASK_DIR
```

已有媒体路径不在 `assets.json` 中时，流程会停止并要求恢复其语义和持久 URI；
绝不能因为“找不到资产 ID”就覆盖磁盘上的现有文件。

### 阶段 4：Storyboard

Codex 把全部上游信息编排为唯一：

```text
TASK_DIR/previsualize-cinematography/storyboard.md
```

Storyboard 负责最终的表演、摄影、灯光、剪辑、原生声音、参考图/声音的包含与
省略、Generation Segment 划分以及段间连续性。它必须逐句保留剧本的精确文本、
说话人、说话方式、嘴部状态、听者反应和音画交接。

验证：

```bash
python3 skills/previsualize-cinematography/scripts/validate_storyboard.py \
  --task-dir TASK_DIR
```

第二次全量门禁要求全部台词在实际 Segment 局部窗口内可自然说完，并检查少角色
构图、对视轴、近景主导和所有位置变化例外。

### 阶段 5：Segment Prompt

每个 Storyboard Generation Segment 编译为一个 Seedance 真正看到的完整自然
语言 Prompt：

```text
TASK_DIR/.pending/virtual-production/seedance-segment-scripts/segment-NNN.md
```

Prompt 必须自包含全部镜头顺序、动作、表演、精确台词、嘴部状态、声音、引用、
排除项、进入状态和结束状态。创作意义不能被转移到伴随 JSON 中。

必须先写完全部首版 Prompt，再运行无 `--segments` 参数的全量验证：

```bash
python3 skills/virtual-production/scripts/validate_segment_scripts.py validate \
  --task-dir TASK_DIR
```

只有输出同时满足：

```text
first_full_prompt_gate=PASS
speech_rate_gate.status=PASS
```

才允许进入逐段视频生成。

### 阶段 6：逐段生成与审查

生成前先预检当前段：

```bash
python3 skills/virtual-production/scripts/preflight_segment.py \
  --task-dir TASK_DIR --segment segment-NNN
```

在当前对话中得到这一段的一次明确确认后，生成命令必须同时提供目标段和临时
人工确认断言：

```bash
python3 skills/virtual-production/scripts/generate_segment_videos.py \
  --task-dir TASK_DIR \
  --segments segment-NNN \
  --human-confirmed-segment segment-NNN
```

如果当前段依赖前一段，只有在前一段的确切 provider attempt 已完成音画审查、
返回 `NO_ISSUES` 并处理必要连续性修正后，才可按预检要求传入
`--observed-predecessor SEGMENT_ID=PROVIDER_ATTEMPT_ID`。

成功的当前媒体位于：

```text
TASK_DIR/.pending/virtual-production/generation-segments/segment-NNN/
├── video.mp4
├── last-frame.png
└── production-record.json
```

每次生成后必须完整观看正常速度、带声音的视频，并检查：

- 精确台词是否只出现一次，是否由正确角色说出；
- 只有当前画内说话人的嘴在说话；
- 角色从画内转画外时是否仍是同一个声音；
- 嵌套寓言里是否误出现框架讲述者、画像、倒影或剪影；
- 身份、服装、道具、空间、灯光、色彩、环境音和动作阶段是否连续；
- 对视方向和正反打是否保持同一轴侧；
- 是否保持近景主导，宽景是否只服务于必要的位置变化；
- 是否出现多余角色、重复人物、字幕、Logo、水印、截断语音或回放尾帧。

即使审查返回 `NO_ISSUES`，也必须等待用户决定接受、修改后重做、原样重试或
暂停；失败不会触发自动重试。

### 阶段 7：后期与交付

全部当前 Segment 都有已接受的 `video.mp4` 和匹配的
`production-record.json`，且用户确认装配计划后，先生成真实媒体证据：

```bash
python3 skills/finish-postproduction/scripts/inspect_finish_media.py \
  --task-dir TASK_DIR
```

Codex 必须查看相邻段边界前后各 3 秒的画面和声音证据，再编写：

```text
TASK_DIR/.pending/finish-postproduction/llm-repair-plan.json
```

验证修复计划：

```bash
python3 skills/finish-postproduction/scripts/validate_repair_plan.py \
  --task-dir TASK_DIR \
  --evidence-manifest \
    TASK_DIR/.pending/finish-postproduction/llm-evidence/evidence-manifest.json \
  --repair-plan TASK_DIR/.pending/finish-postproduction/llm-repair-plan.json
```

存在不确定的剪点、溶解、颜色或声音交接时，先渲染短候选片段并人工检查，不能
让脚本自动决定创作修复。最终执行：

```bash
python3 skills/finish-postproduction/scripts/finish_postproduction.py \
  --task-dir TASK_DIR \
  --evidence-manifest \
    TASK_DIR/.pending/finish-postproduction/llm-evidence/evidence-manifest.json \
  --repair-plan TASK_DIR/.pending/finish-postproduction/llm-repair-plan.json
```

字幕文本直接来自 Storyboard Ordered Shots；ASR 不是文本权威。clean 与
captioned master 必须时长一致并保留同步原生音频。

## 三次全量门禁

1. **剧本门禁：** 检查完整剧本、角色范围和每句台词所属 Shot 时长。
2. **Storyboard 门禁：** 检查完整分镜、局部说话窗口、参考绑定、少角色、
   对视轴、近景主导和位置变化例外。
3. **Prompt 门禁：** 全部首版 Prompt 写完后，一次性检查完整集合、逐镜头
   景别、引用、精确台词、排除项与局部说话窗口。

统一语速硬上限：

- CJK 文本：每秒不超过 4.0 个字符；
- 非 CJK 文本：每秒不超过 2.6 个词；
- 每句另需 0.25 秒起止余量。

任一门禁失败都会阻断下游，不能当作警告跳过。

## 全项目镜头与表演原则

完整流程使用同一套视觉语法：

```text
最少可见角色
-> 明确对视轴、A/B 银幕侧和看向
-> ECU/CU/MCU 近景主导
-> 只有剧情必须读懂位置变化时才短暂放宽
-> 动作落点后立即回到关键表情、眼神、嘴部、手/爪或线索
```

新场景、漂亮环境、宏大规模、多人仍在现场或“增加镜头变化”都不能单独成为
宽景理由。角色在场不等于必须同框；裁切在画外的角色仍通过视线、声音、前景边缘
或后续反应保持空间连续性。

## 角色讲述与嵌套故事

项目不会默认旁白是看不见的播音员。爷爷、父母、老师或主角都可以先在画内与
他人对话，再用同一个声音继续画外讲述。

当讲述者进入嵌套寓言并不应出现在画面中时：

- 在自然语句、呼吸、反应、J-cut 或 L-cut 处完成交接；
- 保留同一个已批准声音参考；
- 不向该 Segment 提交讲述者的正向图片参考；
- 正面描述真正可见的寓言角色和场景；
- 明确禁止讲述者身体、肖像、倒影、剪影或重复观察者；
- 嵌套角色说话时，画外讲述暂停，只有嵌套角色嘴部同步。

返回框架戏时，需要恢复原场景、角色位置、道具、环境音和同一声音身份。

## 创作权威与运行数据

创作事实只存在于：

```text
story.md
-> screenplay-writer/screenplay.md
-> previsualize-cinematography/storyboard.md
-> .pending/virtual-production/seedance-segment-scripts/segment-NNN.md
```

允许的 JSON 只记录：

- 资产规划与共享资产查找；
- provider 请求的当前尝试事实；
- 生成媒体记录；
- 技术 QC 和修复执行参数；
- 最终交付清单。

不要创建第二份剧本、Storyboard JSON、旁白计划、声音计划、翻译追踪、
Prompt manifest、人工确认收据或私有创作账本。用户接受/重做决定保留在当前
对话中，不写成 approval JSON。

## 目录结构

```text
create-narrated-fable-drama/
├── AGENTS.md                         # 高效定位和检索规则
├── README.md                         # 项目使用说明
├── SKILL.md                          # 总编排、全局约束与完成条件
├── agents/                           # 根 Skill 的界面元数据
├── references/                       # 全项目制作与人工协作规范
├── scripts/
│   └── validate_repository.py        # 仓库结构和共享包编译校验
├── src/narrated_fable_drama/
│   ├── cli.py                        # 项目级 CLI
│   ├── core/                         # 路径、上下文、JSON、语速与通用校验
│   ├── contracts/                    # 剧本、资产、Storyboard、Segment 契约
│   ├── media/                        # FFmpeg/FFprobe 统一边界
│   └── providers/                    # Seedream、Seedance、SeedAudio 远程边界
├── skills/
│   ├── screenplay-writer/
│   ├── direct-production-design/
│   ├── previsualize-cinematography/
│   ├── virtual-production/
│   ├── video-review/
│   └── finish-postproduction/
├── tests/unit/                       # 单元测试
└── workspace/
    ├── assets/                       # 跨任务共享、唯一资产库
    └── tasks/                        # 各制作任务
```

一个完整任务最终可能包含：

```text
TASK_DIR/
├── story.md
├── screenplay-writer/
│   └── screenplay.md
├── direct-production-design/
│   └── production-design-plan.json
├── previsualize-cinematography/
│   └── storyboard.md
├── .pending/
│   ├── virtual-production/
│   │   ├── seedance-segment-scripts/
│   │   └── generation-segments/
│   └── finish-postproduction/
│       ├── llm-evidence/
│       └── llm-repair-plan.json
└── finish-postproduction/
    ├── final-clean-master.mp4
    ├── final-captioned-master.mp4
    ├── final-delivery-manifest.json
    └── subtitles/
        ├── subtitle-cues.json
        ├── master.srt
        └── master.vtt
```

## Provider 配置

provider 只从宿主进程环境读取配置，不会自动加载仓库内 `.env`。不要把密钥提交
到仓库。

| 能力 | 必需环境变量 |
| --- | --- |
| Seedream 图片 | `ARK_BASE_URL`、`SEEDREAM_API_KEY`、`SEEDREAM_MODEL` |
| Seedance 视频创建 | `ARK_BASE_URL`、`SEEDANCE_API_KEY`、`SEEDANCE_MODEL` |
| Seedance 查询/取消 | `ARK_BASE_URL`、`SEEDANCE_API_KEY` |
| SeedAudio 声音 | `SEEDAUDIO_API`、`SEEDAUDIO_API_KEY`、`SEEDAUDIO_MODEL` |
| TOS 持久化 | `STORAGE_TOS_REGION`、`STORAGE_TOS_ENDPOINT`、`STORAGE_TOS_BUCKET`、`STORAGE_TOS_ACCESS_KEY_ID`、`STORAGE_TOS_SECRET_ACCESS_KEY`、`STORAGE_TOS_KEY_PREFIX` |

`ARK_BASE_URL` 和 `SEEDAUDIO_API` 必须是 HTTPS。当前 Seedream 适配器只接受
代码中声明的固定模型 ID，使用其他值会直接失败。

安全检查配置状态，不输出密钥：

```bash
python3 -m narrated_fable_drama.providers.seedream --pretty config
python3 -m narrated_fable_drama.providers.seedance --pretty config
python3 -m narrated_fable_drama.providers.seedaudio --pretty config
```

远程访问只能通过 `src/narrated_fable_drama/providers/`。部门脚本不能重复实现
凭据、HTTP、上传、轮询或结果持久化。

如需将仓库或 workspace 放在其他位置，可使用：

```text
NARRATED_FABLE_DRAMA_ROOT
NARRATED_FABLE_DRAMA_WORKSPACE
```

自定义根目录必须包含 `pyproject.toml` 和 `SKILL.md`。

## 最终交付

```text
TASK_DIR/finish-postproduction/final-clean-master.mp4
TASK_DIR/finish-postproduction/final-captioned-master.mp4
TASK_DIR/finish-postproduction/subtitles/subtitle-cues.json
TASK_DIR/finish-postproduction/subtitles/master.srt
TASK_DIR/finish-postproduction/subtitles/master.vtt
TASK_DIR/finish-postproduction/final-delivery-manifest.json
```

技术完成状态为 `FINAL_MASTER_READY`，但项目只有在用户观看并接受交付文件后才算
真正完成。

## 常见阻断

| 现象 | 原因与处理 |
| --- | --- |
| 写剧本前停止 | 缺少必填目标国家；在对话中提供即可 |
| `Cannot find the narrated-fable repository` | 从仓库内运行，或设置有效的 `NARRATED_FABLE_DRAMA_ROOT` |
| 无法导入 `narrated_fable_drama` | 在仓库根目录执行 `python3 -m pip install -e .` |
| `speech_rate_gate` 失败 | 缩短精确台词或增加所属 Shot/Segment 的可用说话时间 |
| 角色/资产范围失败 | 检查剧本 `Kind`、角色定义和最多 8 种视觉类型限制 |
| 发现未登记资产文件 | 恢复其目录语义和 provider URI 到 `workspace/assets/assets.json`，不要覆盖生成 |
| `first_full_prompt_gate` 不是 `PASS` | 不带 `--segments` 重新验证完整首版 Prompt 集合 |
| provider 报缺少环境变量 | 运行对应 `--pretty config`，在宿主环境补齐配置 |
| 生成失败或审查失败 | 不自动重试；报告问题并重新取得当前 Segment 的一次授权 |
| 后期提示缺少当前媒体 | 确认每个 Storyboard Segment 都有匹配的 `video.mp4` 和 `production-record.json` |
| 找不到 `ffmpeg`/`ffprobe` | 安装 FFmpeg 并确认二进制位于 `PATH` |
| 字幕烧录失败 | 使用带 libass `subtitles` 滤镜和 H.264 编码器的 FFmpeg |

## 开发与验证

先运行最接近改动的测试，再运行完整单元测试和结构校验：

```bash
python3 -m pytest tests/unit/test_relevant_file.py -q
python3 -m pytest tests/unit -q
python3 scripts/validate_repository.py
```

代码风格配置位于 `pyproject.toml`：

```bash
python3 -m ruff check src skills scripts tests
```

仓库定位与检索请遵循 `AGENTS.md`：先按路径地图缩小范围，再搜索符号并只读取
命中附近内容；默认不要递归扫描体积很大的 `workspace/`。

## 进一步阅读

- `SKILL.md`：完整总编排、权威链和人工门禁；
- `references/narrated-fable-drama-production-standard.md`：全项目制作标准；
- `references/human-in-the-loop-guided-workflow.md`：对话式导演控制和逐段授权；
- `src/narrated_fable_drama/providers/README.md`：统一远程 provider 边界；
- 各 `skills/<department>/SKILL.md`：部门级输入、输出、职责和硬规则。
