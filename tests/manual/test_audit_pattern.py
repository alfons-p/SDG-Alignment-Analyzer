#!/usr/bin/env python3
import sys
import re
sys.path.insert(0, 'src')
from src.activity_extractor import ActivityExtractor

extractor = ActivityExtractor(min_activity_length=15, max_activity_length=100)

text = 'The Audit and Risk Committee was established to support Council.'
text_lower = text.lower()

# Test patterns
audit_patterns = [
    r'\baudit\s+and\s+risk\s+committee\b',
    r'\bstrategic\s+internal\s+audit\s+plan\b',
    r'\bconducted\s+my\s+audit\s+in\s+accordance\s+with\b',
    r'\baudit\s+act\s+1994\b',
    r'\bbasis\s+(for\s+opinion|of\s+opinion)\b',
    r'\bmisstatements?\s+are\s+considered\s+material\b',
    r'\bindependent\s+auditor["\']?s?\s+report\b',
]

print('Testing audit patterns:')
for pattern in audit_patterns:
    match = re.search(pattern, text_lower)
    print(f'  {pattern}: {"MATCH" if match else "no match"}')

# Check if non-activity filter works
is_non_act = extractor.text_processor._is_non_activity_content(text)
print(f'\n_is_non_activity_content: {is_non_act}')
