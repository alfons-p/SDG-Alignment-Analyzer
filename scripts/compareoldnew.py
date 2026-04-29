#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Mar 29 18:34:57 2026

@author: alfonspalangkaraya
"""

import pandas as pd

oldmaroondah2023 = pd.read_csv("/Users/alfonspalangkaraya/Documents/GitHub/claude3/sdg-alignment-analyzer/results-old/nofinancial/by_council/csv/VIC_Maroondah_Urban_2023_alignment.csv")
newmaroondah2023 = pd.read_csv("/Users/alfonspalangkaraya/Documents/GitHub/claude3/sdg-alignment-analyzer/results/nofinancial/by_council/csv/VIC_Maroondah_Urban_2023_alignment.csv")

maroondah = pd.merge(oldmaroondah2023, newmaroondah2023, on='activity_text', how='inner',
                     suffixes=['_o', '_n'])

maroondah = maroondah[['activity_text', 'word_count_o', 'section_type_o', 'relevance_score_o', 'top_sdg_o', 'top_sdg_name_o', 'top_score_o', 'top_sdg_n', 'top_sdg_name_n', 'top_score_n', 
                       'num_aligned_o', 'SDG_1_score_o', 'SDG_2_score_o', 'SDG_3_score_o', 'SDG_4_score_o', 'SDG_5_score_o', 'SDG_6_score_o', 'SDG_7_score_o', 'SDG_8_score_o', 'SDG_9_score_o', 'SDG_10_score_o', 'SDG_11_score_o', 'SDG_12_score_o', 'SDG_13_score_o', 'SDG_14_score_o', 'SDG_15_score_o', 'SDG_16_score_o', 'SDG_17_score_o', 'word_count_n', 'section_type_n', 'relevance_score_n', 'num_aligned_n', 'SDG_1_score_n', 'SDG_2_score_n', 'SDG_3_score_n', 'SDG_4_score_n', 'SDG_5_score_n', 'SDG_6_score_n', 'SDG_7_score_n', 'SDG_8_score_n', 'SDG_9_score_n', 'SDG_10_score_n', 'SDG_11_score_n', 'SDG_12_score_n', 'SDG_13_score_n', 'SDG_14_score_n', 'SDG_15_score_n', 'SDG_16_score_n', 'SDG_17_score_n']]