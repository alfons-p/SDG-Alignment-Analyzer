#!/usr/bin/env python3
"""Test to verify the Litchfield PDF bug fix."""

import pytest
from pathlib import Path
from src.activity_extractor import ActivityExtractor

def test_litchfield_pdf_extraction():
    """Test that NT_Litchfield_Urban_2025.pdf extracts activities correctly."""
    pdf_path = Path("/Users/alfonspalangkaraya/Documents/GitHub/claude3/sdg-alignment-analyzer/data/LGAcleannames/2025/NT/NT_Litchfield_Urban_2025.pdf")

    # Skip test if file doesn't exist
    if not pdf_path.exists():
        pytest.skip(f"Test file not found: {pdf_path}")

    # Initialize extractor
    extractor = ActivityExtractor(
        min_activity_length=20,
        max_activity_length=500,
        use_llm_labeling=False
    )

    # Extract activities
    result = extractor.extract_from_pdf(pdf_path)

    # Verify we got meaningful results
    assert result['total_activities'] > 0, "Should extract at least one activity"
    assert len(result['activities']) == result['total_activities'], "Activities list should match count"

    # Verify each activity has the required fields
    for activity in result['activities']:
        assert 'text' in activity, "Activity should have text"
        assert 'word_count' in activity, "Activity should have word_count"
        assert 'relevance_score' in activity, "Activity should have relevance_score"
        assert activity['word_count'] >= 20, "Activity should meet minimum word count"
        assert activity['relevance_score'] > 0.6, "Activity should pass relevance threshold"

    # Verify we got a reasonable number of activities
    # This is a 118-page annual report, should have many activities
    assert result['total_activities'] >= 10, f"Expected at least 10 activities, got {result['total_activities']}"

    print(f"✓ Successfully extracted {result['total_activities']} activities from {pdf_path.name}")

if __name__ == "__main__":
    test_litchfield_pdf_extraction()
    print("All tests passed!")