# Configuration Package

This directory contains the modular configuration system for the SDG Alignment Analyzer.

## Structure

### `__init__.py`
Re-exports the main configuration classes and data structures for backward compatibility.

**Exports:**
- `Config` - Application configuration class
- `config` - Global config instance
- `SDG_DEFINITIONS` - Dictionary of all 17 SDG definitions

### `settings.py`
Contains the `Config` dataclass with all application settings and parameters.

**Features:**
- Environment variable integration
- Path management with automatic directory creation
- SDG helper methods (get names, colors, keywords, etc.)
- Type hints throughout

**Key Settings:**
- Model configuration (embedding models, thresholds)
- Processing parameters (batch size, workers)
- Path configuration (data directories, cache)
- UI settings (Streamlit configuration)

### `sdg_definitions.py`
Contains the comprehensive SDG definitions for all 17 Sustainable Development Goals.

**Each SDG includes:**
- Official name and description
- General keywords
- Local government-specific keywords
- UN targets and indicators
- Official color code for visualization

**Usage:**
```python
from src.config import SDG_DEFINITIONS

# Access a specific SDG
sdg11 = SDG_DEFINITIONS[11]  # Sustainable Cities and Communities
print(sdg11['name'])  # "Sustainable Cities and Communities"
print(sdg11['local_gov_keywords'])  # List of relevant terms
```

### `paths.py`
Path constants and utilities for the application.

**Provides:**
- Project root directory
- Data directory paths (raw, processed, results)
- Cache and model directories
- Automatic directory creation

**Usage:**
```python
from src.config.paths import PROJECT_ROOT, DATA_DIR, RESULTS_DIR

# Access paths
pdf_files = list((DATA_DIR / "raw").glob("*.pdf"))
results = RESULTS_DIR / "my_analysis.json"
```

## Migration from Old config.py

The old single `config.py` file has been split into focused modules while maintaining 100% backward compatibility.

### Old Import Style (Still Works!)
```python
from src.config import Config, SDG_DEFINITIONS
config = Config()
```

### New Modular Approach (Recommended)
```python
# For configuration
from src.config.settings import Config
from src.config import config

# For SDG data
from src.config.sdg_definitions import SDG_DEFINITIONS

# For paths
from src.config.paths import RESULTS_DIR
```

## Benefits

1. **Better Organization**: Each module has a single, clear responsibility
2. **Easier Maintenance**: Changes to SDG definitions don't require touching configuration code
3. **Improved Readability**: Easier to find what you're looking for
4. **Modular Imports**: Import only what you need
5. **Type Safety**: Better type hint coverage
6. **Documentation**: Each module has clear docstrings

## SDG Helper Methods

The `Config` class provides convenient methods for accessing SDG data:

```python
from src.config import config

# Get SDG names mapping
config.sdg_names  # {1: "No Poverty", 2: "Zero Hunger", ...}

# Get SDG colors for visualization
config.sdg_colors  # {1: "#E5243B", 2: "#DDA63A", ...}

# Get specific SDG data
config.get_sdg_description(11)  # Full description of SDG 11
config.get_sdg_keywords(3)  # General keywords for Health
config.get_sdg_local_keywords(3)  # Local gov keywords for Health
```

## Testing

All imports have been verified to work correctly:
```bash
python -c "from src.config import Config, SDG_DEFINITIONS; print('✓ Imports successful')"
python -c "from src.alignment_engine import AlignmentEngine; print('✓ Core modules work')"
```

## Line Count Improvement

**Before:**
- `config.py`: 797 lines (monolithic file)

**After:**
- `settings.py`: 148 lines (configuration only)
- `sdg_definitions.py`: 554 lines (SDG data, most content)
- `paths.py`: 41 lines (path utilities)
- `__init__.py`: 19 lines (re-exports)
- **Total**: 762 lines

While the line count is similar, the code is now properly organized by responsibility rather than being a single unwieldy file.

## Future Enhancements

Potential future improvements:
1. Move SDG definitions to JSON/YAML for easier editing
2. Add validation for configuration values
3. Support for configuration profiles (dev, test, prod)
4. Hot-reloading of configuration in development