"""Application settings and configuration for SDG Alignment Analyzer.

Contains the Config dataclass with all tunable parameters, environment variables,
and configuration settings for the application.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional

from .sdg_definitions import SDG_DEFINITIONS
from .env_loader import EnvLoader

# Environment variables are loaded centrally by EnvLoader
# No need to call load_dotenv here - EnvLoader auto-loads on import


@dataclass
class Config:
    """Application configuration with all settings and parameters."""

    # Model settings
    # Default: finetuned-enhanced model from Hugging Face Hub for best SDG alignment accuracy
    # Local path also supported for development: models/sdg-finetuned-enhanced/sdg-enhanced-finetuned-20260226_112509
    # Fallback: all-mpnet-base-v2 for general semantic understanding
    default_embedding_model: str = os.getenv(
        "DEFAULT_EMBEDDING_MODEL",
        "voyager205/sdg-finetuned-enhanced"
    )
    fallback_embedding_model: str = os.getenv("FALLBACK_EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # Similarity thresholds - use threshold_config.py as single source of truth
    # Do NOT hardcode values here - always call get_similarity_threshold()
    high_alignment_threshold: float = float(os.getenv("HIGH_ALIGNMENT_THRESHOLD", "0.5"))
    min_activity_length: int = int(os.getenv("MIN_ACTIVITY_LENGTH", "20"))

    # Use optimized thresholds (auto) or environment variables (fixed)
    threshold_mode: str = os.getenv("THRESHOLD_MODE", "auto")

    # Paths - now using Path objects from environment
    data_raw_path: Path = Path(os.getenv("DATA_RAW_PATH", "data/raw"))
    data_processed_path: Path = Path(os.getenv("DATA_PROCESSED_PATH", "data/processed"))
    data_results_path: Path = Path(os.getenv("DATA_RESULTS_PATH", "results"))
    cache_dir: Path = Path(os.getenv("CACHE_DIR", ".cache"))

    # Processing
    batch_size: int = int(os.getenv("BATCH_SIZE", "32"))
    max_workers: int = int(os.getenv("MAX_WORKERS", "4"))

    # Optional OpenAI settings
    use_openai: bool = os.getenv("USE_OPENAI", "false").lower() == "true"
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")

    # Streamlit
    streamlit_port: int = int(os.getenv("STREAMLIT_SERVER_PORT", "8501"))
    streamlit_address: str = os.getenv("STREAMLIT_SERVER_ADDRESS", "localhost")

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: Optional[str] = os.getenv("LOG_FILE")

    def __post_init__(self):
        """Ensure paths are Path objects and create directories."""
        # Ensure all path attributes are Path objects
        self.data_raw_path = Path(self.data_raw_path)
        self.data_processed_path = Path(self.data_processed_path)
        self.data_results_path = Path(self.data_results_path)
        self.cache_dir = Path(self.cache_dir)

        # Create directories if they don't exist
        self.data_raw_path.mkdir(parents=True, exist_ok=True)
        self.data_processed_path.mkdir(parents=True, exist_ok=True)
        self.data_results_path.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def sdg_names(self) -> Dict[int, str]:
        """Get mapping of SDG numbers to names.

        Returns:
            Dictionary mapping SDG numbers (1-17) to their names
        """
        return {sdg_num: data["name"] for sdg_num, data in SDG_DEFINITIONS.items()}

    @property
    def sdg_colors(self) -> Dict[int, str]:
        """Get mapping of SDG numbers to colors.

        Returns:
            Dictionary mapping SDG numbers (1-17) to their official colors
        """
        return {sdg_num: data["color"] for sdg_num, data in SDG_DEFINITIONS.items()}

    def get_sdg_description(self, sdg_num: int) -> str:
        """Get the description for a specific SDG.

        Args:
            sdg_num: SDG number (1-17)

        Returns:
            The description of the specified SDG
        """
        return SDG_DEFINITIONS.get(sdg_num, {}).get("description", "")

    def get_sdg_keywords(self, sdg_num: int) -> List[str]:
        """Get the keywords for a specific SDG.

        Args:
            sdg_num: SDG number (1-17)

        Returns:
            List of keywords associated with the specified SDG
        """
        return SDG_DEFINITIONS.get(sdg_num, {}).get("keywords", [])

    def get_sdg_local_keywords(self, sdg_num: int) -> List[str]:
        """Get the local government keywords for a specific SDG.

        Args:
            sdg_num: SDG number (1-17)

        Returns:
            List of local government-specific keywords for the SDG
        """
        return SDG_DEFINITIONS.get(sdg_num, {}).get("local_gov_keywords", [])

    def get_sdg_targets(self, sdg_num: int) -> List[str]:
        """Get the target indicators for a specific SDG.

        Args:
            sdg_num: SDG number (1-17)

        Returns:
            List of target indicators for the SDG
        """
        return SDG_DEFINITIONS.get(sdg_num, {}).get("targets", [])

    def get_sdg_indicators(self, sdg_num: int) -> List[str]:
        """Get the indicators for a specific SDG.

        Args:
            sdg_num: SDG number (1-17)

        Returns:
            List of indicators for the SDG
        """
        return SDG_DEFINITIONS.get(sdg_num, {}).get("indicators", [])
    def get_similarity_threshold(
        self,
        mode: str = "st",
        sdg: Optional[int] = None
    ) -> float:
        """
        Get optimized similarity threshold for specified mode and SDG.

        This method uses the optimized threshold configuration from threshold_config.py
        which provides research-based and empirically validated thresholds.

        Args:
            mode: 'st' for Sentence Transformer only, 'hybrid' for ensemble
            sdg: Optional SDG number (1-17) for SDG-specific threshold

        Returns:
            Optimized threshold value based on research and validation

        Examples:
            >>> config = Config()
            >>> config.get_similarity_threshold('hybrid')
            0.70
            >>> config.get_similarity_threshold('hybrid', sdg=12)
            0.50
            >>> config.get_similarity_threshold('st', sdg=17)
            0.35

        Note:
            - Returns SDG-specific threshold if available
            - Falls back to global default for the mode
            - Environment variables can override defaults (backward compatibility)
        """
        # Lazy import to avoid circular dependency
        from .threshold_config import get_threshold

        # Check for environment variable override first (backward compatibility)
        env_var = f"SIMILARITY_THRESHOLD_{mode.upper()}"
        if sdg is not None:
            env_var = f"SIMILARITY_THRESHOLD_SDG{sdg}_{mode.upper()}"

        if self.threshold_mode == "fixed" and os.getenv(env_var):
            return float(os.getenv(env_var))

        # Use optimized threshold configuration
        return get_threshold(mode=mode, sdg=sdg)

    def get_all_similarity_thresholds(self, mode: str = "hybrid") -> Dict[int, float]:
        """
        Get all SDG-specific thresholds for a mode.

        Args:
            mode: 'st' or 'hybrid'

        Returns:
            Dictionary mapping SDG number (1-17) to optimized threshold

        Example:
            >>> config = Config()
            >>> thresholds = config.get_all_similarity_thresholds('hybrid')
            >>> thresholds[12]
            0.50
        """
        from .threshold_config import get_all_thresholds
        return get_all_thresholds(mode=mode)

    def print_threshold_recommendations(self):
        """
        Print threshold recommendations and validation status.

        This displays the current threshold configuration, any validated results,
        and recommendations for future optimization.
        """
        from .threshold_config import print_threshold_table
        print_threshold_table()

    def get_optimization_status(self) -> Dict[str, Any]:
        """
        Get status of threshold optimization.

        Returns:
            Dictionary with optimization status and validation results
        """
        from .threshold_config import THRESHOLD_CONFIG
        from .threshold_config import get_threshold

        return {
            "config_version": THRESHOLD_CONFIG.get("version", "unknown"),
            "config_date": THRESHOLD_CONFIG.get("date", "unknown"),
            "validated_sdgs": list(THRESHOLD_CONFIG.get("validation", {}).keys()),
            "st_default": get_threshold('st'),
            "hybrid_default": get_threshold('hybrid'),
            "validated_threshold_sdg12": THRESHOLD_CONFIG.get("validation", {}).get("sdg_12_hybrid", {}),
        }

    @property
    def st_default_threshold(self) -> float:
        """
        Get default threshold for Sentence Transformer (ST-only) mode.

        Returns:
            Default threshold from threshold_config.py (currently 0.50)
        """
        return self.get_similarity_threshold('st')

    @property
    def hybrid_default_threshold(self) -> float:
        """
        Get default threshold for hybrid mode (ST + sdgBERT ensemble).

        Returns:
            Default threshold from threshold_config.py (currently 0.50)
        """
        return self.get_similarity_threshold('hybrid')
