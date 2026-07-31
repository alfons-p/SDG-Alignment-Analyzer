---
name: check-sdg10-correction
description: Check SDG 10 (Reduced Inequalities) alignment quality
user-invocable: false
---

# SDG 10: Reduced Inequalities - Alignment Check

**Official Definition:** "Reduce inequality within and among countries"

## Sample Activities (from 30 analyzed)

- "Council is updating its Procurement Policy... suppliers comply with..." (Score: 0.607)
- "Support local services... for people with disability" (Score: 0.606)
- "Disability Inclusion Act 2014 Section 13" (Score: 0.591)
- "partners to promote transparency" (Score: 0.622)
- "Disability Inclusion Action Plan" (Score: 0.583)

## True Positive Activities

1. **Disability Services**
   - Disability access programs
   - Accessibility improvements
   - Disability inclusion plans
   - Support services for people with disabilities

2. **Multicultural Services**
   - Multicultural programs
   - Migrant support
   - Refugee services
   - CALD (Culturally and Linguistically Diverse) programs

3. **Indigenous Programs**
   - Reconciliation Action Plans
   - Indigenous support services
   - NAIDOC activities
   - First Nations programs

4. **Social Inclusion**
   - Social inclusion initiatives
   - Accessibility audits
   - Inclusive programs

**Keywords:** inclusion, disability, indigenous, multicultural, accessibility, equality, CALD, reconciliation, diverse, refugee

## False Positives

1. **General Community Programs**
   - Programs without specific inclusion focus
   - General community services

2. **Standard Services**
   - Routine services (unless explicitly targeting inequalities)

3. **General Procurement**
   - Procurement without social inclusion criteria

## False Negatives

1. **Reconciliation Action Plans**
   - Often missed as SDG 10

2. **Accessibility Audits**
   - Building accessibility improvements

3. **Multilingual Services**
   - Language services for diverse communities

## Validation Checklist

- [ ] Does activity specifically target disadvantaged groups?
- [ ] Is there explicit mention of disability, multicultural, or indigenous focus?
- [ ] Does it address accessibility or inclusion?
- [ ] Is it about reducing barriers?

**General community programs → SDG 11 or 17, NOT SDG 10**

## Score Thresholds

- **STRONG (0.6+)**: Explicit inclusion focus
- **MODERATE (0.4-0.6)**: Indirect inclusion component
- **WEAK (<0.4)**: General equality references