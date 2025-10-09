"""Configuration management utilities for whisper-typer CLI."""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import yaml


logger = logging.getLogger(__name__)


def get_config_dir() -> Path:
    """Get the configuration directory path."""
    return Path.home() / ".whisper-typer"


def get_config_path() -> Path:
    """Get the configuration file path."""
    return get_config_dir() / "config.yaml"


def ensure_config_exists() -> Path:
    """
    Ensure config.yaml exists in ~/.whisper-typer/
    Creates default config if it doesn't exist.
    
    Returns:
        Path to config.yaml
    """
    config_path = get_config_path()
    
    if config_path.exists():
        return config_path
    
    # Create directory if needed
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Create default config
    default_config = {
        "primary_language": "en",
        "hotkey": "<ctrl>+<alt>+<space>",
        "model_size": "tiny",
        "compute_type": "int8",
        "device": "cpu",
        "beam_size": 1,
        "vad_filter": True,
        "chunk_duration": 30
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
    
    return config_path


def open_config_in_editor() -> None:
    """Open config.yaml in the user's default editor."""
    config_path = ensure_config_exists()
    
    # Try to find a suitable editor
    editor = None
    
    # 1. Check EDITOR environment variable
    if 'EDITOR' in os.environ:
        editor = os.environ['EDITOR']
    
    # 2. Try common editors
    elif os.name != 'nt':  # Unix-like
        for cmd in ['nano', 'vim', 'vi', 'emacs', 'gedit', 'kate']:
            if shutil.which(cmd):
                editor = cmd
                break
    else:  # Windows
        for cmd in ['notepad.exe', 'notepad++.exe', 'code.exe']:
            if shutil.which(cmd):
                editor = cmd
                break
    
    if not editor:
        logger.warning(f"No editor found. Please edit manually: {config_path}")
        return
    
    try:
        subprocess.run([editor, str(config_path)], check=True)
    except subprocess.CalledProcessError:
        logger.error(f"Failed to open editor. Please edit manually: {config_path}")
    except FileNotFoundError:
        logger.error(f"Editor '{editor}' not found. Please edit manually: {config_path}")


def show_config() -> None:
    """Display current configuration."""
    config_path = ensure_config_exists()
    
    logger.info(f"Configuration file: {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            content = f.read()
        logger.info(content)
    except Exception as e:
        logger.error(f"Error reading config: {e}")


def reset_config() -> None:
    """Reset configuration to defaults."""
    config_path = get_config_path()
    
    # Remove existing config
    if config_path.exists():
        config_path.unlink()
    
    # Create new default config
    ensure_config_exists()
    
    logger.info("✓ Configuration reset to defaults")
    logger.info(f"  Location: {config_path}")


def validate_config() -> bool:
    """
    Validate configuration file.
    
    Returns:
        True if valid, False otherwise
    """
    config_path = ensure_config_exists()
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if not isinstance(config, dict):
            logger.error("Config file must contain a YAML dictionary")
            return False
        
        # Check required keys
        required_keys = ["primary_language", "hotkey", "model_size"]
        missing_keys = [k for k in required_keys if k not in config]
        
        if missing_keys:
            logger.error(f"Missing required keys: {', '.join(missing_keys)}")
            return False
        
        # Validate model_size
        valid_models = ["tiny", "base", "small", "medium", "large-v3"]
        if config["model_size"] not in valid_models:
            logger.error(f"Invalid model_size '{config['model_size']}'. Must be one of: {', '.join(valid_models)}")
            return False
        
        logger.info("✓ Configuration is valid")
        return True
        
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML syntax: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to validate config: {e}")
        return False
