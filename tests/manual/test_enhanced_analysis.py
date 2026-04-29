#!/usr/bin/env python
"""Test enhanced embeddings on a sample council report."""

import sys
sys.path.insert(0, '/Users/alfonspalangkaraya/Documents/GitHub/claude3/sdg-alignment-analyzer')

from pathlib import Path
from src.activity_extractor import ActivityExtractor
from src.alignment_engine import AlignmentEngine

print('=' * 80)
print('TESTING ENHANCED EMBEDDINGS - FULL COUNCIL REPORT')
print('=' * 80)

# Process Alpine Shire Council report
pdf_path = "data/raw/2024/VIC/V1 Alpine Shire Council Annual Report 2023-24.pdf"
output_dir = Path("results/test_enhanced")
output_dir.mkdir(parents=True, exist_ok=True)

print(f'\n[1/5] Processing: {pdf_path}')
print('-' * 80)

# Extract activities
print('\n[2/5] Extracting activities from PDF...')
extractor = ActivityExtractor()
activities_data = extractor.extract_from_pdf(pdf_path)

print(f"Total activities extracted: {activities_data['total_activities']}")
print(f"Document source: {activities_data['source']}")

# Show sample activities
print("\nSample activities:")
for i, activity in enumerate(activities_data['activities'][:5], 1):
    text = activity.get('text', '')[:100]
    print(f"  {i}. {text}...")

# Align with SDGs using enhanced embeddings
print('\n[3/5] Aligning activities with SDGs using enhanced embeddings...')
engine = AlignmentEngine()
results = engine.align_report(activities_data, show_progress=True)

# Display report-level alignment
print('\n[4/5] Report-Level Alignment Summary:')
print('-' * 80)
report = results['report_alignment']
print(f"Total activities analyzed: {report['total_activities']}")
print(f"Mean alignment score: {report['mean_alignment_score']:.4f}")

print('\nTop 5 SDGs by coverage:')
for sdg in report['top_sdgs'][:5]:
    print(f"  SDG {sdg['sdg']:2d}: {sdg['name'][:45]:45s} - Coverage: {sdg['coverage']:.2%}, Score: {sdg['mean_score']:.4f}")

print('\nSDGs with no coverage (gaps):')
if report['gaps']:
    for sdg in report['gaps'][:5]:
        print(f"  SDG {sdg['sdg']:2d}: {sdg['name']}")
else:
    print("  None - all SDGs have some coverage!")

# Show sample activity alignments
print('\n[5/5] Sample Activity Alignments:')
print('-' * 80)
for activity in results['activities'][:5]:
    text = activity['activity_text'][:80]
    top_sdg = activity['top_sdg']
    top_name = activity['top_sdg_name']
    score = activity['top_score']
    print(f"\nActivity: {text}...")
    print(f"  → Top SDG: {top_sdg} - {top_name} (score: {score:.4f})")
    print(f"  → Word count: {activity['word_count']}, Aligned SDGs: {activity['num_aligned']}")

# Save results
output_json = output_dir / "Alpine_Shire_enhanced_results.json"
output_txt = output_dir / "Alpine_Shire_enhanced_summary.txt"

print(f'\n[6/6] Saving results to: {output_dir}')
engine.export_to_json(results, output_json)

# Write summary
with open(output_txt, 'w') as f:
    f.write("SDG Alignment Analysis - Alpine Shire Council (Enhanced Embeddings)\n")
    f.write("=" * 80 + "\n\n")
    f.write(f"Total Activities: {report['total_activities']}\n")
    f.write(f"Mean Alignment Score: {report['mean_alignment_score']:.4f}\n\n")
    f.write("Top 10 SDGs:\n")
    for sdg in report['top_sdgs'][:10]:
        f.write(f"  SDG {sdg['sdg']:2d}: {sdg['name'][:45]:45s} - {sdg['coverage']:.2%} - {sdg['mean_score']:.4f}\n")

print(f'  - JSON: {output_json}')
print(f'  - Summary: {output_txt}')

print('\n' + '=' * 80)
print('ANALYSIS COMPLETE!')
print('=' * 80)
print(f'\nResults saved to: {output_dir}')
print(f"Enhanced embeddings successfully tested on {report['total_activities']} activities!")
