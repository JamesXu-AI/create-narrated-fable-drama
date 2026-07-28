"""Arabic dubbing and lip-timing alignment services."""

from narrated_fable_drama.dubbing.arabic_segment import (
    ArabicSegmentEmbeddingError,
    embed_arabic_segment,
)
from narrated_fable_drama.dubbing.seedance_speech_gate import (
    SeedanceSpeechGateError,
    audit_seedance_character_speech,
)

__all__ = [
    "ArabicSegmentEmbeddingError",
    "SeedanceSpeechGateError",
    "audit_seedance_character_speech",
    "embed_arabic_segment",
]
