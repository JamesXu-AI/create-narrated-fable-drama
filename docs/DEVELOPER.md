# 开发者指南

[English](DEVELOPER.en.md) · **中文**

本文档面向需要自己搭建环境、运行脚本或做进阶定制的开发者。

如果你只是想把一个故事做成成片，**不需要读本文档**——请看仓库根目录的
[`README.md`](../README.md)：你只要写故事、说明目标国家、逐段确认即可，
下面的命令、参数和配置都会由项目自动执行。

## 环境要求

- Python 3.11 或更高版本；
- 运行媒体审查和后期时，`ffmpeg`、`ffprobe` 必须在 `PATH` 中；
- 烧录字幕所用 FFmpeg 需要支持 `movie`、`overlay` 滤镜和 H.264 编码；
- `python3 -m pip install -e .` 会安装字幕渲染所需的 Pillow；阿拉伯文字整形
  必须能启用 Pillow RAQM，因此宿主还需要 FriBiDi 运行库；
- 字幕字体使用仓库内固定 SHA-256 的 OFL 版 Noto Sans Arabic，不依赖 Tahoma、
  `fontconfig` 或 `fc-match`；
- 只有图片、声音、视频生成阶段需要远程服务配置；
- 上传本地参考媒体或把结果持久化到 TOS 时，需要官方 TOS Python 包。

建议在仓库根目录创建独立环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

安装后检查阿拉伯文字整形能力：

```bash
python3 -c "from PIL import features; assert features.check_feature('raqm')"
```

如果检查失败，请为当前系统安装 FriBiDi 运行库并重新安装官方 Pillow wheel；
从源码构建 Pillow 时还必须显式启用 RAQM。字幕渲染不会退回到未整形文本或系统
字体。

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

## 创建任务

任务目录位于 `workspace/tasks/`。根目录只放一个 UTF-8、非空的 `story.md`；
不要创建任务表单、旁白 JSON 或其他创作元数据。

```text
workspace/tasks/my-fable/
└── story.md
```

## 各阶段的准确行为与命令

### 阶段 1：故事接收

任务根目录只允许 `story.md` 作为创作权威。故事可以是完整文本，也可以来自当前
对话。项目保持原故事的前提、人物关系、因果转折、高潮、后果和结尾；除非用户
明确授权改写，否则只改善表演、节奏、清晰度和可拍性。

### 阶段 2：剧本

Codex 根据剧本合同编写：

```text
TASK_DIR/screenplay-writer/screenplay.md
```

剧本必须记录目标国家、固定目标语言 `Arabic`、视觉风格、分辨率、`16:9`、
预计时长和 `elevenlabs_dubbed` 音频来源。每一句台词都必须是阿拉伯文字且不
混入拉丁字母，并包含：

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

Storyboard 负责最终的表演、摄影、灯光、剪辑、ElevenLabs 配音窗口、参考图的
包含与省略、Generation Segment 划分以及段间连续性。它不得给 Seedance 绑定
声音参考。它必须逐句保留剧本的精确文本、
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

Prompt 必须自包含全部镜头顺序、动作、表演、精确阿语台词、嘴部状态，以及
“Seedance 生成原生环境/动作音频并让可见角色以临时可听声音说出台词，随后切除
全部人物声并用 ElevenLabs 精确阿语替换”的唯一音频指令、引用、排除项、进入状态
和结束状态。每个 Segment 生成后，`virtual-production` 必须立即完成对白切除、
切口环境修补、角色 Voice ID 配音和逐段嵌入，不能留到全部片段完成后再统一处理。
创作意义不能被转移到伴随 JSON 中。

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

还必须运行独立的内部 Prompt 审计：

```bash
.venv/bin/python \
  skills/virtual-production/scripts/audit_segment_prompts.py \
  --task-dir TASK_DIR --all
```

它检查整份模型 Prompt 均为阿语（仅放行 `@ImageN/@VideoN` 引用令牌）、
三段式结构、八个核心要素、可读引用映射、每镜唯一主运镜、质量与防畸变兜底、
Storyboard 权威和阿语音频归属，并为每段写入当前
`seedance-prompt-internal-audit/v3` PASS 记录。Prompt、Storyboard、引用或审计规则变化后
必须重新审计。只有全量验证和独立审计都通过，才允许进入逐段视频生成。

### 阶段 6：逐段生成与审查

生成前先预检当前段：

```bash
python3 skills/virtual-production/scripts/preflight_segment.py \
  --task-dir TASK_DIR \
  --segment-script TASK_DIR/.pending/virtual-production/seedance-segment-scripts/segment-NNN.md
```

在当前对话中得到这一段的一次明确确认后，生成命令必须同时提供目标段和临时
人工确认断言：

```bash
python3 skills/virtual-production/scripts/generate_segment_videos.py \
  --task-dir TASK_DIR \
  --segments segment-NNN \
  --human-confirmed-segment segment-NNN
```

如果当前段依赖前一段，只有在前一段的确切 provider 画面完成直接审查、返回
`NO_ISSUES`，且必要连续性修正已经反映到后继段后，才可按预检要求传入
`--observed-predecessor SEGMENT_ID=PROVIDER_ATTEMPT_ID`。前一段的配音不必已经
完成；但后继段的每一次 Seedance 提交仍需要单独、即时的人工确认。

成功的当前媒体位于：

```text
TASK_DIR/.pending/virtual-production/generation-segments/segment-NNN/
├── video.mp4
├── last-frame.png
└── production-record.json
```

每一段 provider 任务成功后，`virtual-production` 先发布不可变的
`seedance-source.mp4`、尾帧和 `PICTURE_GENERATED` 记录，并立即启动相互独立的
画面轨与音频轨。画面轨审查故事动作、身份、构图、连续性、尾帧和视觉接缝；
返回 `NO_ISSUES` 后，另一个 Segment 进程可在获得新一轮人工确认后提交后继段，
无需等待当前段配音完成。

音频轨必须立即执行，不得延期或批处理。它检测并切除 Seedance 临时人物声，在
对白切口内硬静音完整 Seedance 混音，在切口外原样保留 Seedance 原生环境音和
动作音效，再按实际口型窗口嵌入映射 Voice ID 的精确阿语对白。ElevenLabs
只能生成阿拉伯语角色对白，不得生成环境音、动作音效、Foley、动物叫声、音乐、
房间底噪或任何其他非对白声音；整个过程不得重定时视频帧。只有音频和声音身份
门禁通过后，当前段才进入 `GENERATED` 和完整音画审查。

音频轨完成后，必须完整观看正常速度、带声音的视频，并按 README「核心特性 ·
全程自动质检与纠错」中的清单逐项核对。即使完整审查返回 `NO_ISSUES`，当前段仍
必须等待用户决定接受、修改后重做、原样重试或暂停。仅音频失败会阻止当前段接受
和后期制作，但不会撤销已通过审查的画面，也不会停止已单独授权的后继 Seedance
任务。

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
captioned master 必须时长一致并保留同步 ElevenLabs 阿语配音。

## 七个制作部门

各部门只修改自己拥有的产物：

| 部门 | 输入 | 拥有的输出与职责 |
| --- | --- | --- |
| `screenplay-writer` | `story.md`、对话中的国家/风格/分辨率 | 唯一 `screenplay.md`；故事改编、精确台词、说话方式、表演、状态变化、讲述切换 |
| `direct-production-design` | 故事、已验证剧本、共享资产库 | `production-design-plan.json`；角色、声音、服装、道具、场景和共享资产目录 |
| `previsualize-cinematography` | 剧本、生产设计、资产目录 | 唯一 `storyboard.md`；表演、摄影、灯光、剪辑、Segment 划分、引用绑定与连续性 |
| `virtual-production` | 已验证 Storyboard | 编写并审计每段 Prompt；提交 Seedance 画面与原生音轨；切除临时人物声，用无对白原生声修补切口，仅混入 ElevenLabs 阿语对白；完成内部音频门禁 |
| `video-review` | 权威文档或完整音画片段 | 独立审查结果；返回 `NO_ISSUES` 或最小、按责任部门路由的修正意见 |
| `finish-postproduction` | 全部已接受 Segment 和真实媒体证据 | 修复决策、装配、字幕、clean/captioned masters 与交付清单 |

完整规则分别位于：

```text
skills/screenplay-writer/SKILL.md
skills/direct-production-design/SKILL.md
skills/previsualize-cinematography/SKILL.md
skills/virtual-production/SKILL.md
skills/video-review/SKILL.md
skills/finish-postproduction/SKILL.md
```

## 四次全量门禁

1. **剧本门禁：** 检查完整剧本、角色范围和每句台词所属 Shot 时长。
2. **Storyboard 门禁：** 检查完整分镜、局部说话窗口、参考绑定、少角色、
   对视轴、近景主导和位置变化例外。
3. **Prompt 门禁：** 全部首版 Prompt 写完后，一次性检查完整集合、逐镜头
   景别、引用、精确台词、排除项与局部说话窗口。
4. **独立 Prompt 审计门禁：** 检查精确 Prompt 的三段式结构、八个核心要素、
   可读引用映射、每镜唯一主运镜、质量/防畸变兜底、Storyboard 权威和阿语音频
   归属。Prompt、Storyboard、引用或审计规则变化都会使旧 PASS 失效。

统一语速硬上限：

- CJK 文本：每秒不超过 4.0 个字符；
- 非 CJK 文本：每秒不超过 2.6 个词；
- 每句另需 0.25 秒起止余量。

任一门禁失败都会阻断下游，不能当作警告跳过。

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
├── README.md                         # 面向用户的使用说明
├── docs/DEVELOPER.md                 # 开发者/进阶技术指南（本文档）
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
│   └── providers/                    # Seedream、Seedance、SeedAudio、ElevenLabs 远程边界
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
| ElevenLabs 阿语配音 | `ELEVENLABS_API_KEY`、`ELEVENLABS_MODEL_ID`、`ELEVENLABS_VOICE_MAP` |
| TOS 持久化 | `STORAGE_TOS_REGION`、`STORAGE_TOS_ENDPOINT`、`STORAGE_TOS_BUCKET`、`STORAGE_TOS_ACCESS_KEY_ID`、`STORAGE_TOS_SECRET_ACCESS_KEY`、`STORAGE_TOS_KEY_PREFIX` |

`ARK_BASE_URL` 和 `SEEDAUDIO_API` 必须是 HTTPS。当前 Seedream 适配器只接受
代码中声明的固定模型 ID，使用其他值会直接失败。

`ELEVENLABS_VOICE_MAP` 是以剧本 Entity ID 为键、ElevenLabs Voice ID 为值的
JSON 对象，例如 `{"grandfather":"voice-id-1","fox":"voice-id-2"}`。可选
`ELEVENLABS_OUTPUT_FORMAT` 当前必须为 `mp3_*` 格式，缺省为
`mp3_44100_128`。`ELEVENLABS_MODEL_ID` 必须精确为
`eleven_multilingual_v2`；阿语分支不会把 `language_code=ar` 作为口音锁，
而是由角色资产中的中性城市利雅得沙特音色 Prompt 锁定口音，并仅在发送 TTS
时使用不改变原文字符的局部阿语注音。

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
| 提示缺少字幕字体或哈希不匹配 | 恢复 `skills/finish-postproduction/assets/fonts/` 中仓库固定的 Noto Sans Arabic 文件，不要改用系统字体 |
| 提示缺少 Pillow RAQM | 安装 FriBiDi 运行库和官方 Pillow wheel，并运行环境要求中的 RAQM 检查 |
| 字幕烧录失败 | 确认 FFmpeg 支持 `movie`、`overlay` 滤镜和 H.264 编码器 |

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
