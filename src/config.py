"""Configuration loader for Whisper Typer UI."""

import os
from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    """Configuration loading or validation error."""
    
    def __init__(self, config_key: str, message: str = ""):
        self.config_key = config_key
        super().__init__(f"Configuration error for '{config_key}': {message}")


class AppConfig:
    """Application configuration loaded from config.yaml."""
    
    # Default values
    DEFAULTS = {
        "primary_language": "en",
        "hotkey": "<ctrl>+<alt>+<space>",
        "model_size": "base",
        "compute_type": "int8",
        "device": "cpu",
        "beam_size": 5,
        "vad_filter": True
    }
    
    VALID_MODEL_SIZES = ["tiny", "base", "small", "medium", "large-v3"]
    VALID_COMPUTE_TYPES = ["int8", "float16", "float32"]
    VALID_DEVICES = ["cpu", "cuda"]
    
    def __init__(self, config_path: str = "config.yaml"):
        """Load configuration from YAML file.
        
        Args:
            config_path: Path to config.yaml file
            
        Raises:
            ConfigError: If YAML is invalid or required keys are malformed
        """
        self.config_path = Path(config_path)
        self._config: dict[str, Any] = {}
        self._load_config()
        self.validate()
    
    def _load_config(self) -> None:
        """Load and parse YAML config file."""
        if not self.config_path.exists():
            # Use all defaults if file doesn't exist
            self._config = self.DEFAULTS.copy()
            return
        
        try:
            with open(self.config_path, 'r') as f:
                loaded = yaml.safe_load(f) or {}
                # Merge with defaults (loaded values take precedence)
                self._config = self.DEFAULTS.copy()
                self._config.update(loaded)
        except yaml.YAMLError as e:
            raise ConfigError("yaml_syntax", f"Invalid YAML syntax: {e}")
        except Exception as e:
            raise ConfigError("file_read", f"Failed to read config file: {e}")
    
    @property
    def primary_language(self) -> str:
        """Primary language for transcription (ISO 639-1 code)."""
        return self._config["primary_language"]
    
    @property
    def hotkey_combo(self) -> str:
        """Global hotkey combination in pynput format."""
        return self._config["hotkey"]
    
    @property
    def model_size(self) -> str:
        """Whisper model size (tiny, base, small, medium, large-v3)."""
        return self._config["model_size"]
    
    @property
    def compute_type(self) -> str:
        """CTranslate2 compute type (int8, float16, float32)."""
        return self._config["compute_type"]
    
    @property
    def device(self) -> str:
        """Device for model inference (cpu or cuda)."""
        return self._config["device"]
    
    @property
    def beam_size(self) -> int:
        """Beam size for transcription (lower = faster)."""
        return self._config["beam_size"]
    
    @property
    def vad_filter(self) -> bool:
        """Whether to use VAD filter to skip silence."""
        return self._config["vad_filter"]
    
    def validate(self) -> None:
        """Validate configuration values.
        
        Raises:
            ConfigError: If any configuration value is invalid
        """
        # Validate primary_language (basic ISO 639-1 check)
        lang = self.primary_language
        if not isinstance(lang, str) or len(lang) != 2 or not lang.isalpha():
            raise ConfigError("primary_language", f"Invalid ISO 639-1 code: {lang}")
        
        # Validate hotkey format (basic check - pynput will validate fully)
        hotkey = self.hotkey_combo
        if not isinstance(hotkey, str) or not hotkey:
            raise ConfigError("hotkey", f"Invalid hotkey format: {hotkey}")
        
        # Validate model_size
        model = self.model_size
        if model not in self.VALID_MODEL_SIZES:
            raise ConfigError("model_size", 
                f"Invalid model size '{model}'. Valid options: {', '.join(self.VALID_MODEL_SIZES)}")
        
        # Validate compute_type
        compute = self.compute_type
        if compute not in self.VALID_COMPUTE_TYPES:
            raise ConfigError("compute_type",
                f"Invalid compute type '{compute}'. Valid options: {', '.join(self.VALID_COMPUTE_TYPES)}")
        
        # Validate device
        device = self.device
        if device not in self.VALID_DEVICES:
            raise ConfigError("device",
                f"Invalid device '{device}'. Valid options: {', '.join(self.VALID_DEVICES)}")
        
        # Validate beam_size
        beam = self.beam_size
        if not isinstance(beam, int) or beam < 1:
            raise ConfigError("beam_size", f"beam_size must be a positive integer, got: {beam}")
        
        # Validate vad_filter
        vad = self.vad_filter
        if not isinstance(vad, bool):
            raise ConfigError("vad_filter", f"vad_filter must be boolean, got: {type(vad)}")
