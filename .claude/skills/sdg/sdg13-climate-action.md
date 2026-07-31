---
name: check-sdg13-correction
description: Check SDG 13 (Climate Action) alignment quality
user-invocable: false
---

# SDG 13: Climate Action - Alignment Check

**Official Definition:** "Take urgent action to combat climate change and its impacts"

## Sample Activities (from 30 analyzed)

- "Climate Change Initiatives: Council will deliver a program of initiatives" (Score: 0.972)
- "Climate Action Plan... report provides details and an update" (Score: 0.996)
- "Southern Riverina Drought Resilience Action Plan" (Score: 0.927)
- "Supported by Rewiring Australia... six-week program" (Score: 0.993)
- "Coastal Management Program Council" (Score: 0.898)

## True Positive Activities

1. **Climate Mitigation**
   - Emissions reduction programs
   - Carbon neutral initiatives
   - Renewable energy projects
   - Energy efficiency programs

2. **Climate Adaptation**
   - Climate adaptation plans
   - Flood management
   - Drought resilience
   - Heat management

3. **Climate Planning**
   - Climate action plans
   - Sustainability strategies
   - Risk assessments

4. **Green Infrastructure**
   - Urban greening
   - Cool streets programs
   - Green roofs

**Keywords:** climate, carbon, emissions, renewable, adaptation, greenhouse, net zero, drought, flood, climate action

## False Positives

1. **General Environmental Programs**
   - Biodiversity programs (SDG 15)
   - General sustainability (SDG 11)

2. **Tree Planting Without Climate Focus**
   - Ornamental planting (SDG 11 or 15)
   - Parks (SDG 11)

3. **Flood Management Without Climate Context**
   - Routine drainage (SDG 6 or 9)

## False Negatives

1. **Climate Risk Planning**
   - Emergency management for climate events

2. **Green Building Standards**
   - Sustainability requirements

## Validation Checklist

- [ ] Does activity explicitly address climate change?
- [ ] Is it about emissions reduction or adaptation?
- [ ] Does it mention climate, carbon, or greenhouse gases?
- [ ] Is there clear climate context?

**General environmental programs → SDG 15 or 11, NOT SDG 13**

## Score Thresholds

- **STRONG (0.8+)**: Explicit climate action
- **MODERATE (0.6-0.8)**: Climate-related context
- **WEAK (<0.6)**: General environmental references