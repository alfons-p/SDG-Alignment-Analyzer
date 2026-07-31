---
name: check-sdg3-correction
description: Check SDG 3 (Good Health and Well-being) alignment quality
user-invocable: false
---

# SDG 3: Good Health and Well-being - Alignment Check

**Official Definition:** "Ensure healthy lives and promote well-being for all at all ages"

## Sample Activities (from 30 analyzed)

- "provided within Council owned Narromine Shire Family Medical Health Centre" (Score: 1.000)
- "Living Skills program was launched in collaboration with the William Campbell Foundation" (Score: 0.883)
- "Headspace Shepparton's Nature Scripts pilot project" (Score: 0.689)
- "Health and Wellbeing Program that subsidises the cost of health and wellbeing activities" (Score: 1.000)
- "mental, emotional, and social aspects that contribute to a thriving workforce" (Score: 0.991)

## True Positive Activities

1. **Medical Services**
   - Medical centers and clinics
   - Health centers
   - Immunization programs
   - Drug and alcohol services

2. **Mental Health Programs**
   - Headspace programs
   - Mental health support
   - Counseling services
   - Wellbeing programs

3. **Aged Care & Disability**
   - Aged care services
   - Disability support programs
   - Community nursing

4. **Public Health**
   - Health education programs
   - Disease prevention
   - Sexual health services
   - Maternal and child health

**Keywords:** health, medical, mental, wellbeing, clinic, hospital, disability, aged care, drug, alcohol, counseling

## False Positives

1. **General Recreation**
   - Sports facilities (exercise ≠ health services)
   - Parks and playgrounds
   - Fitness centers (unless health-focused)

2. **General Community Programs**
   - Community centers
   - General youth programs
   - Social activities

3. **Staff Wellbeing**
   - Employee wellness programs (internal, not public health)

## False Negatives

1. **Community Health Education**
   - Health promotion programs
   - Nutrition education

2. **Preventive Health**
   - Screening programs
   - Vaccination campaigns

## Validation Checklist

- [ ] Does activity provide health services or health education?
- [ ] Is there explicit mention of medical, mental health, or wellbeing?
- [ ] Does it target public health (not just fitness)?
- [ ] Is it a health facility or service?

**Sports facilities → SDG 11 (Communities), not SDG 3**

## Score Thresholds

- **STRONG (0.8+)**: Direct medical/mental health services
- **MODERATE (0.6-0.8)**: Health education or wellness
- **WEAK (<0.6)**: General wellbeing references