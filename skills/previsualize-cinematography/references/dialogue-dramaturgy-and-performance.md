# Dialogue Dramaturgy and Performance

Rewrite dialogue as action between characters. Make every line change pressure, information, relationship, or choice, and make every change visible or audible.

Repair premise, structure, character arc, setup/payoff, and scene causality with [Screenwriting architecture and rewrite](screenwriting-architecture-and-rewrite.md) before polishing dialogue.

## Contents

- [Scene engine](#scene-engine)
- [Line ownership contract](#line-ownership-contract)
- [Dialogue rewrite hierarchy](#dialogue-rewrite-hierarchy)
- [Performance beat anatomy](#performance-beat-anatomy)
- [Subtext and playable direction](#subtext-and-playable-direction)
- [Listening and reaction](#listening-and-reaction)
- [Interruptions, overlap, and off-screen speech](#interruptions-overlap-and-off-screen-speech)
- [Ensemble scenes](#ensemble-scenes)
- [Dialogue acceptance](#dialogue-acceptance)

## Scene engine

Before rewriting lines, define:

```yaml
scene_question:
point_of_view_character:
audience_knows_suspects_and_must_not_see:
setup_or_payoff_obligation:
speaker_A_objective:
speaker_B_objective:
shared_obstacle:
incoming_relationship_pressure:
tactic_progression:
turn_or_reveal:
outgoing_relationship_state:
next_question:
```

If both characters want the same immediate outcome and nothing complicates it, the scene may be information delivery rather than drama. Introduce a credible difference in desire, knowledge, risk, timing, or willingness; do not manufacture conflict unrelated to the story.

## Line ownership contract

Assign every utterance a stable `line_id` and one owner:

```text
L07 | speaker: LIN | addressee: CHEN | trigger: CHEN hides the key |
intent: force a confession | subtext: I already know |
text: "你还要装到什么时候？" | delivery: quiet, clipped, no tears |
mouth: visible | listener: looks at the key, does not answer | 4.1–6.2s
```

Treat these as dialogue events too:

- Laugh, sob, gasp, sigh, hum, cough, whisper, mutter, and unfinished breath.
- Voice-over, phone voice, radio, television, memory voice, and off-screen speech.
- Group response, chant, interruption, simultaneous speech, and deliberate silence.

Do not use `他们说` or `有人回答` when identity matters. Do not let a reference audio file silently decide who speaks.

Give each principal character a distinct voice system: vocabulary/register, sentence length/rhythm, directness/evasion, humor/metaphor, habitual defense, forbidden admission, and pressure-state change. Reject lines that could be exchanged between characters without changing meaning or behavior.

## Dialogue rewrite hierarchy

Repair in this order:

1. **Cinematic behavior:** prefer a playable action, image, sound, silence, or reaction when dialogue would only explain it.
2. **Causality:** the line responds to something the speaker perceived or decided.
3. **Objective:** the speaker uses the line to obtain, avoid, test, conceal, provoke, comfort, or change something.
4. **Attribution:** speaker and addressee are unmistakable.
5. **Subtext:** the line does not merely announce the underlying emotion or plot fact.
6. **Escalation:** later lines change tactic or stakes instead of repeating.
7. **Voice:** wording and rhythm could belong only to this character in this pressure state.
8. **Speakability:** syntax, breath, vocabulary, and rhythm fit the character and moment.
9. **Duration:** the line plus preparation, turn-taking, and reaction fits the shot.

Prefer short, active lines. Remove names characters would not naturally repeat, exposition both speakers already know, and verbal descriptions of visible action. Preserve intentional repetition when it reveals denial, obsession, ritual, or a tactic shift.

## Performance beat anatomy

Direct each important line through these phases:

```text
cue -> register -> prepare -> speak -> listener absorbs -> after-beat
```

Example:

```text
CHEN hears the elevator bell (cue), stops turning the key (register),
keeps his eyes on the lock and swallows once (prepare), says quietly
"你还是来了" (speak). LIN does not answer; her grip loosens on the bag
(listener absorbs). CHEN finally looks back (after-beat).
```

Do not overload every line with all six phases. Compress routine exchanges; fully stage the line that changes the scene.

## Subtext and playable direction

Replace abstract labels with behavior and vocal action:

| Weak direction | Playable direction |
|---|---|
| very sad | suppresses the first breath, voice thins on the final word, avoids eye contact |
| angry | keeps volume low, jaw held, consonants clipped, moves the cup out of the other's reach |
| nervous | answers too quickly, then corrects herself; thumb rubs the torn label |
| in love | looks at the listener only after the joke lands; voice softens without slowing |
| shocked | speech stops, lips part without sound, eyes find the evidence before the person |

Give actors verbs: test, deflect, corner, soothe, bait, conceal, bargain, dismiss, confess, punish, invite. Avoid directing only with emotional adjectives.

## Listening and reaction

The listener remains active during speech. Assign one readable listening behavior:

- Tracks the speaker's face, avoids eye contact, or watches a relevant prop.
- Holds a pose until one word changes the body.
- Begins a reply, aborts it, inhales, swallows, or shifts weight.
- Protects, releases, hides, or offers a prop.
- Changes distance, orientation, or power without speaking.

Reserve a reaction shot only when the listener's change is the audience's new information. Otherwise let the reaction play in the master, over-the-shoulder foreground, or speaker's shot.

Silence must have an owner and an action. Write `LIN chooses not to answer; lips closed, gaze remains on the key`, not merely `pause`.

## Interruptions, overlap, and off-screen speech

Use interruption only with a defined takeover point:

```text
4.2–5.4s LIN: "我只是想——"
5.1–6.4s CHEN interrupts on "想": "你从来没问过我。"
```

Because overlap is high risk, prefer editorial sound design or separate coverage unless the interruption is essential. If overlap is requested, name both speakers, exact text, overlap window, dominant voice, mouth visibility, and listener behavior.

For off-screen speech, state:

```text
CHEN speaks from camera-right off-screen; only LIN is visible.
LIN's lips remain closed; she hears the line and reacts after the final word.
```

For voice-over, specify that no visible character lip-syncs unless the shot intentionally reveals the narrator speaking.

## Ensemble scenes

For three or more characters:

- Establish positions and eyeline groups before singles.
- Assign each line to one ID and one target or group.
- Keep silent characters on distinct listening tasks; do not animate every face equally.
- Use a master or subgroup two-shot to preserve geography.
- Avoid rapid round-robin dialogue inside one generation segment.
- Split simultaneous reactions by dramatic priority: primary, secondary, background.

Use a dialogue traffic table:

| Beat | Speaker | Addressee | Visible listeners | Dominant reaction | Camera purpose |
|---|---|---|---|---|---|

## Dialogue acceptance

Reject a dialogue scene when:

- A line has no trigger, objective, or identifiable owner.
- A character says information only for the audience that all characters already know.
- Several lines repeat the same tactic without escalation.
- The prompt asks for an emotion but gives no observable or audible performance.
- The listener becomes inert during the scene's decisive line.
- An interruption or overlap has no exact timing and voice priority.
- The line sounds natural on paper but cannot be spoken, breathed, and reacted to in the allotted time.
- The scene ends before the changed relationship or decision becomes readable.
