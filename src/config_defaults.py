"""Shared default configuration values for Whisper Typer."""

DEFAULT_CONFIG = {
    "primary_language": "en",
    "hotkey": "<ctrl>+<alt>+<space>",
    "model_size": "tiny",
    "compute_type": "int8",
    "device": "cpu",
    "beam_size": 1,
    "vad_filter": True,
    "chunk_duration": 30,
}
