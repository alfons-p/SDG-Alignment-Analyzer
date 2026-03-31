# SDG-specific ensemble weights
# Format: {sdg_number: (sdg_bert_weight, st_weight)}
#
# Based on script/analysis/optimize_threshold.py; 
#   5 fold cross-validation and sample size 250

SDG_ENSEMBLE_WEIGHTS = {
    1: (0.52, 0.48),   # sdgBERT 15%, ST 85%
    2: (0.535, 0.465),   # sdgBERT 15%, ST 85%
    3: (0.5, 0.5),   # sdgBERT 15%, ST 85%
    4: (0.5, 0.5),   # sdgBERT 15%, ST 85%
    5: (0.502, 0.498),   # sdgBERT 15%, ST 85%
    6: (0.511, 0.489),   # sdgBERT 15%, ST 85%
    7: (0.51, 0.49),   # sdgBERT 15%, ST 85%
    8: (0.15, 0.52),   # sdgBERT 15%, ST 85%
    9: (0.506, 0.494),   # sdgBERT 15%, ST 85%
    10: (0.537, 0.463),  # sdgBERT 15%, ST 85%
    11: (0.511, 0.489),  # sdgBERT 15%, ST 85%
    12: (0.505, 0.495),  # sdgBERT 15%, ST 85%
    13: (0.509, 0.491),  # sdgBERT 15%, ST 85%
    14: (0.509, 0.491),  # sdgBERT 15%, ST 85%
    15: (0.5, 0.5),  # sdgBERT 15%, ST 85%
    16: (0.51, 0.49),  # sdgBERT 15%, ST 85%
    17: (0.0, 1.0),    # sdgBERT 0%, ST 100% (sdgBERT doesn't support SDG 17)
}

DEFAULT_SDG_BERT_WEIGHT = 0.15
DEFAULT_ST_WEIGHT = 0.85