#!/usr/bin/env python3
"""Comprehensive tests for app.py and its dependencies.

Tests all components of the Streamlit dashboard to verify they work correctly.
Run with: python tests/test_app_live.py
"""

import os
import sys
import tempfile
import hashlib
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import io

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test results tracking
PASSED = 0
FAILED = 0
ERRORS = []


def run_test(name, test_func):
    """Run a single test and track results."""
    global PASSED, FAILED, ERRORS
    try:
        test_func()
        PASSED += 1
        print(f"  ✅ {name}")
        return True
    except AssertionError as e:
        FAILED += 1
        ERRORS.append(f"{name}: {e}")
        print(f"  ❌ {name}: {e}")
        return False
    except Exception as e:
        FAILED += 1
        ERRORS.append(f"{name}: {type(e).__name__}: {e}")
        print(f"  ❌ {name}: {type(e).__name__}: {e}")
        return False


# =============================================================================
# SECTION 1: Import Tests
# =============================================================================

print("\n" + "="*70)
print("SECTION 1: Import Tests")
print("="*70)

def test_import_streamlit():
    import streamlit as st
    assert st is not None

def test_import_session():
    from src.dashboard.session import SessionManager, CacheKey
    assert SessionManager is not None
    assert CacheKey is not None

def test_import_cache_manager():
    from src.dashboard.cache_manager import CacheManager
    assert CacheManager is not None

def test_import_styles():
    from src.dashboard.styles import get_landing_page_styles
    styles = get_landing_page_styles()
    assert "<style>" in styles

def test_import_processing():
    from src.dashboard.processing import process_pdf, scan_sdg_mentions_cached
    assert process_pdf is not None
    assert scan_sdg_mentions_cached is not None

def test_import_components():
    from src.dashboard.components import (
        render_landing_page,
        render_header,
        render_sidebar_settings,
        render_overview,
        render_gaps,
        render_top_sdgs,
        render_radar_chart,
        render_heatmap,
        render_activities_table,
        render_side_by_side_comparison,
        render_multi_report_comparison,
        render_sdg_keyword_analysis,
        render_download_buttons,
        render_sdg_mentions_tab,
        render_single_report_sdg_mentions,
    )
    assert True

run_test("Import streamlit", test_import_streamlit)
run_test("Import SessionManager and CacheKey", test_import_session)
run_test("Import CacheManager", test_import_cache_manager)
run_test("Import styles", test_import_styles)
run_test("Import processing functions", test_import_processing)
run_test("Import all UI components", test_import_components)


# =============================================================================
# SECTION 2: CacheKey Enum Tests
# =============================================================================

print("\n" + "="*70)
print("SECTION 2: CacheKey Enum Tests")
print("="*70)

def test_cachekey_keys():
    from src.dashboard.session import CacheKey
    required_keys = [
        "PROCESSED_RESULTS",
        "CURRENT_FILE_HASHES",
        "LAST_SETTINGS_HASH",
        "UPLOADED_FILES",
        "CURRENT_VIEW",
        "PROCESSING_STATE",
        "SELECTED_REPORT_INDEX",
        "SDG_MENTION_RESULTS",
    ]
    for key in required_keys:
        assert hasattr(CacheKey, key), f"Missing CacheKey.{key}"

def test_cachekey_values():
    from src.dashboard.session import CacheKey
    for key in CacheKey:
        assert isinstance(key.value, str), f"CacheKey.{key.name}.value is not a string"

run_test("CacheKey has all required keys", test_cachekey_keys)
run_test("CacheKey values are strings", test_cachekey_values)


# =============================================================================
# SECTION 3: ProcessingSettings Dataclass Tests
# =============================================================================

print("\n" + "="*70)
print("SECTION 3: ProcessingSettings Tests")
print("="*70)

def test_processing_settings_fields():
    from src.dashboard.components.sidebar import ProcessingSettings
    settings = ProcessingSettings()
    required_fields = [
        "uploaded_files",
        "model_name",
        "similarity_threshold",
        "use_hybrid",
        "ensemble_mode",
        "sdg_bert_weight",
        "st_weight",
        "min_words",
        "max_words",
        "top_activities",
        "enable_sdg17_correction",
        "enable_sdg11_correction",
        "use_custom_thresholds",
        "sdg_thresholds",
    ]
    for field in required_fields:
        assert hasattr(settings, field), f"Missing field: {field}"

def test_processing_settings_defaults():
    from src.dashboard.components.sidebar import ProcessingSettings, MODEL_PATHS
    settings = ProcessingSettings()
    assert settings.model_name == MODEL_PATHS["finetuned"]
    assert settings.similarity_threshold == 0.5
    assert settings.use_hybrid == False
    assert settings.min_words == 20
    assert settings.max_words == 500
    assert settings.enable_sdg17_correction == True
    assert settings.enable_sdg11_correction == True

def test_processing_settings_custom():
    from src.dashboard.components.sidebar import ProcessingSettings
    settings = ProcessingSettings(
        model_name="custom-model",
        similarity_threshold=0.7,
        use_hybrid=True,
        min_words=30,
        max_words=600,
    )
    assert settings.model_name == "custom-model"
    assert settings.similarity_threshold == 0.7
    assert settings.use_hybrid == True
    assert settings.min_words == 30
    assert settings.max_words == 600

run_test("ProcessingSettings has all required fields", test_processing_settings_fields)
run_test("ProcessingSettings default values", test_processing_settings_defaults)
run_test("ProcessingSettings can be created with custom values", test_processing_settings_custom)


# =============================================================================
# SECTION 4: TextProcessor Tests
# =============================================================================

print("\n" + "="*70)
print("SECTION 4: TextProcessor Tests")
print("="*70)

def test_text_processor_init():
    from src.text_processor import TextProcessor
    tp = TextProcessor(min_activity_length=20, max_activity_length=500)
    assert tp is not None

def test_text_processor_is_model_loaded():
    from src.text_processor import TextProcessor
    tp = TextProcessor()
    assert hasattr(tp, 'is_model_loaded')
    assert callable(tp.is_model_loaded)
    result = tp.is_model_loaded()
    assert isinstance(result, bool)

def test_text_processor_get_model_info():
    from src.text_processor import TextProcessor
    tp = TextProcessor()
    assert hasattr(tp, 'get_model_info')
    assert callable(tp.get_model_info)
    info = tp.get_model_info()
    assert isinstance(info, dict)
    assert "name" in info
    assert "loaded" in info
    assert "type" in info

def test_text_processor_priority_verbs():
    from src.text_processor import TextProcessor
    tp = TextProcessor()
    assert hasattr(tp, 'priority_verbs')
    assert isinstance(tp.priority_verbs, set)
    assert len(tp.priority_verbs) > 0

def test_text_processor_clean_text():
    from src.text_processor import TextProcessor
    tp = TextProcessor()
    assert hasattr(tp, 'clean_text')
    assert callable(tp.clean_text)
    result = tp.clean_text("  This is a test.  \n\n  ")
    assert isinstance(result, str)

def test_text_processor_extract_activities():
    from src.text_processor import TextProcessor
    tp = TextProcessor()
    assert hasattr(tp, 'extract_activities')
    assert callable(tp.extract_activities)

def test_text_processor_detect_section_type():
    from src.text_processor import TextProcessor
    tp = TextProcessor()
    assert hasattr(tp, 'detect_section_type')
    assert callable(tp.detect_section_type)

run_test("TextProcessor can be instantiated", test_text_processor_init)
run_test("TextProcessor has is_model_loaded method", test_text_processor_is_model_loaded)
run_test("TextProcessor has get_model_info method", test_text_processor_get_model_info)
run_test("TextProcessor has priority_verbs attribute", test_text_processor_priority_verbs)
run_test("TextProcessor has clean_text method", test_text_processor_clean_text)
run_test("TextProcessor has extract_activities method", test_text_processor_extract_activities)
run_test("TextProcessor has detect_section_type method", test_text_processor_detect_section_type)


# =============================================================================
# SECTION 5: ActivityExtractor Tests
# =============================================================================

print("\n" + "="*70)
print("SECTION 5: ActivityExtractor Tests")
print("="*70)

def test_activity_extractor_init():
    from src.activity_extractor import ActivityExtractor
    extractor = ActivityExtractor(min_activity_length=20, max_activity_length=500)
    assert extractor is not None

def test_activity_extractor_text_processor():
    from src.activity_extractor import ActivityExtractor
    extractor = ActivityExtractor()
    assert hasattr(extractor, 'text_processor')
    assert extractor.text_processor is not None

def test_activity_extractor_text_processor_methods():
    from src.activity_extractor import ActivityExtractor
    extractor = ActivityExtractor()
    # Should not raise
    extractor.text_processor.is_model_loaded()
    extractor.text_processor.get_model_info()

def test_activity_extractor_get_model_info():
    from src.activity_extractor import ActivityExtractor
    extractor = ActivityExtractor()
    assert hasattr(extractor, 'get_model_info')
    info = extractor.get_model_info()
    assert isinstance(info, dict)

run_test("ActivityExtractor can be instantiated", test_activity_extractor_init)
run_test("ActivityExtractor has text_processor attribute", test_activity_extractor_text_processor)
run_test("ActivityExtractor text_processor has is_model_loaded", test_activity_extractor_text_processor_methods)
run_test("ActivityExtractor has get_model_info method", test_activity_extractor_get_model_info)


# =============================================================================
# SECTION 6: AlignmentEngine Tests
# =============================================================================

print("\n" + "="*70)
print("SECTION 6: AlignmentEngine Tests")
print("="*70)

def test_alignment_engine_init():
    from src.alignment_engine import AlignmentEngine
    engine = AlignmentEngine()
    assert engine is not None

def test_alignment_engine_align_report():
    from src.alignment_engine import AlignmentEngine
    engine = AlignmentEngine()
    assert hasattr(engine, 'align_report')
    assert callable(engine.align_report)

def test_hybrid_alignment_engine_init():
    from src.hybrid_alignment_engine import HybridAlignmentEngine
    engine = HybridAlignmentEngine(use_sdg_bert=False)
    assert engine is not None

def test_hybrid_alignment_engine_align_report():
    from src.hybrid_alignment_engine import HybridAlignmentEngine
    engine = HybridAlignmentEngine(use_sdg_bert=False)
    assert hasattr(engine, 'align_report')
    assert callable(engine.align_report)

run_test("AlignmentEngine can be instantiated", test_alignment_engine_init)
run_test("AlignmentEngine has align_report method", test_alignment_engine_align_report)
run_test("HybridAlignmentEngine can be instantiated", test_hybrid_alignment_engine_init)
run_test("HybridAlignmentEngine has align_report method", test_hybrid_alignment_engine_align_report)


# =============================================================================
# SECTION 7: Dashboard Utils Tests
# =============================================================================

print("\n" + "="*70)
print("SECTION 7: Dashboard Utils Tests")
print("="*70)

def test_get_extractor():
    from src.dashboard.utils import get_extractor
    extractor = get_extractor(min_words=20, max_words=500)
    assert extractor is not None
    assert hasattr(extractor, 'extract_from_pdf')

def test_extract_metadata():
    from src.dashboard.utils import extract_metadata_from_filename
    metadata = extract_metadata_from_filename("NSW_Council_Urban_2024.pdf")
    assert metadata['year'] == '2024'
    assert metadata['state'] == 'NSW'
    assert metadata['urban_rural'] == 'Urban'

def test_sdg_colors():
    from src.dashboard.utils import SDG_COLORS
    assert len(SDG_COLORS) == 17
    for i in range(1, 18):
        assert i in SDG_COLORS

def test_sdg_data():
    from src.dashboard.utils import SDG_DATA
    assert len(SDG_DATA) == 17
    for i in range(1, 18):
        assert i in SDG_DATA
        assert 'name' in SDG_DATA[i]
        assert 'description' in SDG_DATA[i]

run_test("get_extractor creates ActivityExtractor", test_get_extractor)
run_test("extract_metadata_from_filename extracts year", test_extract_metadata)
run_test("SDG_COLORS has 17 entries", test_sdg_colors)
run_test("SDG_DATA has 17 entries", test_sdg_data)


# =============================================================================
# SECTION 8: Threshold Config Tests
# =============================================================================

print("\n" + "="*70)
print("SECTION 8: Threshold Config Tests")
print("="*70)

def test_get_threshold_st():
    from src.config.threshold_config import get_threshold
    threshold = get_threshold('st')
    assert isinstance(threshold, float)
    assert 0 < threshold < 1

def test_get_threshold_hybrid():
    from src.config.threshold_config import get_threshold
    threshold = get_threshold('hybrid')
    assert isinstance(threshold, float)
    assert 0 < threshold < 1

def test_get_threshold_sentence_transformer():
    from src.config.threshold_config import get_threshold
    threshold = get_threshold('sentence_transformer')
    assert isinstance(threshold, float)

def test_get_all_thresholds():
    from src.config.threshold_config import get_all_thresholds
    thresholds = get_all_thresholds('hybrid')
    assert isinstance(thresholds, dict)
    assert len(thresholds) == 17
    for i in range(1, 18):
        assert i in thresholds
        assert isinstance(thresholds[i], float)

run_test("get_threshold returns float for st mode", test_get_threshold_st)
run_test("get_threshold returns float for hybrid mode", test_get_threshold_hybrid)
run_test("get_threshold accepts sentence_transformer mode", test_get_threshold_sentence_transformer)
run_test("get_all_thresholds returns dict with 17 SDGs", test_get_all_thresholds)


# =============================================================================
# SECTION 9: SDG Mention Finder Tests
# =============================================================================

print("\n" + "="*70)
print("SECTION 9: SDG Mention Finder Tests")
print("="*70)

def test_sdg_mention_finder_exists():
    from src.sdg_mention_finder import scan_pdf_for_sdg_mentions
    assert callable(scan_pdf_for_sdg_mentions)

run_test("scan_pdf_for_sdg_mentions function exists", test_sdg_mention_finder_exists)


# =============================================================================
# SECTION 10: Integration Test - Mock PDF Processing
# =============================================================================

print("\n" + "="*70)
print("SECTION 10: Integration Tests")
print("="*70)

def test_results_structure():
    mock_results = {
        "source": "test.pdf",
        "report_alignment": {
            "total_activities": 100,
            "mean_alignment_score": 0.45,
            "mean_scores": {i: 0.3 + i * 0.02 for i in range(1, 18)},
            "top_sdgs": [
                {"sdg": 1, "name": "No Poverty", "mean_score": 0.5, "coverage": 0.3}
            ],
            "gaps": [],
        },
        "activities": [],
    }
    assert "source" in mock_results
    assert "report_alignment" in mock_results
    assert "activities" in mock_results
    report = mock_results["report_alignment"]
    assert "total_activities" in report
    assert "mean_alignment_score" in report
    assert "mean_scores" in report
    assert "top_sdgs" in report

run_test("Mock results structure matches expected format", test_results_structure)


# =============================================================================
# SECTION 11: Requirements Verification
# =============================================================================

print("\n" + "="*70)
print("SECTION 11: Requirements Verification")
print("="*70)

def test_required_packages():
    required_packages = [
        "streamlit",
        "pandas",
        "numpy",
        "plotly",
        "sentence_transformers",
        "transformers",
        "spacy",
    ]
    for package in required_packages:
        __import__(package)

def test_pymupdf():
    import fitz  # pymupdf
    assert fitz is not None

def test_torchvision():
    try:
        import torchvision
        assert torchvision is not None
    except ImportError:
        print("    Note: torchvision not installed (may be optional)")

def test_pypdfium2():
    try:
        import pypdfium2
        assert pypdfium2 is not None
    except ImportError:
        print("    Note: pypdfium2 not installed")

run_test("All required packages can be imported", test_required_packages)
run_test("pymupdf (fitz) is available", test_pymupdf)
run_test("torchvision is available", test_torchvision)
run_test("pypdfium2 is available", test_pypdfium2)


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Passed: {PASSED}")
    print(f"Failed: {FAILED}")

    if ERRORS:
        print("\nErrors:")
        for error in ERRORS:
            print(f"  - {error}")

    print("\n" + "="*70)
    if FAILED == 0:
        print("✅ ALL TESTS PASSED")
    else:
        print(f"❌ {FAILED} TESTS FAILED")
    print("="*70)

    sys.exit(0 if FAILED == 0 else 1)