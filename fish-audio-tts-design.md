# Fish Audio TTS Integration Design

## Goal

Add optional Fish Audio as a TTS provider alongside Edge-TTS, selected via `.env` configuration. No fallback logic — the configured provider is used directly.

## Architecture

```
voice/
  __init__.py          # Re-exports: speak(), get_voice_assignment(), generate_audio()
  provider.py          # TTSProvider ABC + get_provider() factory
  edge.py              # EdgeTTSStrategy implementation
  fish.py              # FishAudioStrategy implementation
  player.py            # play_audio(), cleanup_audio() (unchanged)
```

`voices.py` is removed — voice pool logic migrates into `EdgeTTSStrategy`.

## .env Configuration

```env
# TTS Provider: "edge" (default) or "fish"
TTS_PROVIDER=edge

# Fish Audio per-role voice IDs (required when TTS_PROVIDER=fish)
FISH_API_KEY=your_fish_audio_key
FISH_VOICE_MODERATOR=voice_id_here
FISH_VOICE_PROPOSER=voice_id_here
FISH_VOICE_CRITIC=voice_id_here
FISH_VOICE_SPEAKER_A=voice_id_here
FISH_VOICE_SPEAKER_B=voice_id_here
FISH_VOICE_JUDGE=voice_id_here
```

- If `TTS_PROVIDER=fish` and a role's `FISH_VOICE_*` env var is missing, that role's voice playback is skipped with a warning log.
- Edge-TTS requires no extra env vars — it uses built-in voice pools with random assignment.

## TTSProvider ABC

```python
# voice/provider.py

class TTSProvider(ABC):
    @abstractmethod
    async def generate_audio(
        self, text: str, voice: str, output_path: Path | None = None
    ) -> Path: ...

    @abstractmethod
    def get_voice(self, role: str) -> str: ...

    @abstractmethod
    def voice_assignment(self) -> dict[str, str]: ...
```

### Methods

- `generate_audio(text, voice, output_path)` — async TTS generation, returns path to audio file
- `get_voice(role)` — returns the voice identifier string for a given role key
- `voice_assignment()` — returns full `{role: voice}` mapping dict

### Factory

```python
def get_provider() -> TTSProvider:
    provider = os.getenv("TTS_PROVIDER", "edge").lower()
    if provider == "fish":
        return FishAudioStrategy()
    return EdgeTTSStrategy()
```

Raises `ValueError` if `TTS_PROVIDER` is unrecognized.

## EdgeTTSStrategy

File: `voice/edge.py`

- Migrates `voice/tts.py` logic (text chunking, `edge_tts.Communicate`) into `EdgeTTSStrategy.generate_audio()`
- Migrates `voice/voices.py` random-pool-per-role logic into `EdgeTTSStrategy.get_voice()`
- Voice names remain Edge-TTS format (e.g. `en-US-AriaNeural`)
- Parameters like `rate`, `pitch`, `volume` are passed as kwargs with sensible defaults

## FishAudioStrategy

File: `voice/fish.py`

- Uses the `fish-audio` Python SDK from PyPI
- `generate_audio()` calls Fish Audio TTS API with the voice ID for the role
- Reads `FISH_API_KEY` from env for authentication
- Returns MP3 path compatible with pygame playback
- `get_voice(role)` reads from `FISH_VOICE_{ROLE}` env vars (e.g. `FISH_VOICE_MODERATOR`)
- `voice_assignment()` reads all `FISH_VOICE_*` vars and returns mapping

## player.py Changes

`speak()` currently hardcodes a call to `generate_audio_sync()` from `tts.py`. It will be updated to:

1. Accept a `TTSProvider` instance
2. Call `asyncio.run(provider.generate_audio(text, voice))` instead of `generate_audio_sync()`
3. The rest (pygame playback, cleanup) remains unchanged

## Public API (voice/__init__.py)

```python
from voice.provider import get_provider

_provider = get_provider()

def speak(text: str, role: str) -> None:
    voice = _provider.get_voice(role)
    audio_path = asyncio.run(_provider.generate_audio(text, voice))
    play_audio(audio_path)
    cleanup_audio(audio_path)

def get_voice_assignment() -> dict[str, str]:
    return _provider.voice_assignment()
```

Module-level `_provider` is initialized once at import time from `.env`.

## Consumer Changes

### Before

```python
from voice.voices import VoiceAssignment
from voice.player import speak as voice_speak

voices = VoiceAssignment()
voice_speak(text, voice=voices.moderator)
```

### After

```python
from voice import speak

speak(text, role="moderator")
```

Roles: `moderator`, `proposer`, `critic`, `speaker_a`, `speaker_b`, `judge`.

## Dependencies

Add to `pyproject.toml`:
```
fish-audio>=0.1.0
```

The `fish-audio` package is only imported when `TTS_PROVIDER=fish`, so it won't break Edge-TTS users who don't install it. However, we'll add it as a core dependency for simplicity.

## .env.example Updates

Add Fish Audio vars to the existing example file under a new `# Voice / TTS` section.

## Files Changed Summary

| File | Action |
|------|--------|
| `voice/provider.py` | New — ABC + factory |
| `voice/edge.py` | New — EdgeTTSStrategy |
| `voice/fish.py` | New — FishAudioStrategy |
| `voice/__init__.py` | Rewrite — new public API |
| `voice/player.py` | Modify — accept provider, remove direct tts import |
| `voice/tts.py` | Delete — logic moves to `edge.py` |
| `voice/voices.py` | Delete — logic moves to `edge.py` |
| `normal_critic_debate/debate.py` | Modify — new import pattern |
| `public_debate/public_debate.py` | Modify — new import pattern |
| `.env.example` | Modify — add TTS vars |
| `pyproject.toml` | Modify — add `fish-audio` dependency |