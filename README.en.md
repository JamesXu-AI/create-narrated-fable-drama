# Narrated Fable Drama

**English** · [中文](README.md)

> Turn a plain story you write into an AI narrated drama or fable short film,
> up to **240 seconds, 16:9**.

You need **zero filmmaking background** — no need to understand camera moves,
composition, lighting, editing, voice acting, or directing. You just tell the
story clearly; the professional cinematography, performance pacing, sound, and
finishing pipeline are all handled automatically.

---

## You Only Do Three Things

1. **Write the story** — write it in plain language, or just tell it in the chat;
2. **Name the target country** — used to decide the language and cultural context;
3. **Review each clip** — after each clip is generated, take a look and choose
   *Accept / Redo / Pause*.

> Everything else — rewriting the screenplay, designing characters and locations,
> planning shots, generating Seedance picture, mouth performance, native
> ambience/action sound, and disposable guide speech, then immediately replacing
> only character speech with exact phrase-aligned ElevenLabs Arabic,
> per-clip QC, seam
> repair, precise subtitles, and exporting the master — is done automatically by
> the project according to its built-in filmmaking standards.

---

## What Stories It Fits

- Humans, animals, fantasy characters, anthropomorphic objects, or hybrids;
- External voiceover narration;
- Ordinary character dialogue;
- A character speaking on camera, then continuing off camera in the same voice;
- A real-world frame story that opens into a nested fable and returns to the frame;
- A single segment switching between dialogue, on-camera storytelling, and
  off-camera storytelling while preserving one character voice.

---

## Output Specs

> The defaults already produce high-quality masters, so you don't need to
> memorize these; only mention a change in the chat if you want one.

| Item          | Rule                                                        |
| :------------ | :---------------------------------------------------------- |
| You provide   | One story + a target country                                |
| Aspect ratio  | Fixed `16:9` (landscape)                                    |
| Visual style  | Defaults to "3D Healing Animation"; specify another in chat |
| Resolution    | Defaults to `1080p`; choose `480p` / `720p` / `1080p` / `4K` |
| Max duration  | `240` seconds                                               |
| Language      | Arabic only; target country guides dialect and cultural context |
| Audio         | Seedance generates disposable character speech plus native ambience/action audio; each clip hard-mutes the mixed Seedance track only inside dialogue-replacement intervals, preserves it unchanged elsewhere, and inserts exact ElevenLabs Arabic. ElevenLabs generates dialogue only |
| Subtitles     | External and burned-in subtitles generated automatically; no text forced into the frame |

---

## How It Works

```text
Your story + target country
        │
        ▼
Auto: rewrite screenplay → design characters & locations → plan shots
        → independently audit every Seedance instruction
        → generate one Seedance clip with picture, mouth performance, temporary speech, and native ambience/action audio
        ├─ picture track: review immediately; after a fresh confirmation, a reviewed successor may start
        └─ audio track: immediately remove character speech, retain Seedance ambience/action sound, and insert only ElevenLabs Arabic dialogue
        │
        ▼
Complete A/V review after current dubbing passes → Accept / Redo / Pause   ← you step in here
        │
        ▼
Auto: stitch → repair seams → add subtitles → export the master
```

The whole pipeline runs automatically; **you only step in at the "per-clip
review" stage** — watch the clip, then decide to accept or redo.

---

## How You and the Project Collaborate

Before video generation actually starts, the project automatically completes the
upstream screenplay, design, and shot planning. It usually pauses to ask you only
when:

- The target country is missing;
- An important creative choice can't be decided safely on your behalf;
- It is about to overwrite content you already have.

Once video generation begins, the loop is:

1. The project shows a summary for one clip;
2. You confirm "generate this one clip, once";
3. The project generates and immediately reviews the picture; once it passes,
   the next picture may start after your separate fresh confirmation without
   waiting for the current dubbing;
4. The current clip completes Arabic dialogue replacement and full audiovisual
   review; you then choose accept, redo with changes, retry as-is, or pause;
5. After all clips are accepted, you confirm the final assembly plan.

> **Important:** The project never batch-generates or auto-retries behind your
> back — every single video generation requires your explicit, on-the-spot
> authorization.

---

## Core Features

This is where the product is most valuable, and what fundamentally sets it apart
from "casually generating an AI clip." You **don't need to understand or configure
any of it** — the system executes professional film-crew shot design and quality
control for you behind the scenes.

### 1. Cinematic Camera Language (Automatic Shot Design)

The system doesn't stitch random frames — it tells your story with a consistent
cinematic visual grammar, so the master looks "directed":

| Capability                | Description                                                   |
| :------------------------ | :------------------------------------------------------------ |
| Few characters on screen  | Only necessary characters appear, so the audience always knows where to look |
| Close-up-driven acting    | Favors ECU / CU / MCU to capture eyes, expression, mouth, and key actions |
| Consistent eyelines & axis | Who looks at whom, and who is on which side, stays consistent (the "180° axis / shot-reverse-shot"), so dialogue never breaks |
| Restrained wide shots     | Pulls out briefly only when the plot must show "who moved where," then returns to detail |
| Off-frame characters kept alive | A cropped-out character stays spatially connected via eyeline, sound, foreground, and later reactions |

> **Your benefit:** Without learning any camera, composition, or editing craft,
> you still get a master with deliberate framing, coherent eyelines, and the right
> emotional beats.

### 2. End-to-End Automatic QC & Correction (Four Gates Guarding Quality)

The system automatically "inspects and signs off" at key checkpoints. Failing any
gate **blocks the flow from moving forward**, stopping common AI-video failures at
the source:

1. **Screenplay gate** — checks whether each line can be spoken naturally within
   its shot duration, avoiding "machine-gun pacing" or "subtitles that can't keep
   up." Hard limits: no more than **4 characters/second** for Chinese, no more than
   **2.6 words/second** for English and similar, plus a start/end breathing margin
   for every line.
2. **Shot gate** — checks whether the storyboard follows the camera language above
   (few characters, close-up dominance, correct eyeline axis, wide shots only when
   needed), and verifies dialogue, speaker, and lip state segment by segment.
3. **Generation-instruction gate** — before video is actually generated, it
   reviews the shot order, framing, exact lines, and elements to exclude across all
   clips at once, ensuring a complete, self-consistent "shooting brief" is handed
   to generation.
4. **Independent prompt-audit gate** — a separate internal gate inside virtual
   production verifies the three-part structure, eight core elements, readable
   asset mapping, one dominant camera family per shot, anti-distortion fallback,
   and the audio ownership rule: Seedance supplies native ambience/action sound
   and disposable guide speech, while ElevenLabs replaces only exact Arabic
   character dialogue.
   Any prompt or storyboard change invalidates the old PASS.

In addition, each clip receives a separate picture review first; a passing picture
may serve as continuity evidence for the successor. After Arabic dialogue
replacement finishes, the system **watches the full clip at normal speed with
sound**, checking item by item:

- Whether the exact line appears only once, spoken by the correct character;
- Whether only the current on-camera speaker's mouth is moving;
- Whether the voice stays the same when a character shifts on camera to off camera;
- Whether the frame narrator, portraits, reflections, or silhouettes wrongly
  appear inside a nested fable;
- Whether identity, wardrobe, props, space, lighting, color, ambience, and action
  phase stay continuous;
- Whether eyeline direction and shot-reverse-shot stay on the same axis side;
- Whether close-up dominance holds and wide shots serve only necessary position
  changes;
- Whether there are extra characters, duplicated figures, subtitles, logos,
  watermarks, truncated speech, or replayed tail frames.

Any issue is reported explicitly, and it **never auto-retries and never fudges a
pass** — whether to accept is always your call.

> **Your benefit:** Runaway pacing, mismatched lips, character continuity breaks,
> text baked into the frame, and other typical AI failures are caught in bulk
> before you ever see them.

### 3. A Narrator That Actually "Tells the Story," Plus Nested Fables

The narrator isn't necessarily an unseen announcer. A grandfather, parent,
teacher, or protagonist can first speak on camera to others, then continue off
camera **in the same voice**. When they start telling a nested fable:

- The frame shows only the fable's characters and locations, and the **narrator
  does not wrongly appear on screen** (nor as a portrait, reflection, or
  silhouette);
- The narration keeps using that one established voice, never switching mid-way;
- When a fable character speaks, the narration pauses and only that character's
  mouth moves;
- When the story returns to reality, the original scene, positions, props, and
  voice are restored.

> **Your benefit:** Nested narration like "Grandpa told a story" is filmed
> correctly and coherently, instead of mixing the narrator and the story's
> characters together.

### 4. Automatic Editing (Cutting Clips into a Finished Master)

The clips you accept one by one are **automatically edited into a coherent, clean,
finished master** — seams, transitions, sound handoffs, and end-of-tail audio are
all handled for you, with **no editing software and no editing knowledge required**:

| Capability              | Description                                                   |
| :---------------------- | :------------------------------------------------------------ |
| Auto-assembled timeline | Stitches each accepted clip into one complete timeline, in the authoritative order of the screenplay and storyboard |
| Smart seams & transitions | Automatically decides and applies hard cuts, dissolves, or fades at each junction, so clips join naturally without jarring |
| Auto audio alignment    | Aligns sound to picture, bridges ambience, and fades the tail out to avoid end-of-clip pops or dropouts |
| AI-artifact removal     | Trims replayed tail frames, frozen/stuttering frames, repeated actions, extra footage, and truncated speech |
| Bounded picture smoothing | Applies only limited technical normalization of brightness / contrast / color — never altering characters, lines, or lip sync |

> All editing is **lossless and reversible**, performed only on clips **you have
> accepted**; it never silently changes or replaces your original clips. When a
> seam is uncertain, it pauses to let you look rather than fudging it.

> **Your benefit:** Without knowing how to edit, you still get a bunch of clips
> cut into one clean, coherent master with synchronized ElevenLabs Arabic dialogue
> and precise subtitles.

---

## What You Get in the End

A ready-to-use set of master files:

- A clean master (no subtitles);
- A captioned master;
- Standalone subtitle files (`SRT`, `VTT`);
- A delivery manifest.

> The project is only truly done after you **watch and accept** these files.

---

## When the Project Pauses to Ask You

| Situation                          | What you do                              |
| :--------------------------------- | :--------------------------------------- |
| It stops at the start asking for the country | Just tell it the target country in the chat |
| A generated picture needs review | Review the picture; a pass may release the next separately confirmed picture attempt |
| A dubbed clip needs acceptance | Watch the complete clip with sound and reply *Accept / Redo / Pause* |
| It warns a line is too long / pacing too fast | Ask it to shorten the line, or spread it into a longer clip |
| A generation fails                 | It won't auto-retry; it reports the issue and asks you to authorize once more |

---

## For Developers

The content above covers everything you need to "turn a story into a master";
regular users can stop here.

If you need to **set up the environment yourself, run scripts, configure remote
services, or do further development**, all technical commands, script parameters,
gate details, provider configuration, directory structure, and validation steps
are collected in **[`docs/DEVELOPER.md`](docs/DEVELOPER.md)**, kept fully separate
from this document.
