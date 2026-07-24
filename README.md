# Narrated Fable Drama / 寓言解说剧

这是一个把用户提供的 `story.md` 改编为 16:9 AI 解说剧或寓言短片的完整
Seedance 工作流。它支持：

- 人物、动物、幻想角色或混合主体，不限制必须是动物；
- 普通角色对白；
- 外部旁白；
- 角色自己担任讲述者；
- 现实框架戏引出嵌套寓言；
- 同一角色从画内对白自然转成画外讲述，再返回画内；
- Seedance 原生对白、旁白、环境音、音效与克制配乐；
- 精确字幕与 clean/captioned 两版成片。

例如，爷爷先与孙子对话，再由爷爷讲出寓言。进入寓言画面以后，爷爷可以
不出现在画面里，但必须继续使用同一个已经建立的爷爷声音；寓言角色开口时，
爷爷暂停，只有寓言角色的嘴部同步。这个切换会同时写进剧本、Storyboard 和
最终 Seedance Prompt。

## 工程结构

```text
create-narrated-fable-drama/
├── SKILL.md                         # 总编排与全局门禁
├── agents/                          # 根 Skill 的界面元数据
├── skills/                          # 六个职责隔离的制作部门
│   ├── screenplay-writer/
│   ├── direct-production-design/
│   ├── previsualize-cinematography/
│   ├── virtual-production/
│   ├── video-review/
│   └── finish-postproduction/
├── src/narrated_fable_drama/        # 跨部门共享 Python 包
│   ├── core/                        # 路径、项目上下文、通用运行支持
│   ├── contracts/                   # 剧本、资产、Segment 等共享契约
│   └── providers/                   # Seedance/Seedream/SeedAudio 适配器
├── scripts/                         # 项目级入口与结构校验
├── references/                      # 全局制作规范
├── tests/unit/                      # 单元测试
└── workspace/                       # 可变运行数据，不与代码混放
    ├── assets/                      # 共享资产与唯一资产目录
    └── tasks/                       # 各制作任务
```

首次在仓库根目录使用时安装本地共享包：

```bash
python3 -m pip install -e .
python3 scripts/validate_repository.py
```

## 输入

任务目录只需要：

```text
TASK_DIR/story.md
```

AI 先从当前对话判断目标国家：

- 已经知道：直接继续；
- 不知道：只问一次国家；
- 国家确定后：由剧本确定目标语言。

国家必须指定，没有默认值；缺失时 AI 必须先询问。画幅固定为 `16:9`。
视觉风格可在对话中指定，未指定时默认 `3D Healing Animation`（3D 治愈风格）。
分辨率也可在对话中指定，支持 `480p`、`720p`、`1080p`、`4k`，默认
`1080p`。无需额外任务表单。

## 创作信息放在哪里

创作权威只有：

```text
story.md
-> screenplay-writer/screenplay.md
-> previsualize-cinematography/storyboard.md
-> .pending/virtual-production/seedance-segment-scripts/segment-NNN.md
```

最终 `segment-NNN.md` 是 Seedance 真正看到的完整自然语言 Prompt。

生产设计仍可使用 JSON 管理可复用图片、声音和资产 URI，但 JSON 不得承载
旁白身份、对白切换、人物在场、镜头、表演或剪辑等故事含义。运行时的 provider
记录、QC 和交付清单也可以使用 JSON，因为它们只记录技术事实。

## 部门

```text
screenplay-writer
direct-production-design
previsualize-cinematography
virtual-production
video-review
finish-postproduction
```

根 `SKILL.md` 编排完整流程；各部门只修改自己拥有的产物。

## 自然对白 / 旁白切换

每一句话都必须声明：

- 精确说话人和精确文本；
- `on_camera_dialogue`、`on_camera_storytelling`、
  `off_camera_storytelling`、`external_voiceover` 或
  `embedded_character_dialogue`；
- 谁的嘴动、谁的嘴闭合；
- 触发切换的动作、短语落点或呼吸；
- 听者反应；
- J-cut、L-cut、视觉转场或声音桥；
- 同一声音是否跨镜头继续；
- 讲述者是画内、裁切在画外，还是完全不在该嵌套场景。

进入嵌套寓言时，如果爷爷不应出现在画面里，该 Segment 不提交爷爷的正向图片
参考，只保留已批准的声音参考，并在 Prompt 中明确“同一个爷爷声音继续画外
讲述”，同时正面描述当前真正可见的寓言画面。

## 基本命令

验证剧本：

```bash
python3 skills/screenplay-writer/scripts/build_screenplay.py check \
  --task-dir TASK_DIR
```

验证 Storyboard：

```bash
python3 skills/previsualize-cinematography/scripts/validate_storyboard.py \
  --task-dir TASK_DIR
```

验证所有 Seedance Prompt：

```bash
python3 skills/virtual-production/scripts/validate_segment_scripts.py validate \
  --task-dir TASK_DIR
```

生成一个经用户确认的 Segment：

```bash
python3 skills/virtual-production/scripts/generate_segment_videos.py \
  --task-dir TASK_DIR --segments segment-NNN
```

完成后期：

```bash
python3 skills/finish-postproduction/scripts/finish_postproduction.py \
  --task-dir TASK_DIR
```

## 三次全量门禁

1. 剧本生成后：全量校验剧本，并按每句所属 Shot 的时长校验语速。
2. Storyboard 生成后：全量校验 Storyboard，并按每句精确台词窗口校验语速。
3. 第一版全部 Segment Prompt 生成后：全量校验所有 Prompt、引用、精确台词
   与语速窗口。

统一硬上限为：CJK 文本每秒不超过 4.0 个字符，非 CJK 文本每秒不超过
2.6 个词，并为每句增加 0.25 秒起止余量。失败会阻断后续，不是警告。

## 人工确认

人工逐段确认从“全部 Segment Prompt 已生成且第三次全量门禁通过”之后开始。
此前除了缺少必填国家、无法安全推断的重要创作选择或破坏性覆盖，不进入逐段
确认。进入后，以下情况暂停：

- 即将调用视频生成；
- 每一个视频生成完成后；
- 需要用户决定重大故事方向；
- 最终装配前。

一次确认只授权一个 Segment 的一次生成尝试，不自动重试，也不自动生成下一段。

## 交付

```text
finish-postproduction/final-clean-master.mp4
finish-postproduction/final-captioned-master.mp4
finish-postproduction/subtitles/master.srt
finish-postproduction/subtitles/master.vtt
finish-postproduction/final-delivery-manifest.json
```
