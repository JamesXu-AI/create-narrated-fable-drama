# Shared provider boundary

This is the only repository package that may implement remote provider calls.

- `runtime.py`: shared HTTP, Ark/TOS upload, configuration, and provider-neutral
  transport helpers.
- `seedream.py`: Seedream image generation.
- `seedance.py`: Seedance video creation, polling, and result retrieval.
- `seedaudio.py`: SeedAudio generation for retained voice-reference assets.

Department scripts may import these modules' public functions. They must keep
creative authority, validation, scheduling, local FFmpeg/FFprobe processing, and
task artifacts in their owning department, and must not duplicate credentials,
HTTP clients, remote SDK setup, upload logic, polling, or provider persistence.

The dependency direction is one-way:

```text
department scripts -> providers -> remote services
```

Provider modules never import a department and never author production artifacts.
