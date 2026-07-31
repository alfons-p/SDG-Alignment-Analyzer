---
name: check-sdg16-correction
description: Check SDG 16 (Peace, Justice and Strong Institutions) alignment quality
user-invocable: false
---

# SDG 16: Peace, Justice and Strong Institutions - Alignment Check

**Official Definition:** "Promote peaceful and inclusive societies for sustainable development, provide access to justice for all and build effective, accountable and inclusive institutions at all levels"

## Sample Activities (from 30 analyzed)

- "Internal audit provides independent and objective reviews... governance, risk management" (Score: 0.900)
- "Public Transparency Policy... good governance" (Score: 0.936)
- "Governance frameworks updated" (Score: 0.999)
- "Family Violence Statement of Commitment" (Score: 0.734)
- "Deliver initiatives to improve information and data management... privacy, security" (Score: 0.930)

## True Positive Activities

1. **Anti-Corruption**
   - Anti-corruption policies
   - Transparency initiatives
   - "No private benefit" policies
   - Conflict of interest declarations

2. **Governance**
   - Good governance frameworks
   - Public transparency policies
   - Accountability mechanisms
   - Internal audit

3. **Inclusive Institutions**
   - Public participation programs
   - Community engagement in decision-making
   - Representative governance
   - Councillor conduct policies

4. **Justice and Safety**
   - Legal services access
   - Community safety programs
   - Crime prevention
   - Family violence prevention

**Keywords:** governance, transparency, accountability, corruption, justice, institution, participation, civic, audit, policy, councillor

## False Positives

1. **General Community Programs**
   - Community events without governance focus
   - General services

2. **Routine Administration**
   - Standard council operations
   - Administrative tasks without transparency focus

## False Negatives (OFTEN MISSED)

1. **Councillor Entitlements Policies**
   - "No private benefit" for councillors
   - Facilities policies → SDG 16 (anti-corruption)

2. **Transparency Initiatives**
   - Public disclosure requirements
   - Open data initiatives

3. **Community Consultation**
   - Public participation in decision-making
   - Community engagement for governance

4. **Family Violence Programs**
   - Domestic violence prevention
   - Safety programs

## Validation Checklist

- [ ] Does activity relate to governance or transparency?
- [ ] Is it about anti-corruption or accountability?
- [ ] Does it promote inclusive decision-making?
- [ ] Is it about councillor conduct or ethics?

**Councillor entitlements policies → SDG 16, NOT SDG 11**

## Common Misses

The model frequently misses SDG 16 for:
- Councillor facilities policies (anti-corruption)
- Transparency policies
- Public participation programs
- Ethics and conduct frameworks

## Score Thresholds

- **STRONG (0.8+)**: Explicit governance/transparency focus
- **MODERATE (0.6-0.8)**: Governance context
- **WEAK (<0.6)**: General governance references

## Special Note

SDG 16 is **significantly under-detected** by the current model. Activities about:
- Councillor entitlements → Should be SDG 16
- "No private benefit" → Should be SDG 16
- Public transparency → Should be SDG 16
- Community engagement for governance → Should be SDG 16