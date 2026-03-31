"""Centralized environment variable loading.

Provides a single source of truth for loading .env files across the application.
All modules should import and use this instead of calling load_dotenv directly.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


class EnvLoader:
    """Centralized environment variable loader.

    Usage:
        from src.config.env_loader import EnvLoader
        EnvLoader.load()  # Call once at application entry point
    """

    _loaded = False
    _env_path: Optional[Path] = None

    @classmethod
    def load(cls, env_path: Optional[Path] = None) -> bool:
        """Load environment variables from .env file.

        This should be called once at application entry point (e.g., app.py, main CLI scripts).
        Subsequent calls are no-ops to avoid redundant loading.

        Args:
            env_path: Optional path to .env file. If not provided, uses project root .env.

        Returns:
            True if .env was loaded, False if already loaded or not found
        """
        if cls._loaded:
            return False

        if env_path is None:
            # Default to project root .env
            cls._env_path = Path(__file__).parent.parent.parent / ".env"
        else:
            cls._env_path = env_path

        if cls._env_path.exists():
            load_dotenv(cls._env_path)
            cls._loaded = True
            return True
        else:
            # Fallback to default behavior (current working directory)
            load_dotenv()
            cls._loaded = True
            return True

    @classmethod
    def is_loaded(cls) -> bool:
        """Check if environment variables have been loaded.

        Returns:
            True if load() has been called, False otherwise
        """
        return cls._loaded

    @classmethod
    def get_env_path(cls) -> Optional[Path]:
        """Get the path to the loaded .env file.

        Returns:
            Path to .env file or None if not loaded
        """
        return cls._env_path

    @classmethod
    def reset(cls) -> None:
        """Reset the loader state. Useful for testing.

        This allows reloading environment variables in test scenarios.
        """
        cls._loaded = False
        cls._env_path = None


# Auto-load on import for backward compatibility
# This ensures existing code continues to work without explicit calls
EnvLoader.load()
