---
name: check-sdg17-correction
description: Check SDG 17 (Partnerships for the Goals) alignment quality
user-invocable: false
---

# SDG 17: Partnerships for the Goals - Alignment Check

**Official Definition:** "Strengthen the means of implementation and revitalize the Global Partnership for Sustainable Development"

## Sample Activities (from 30 analyzed)

- "A Variety of Modern Communication Mechanisms Available for the Whole Shire" (Score: 0.881)
- "Children's Centre, partially funded through NSW Government's Community Building" (Score: 0.997)
- "Long-Term Domestic Assistance... cleaning services" (Score: 0.755)
- "transparent and aligned... services are delivered responsibly" (Score: 0.886)
- "Australia Day Ambassador... delivered a heartfelt address" (Score: 0.650)

## True Positive Activities

1. **Multi-Stakeholder Partnerships**
   - Regional coordination between councils
   - Public-private partnerships
   - Joint initiatives with government
   - Collaborative programs

2. **Advocacy and Representation**
   - Regional advocacy on behalf of councils
   - Constituent council representation
   - Inter-governmental coordination

3. **Resource Mobilization**
   - Funding partnerships
   - Grant programs
   - Shared service arrangements

4. **Capacity Building**
   - Knowledge sharing programs
   - Training partnerships
   - Technology transfer

**Keywords:** partnership, collaboration, regional, coordination, stakeholder, joint, advocacy, inter-council, shared service

## False Positives (BIAS CORRECTION APPLIES)

1. **Generic "Investing in Services"**
   - "We continue to invest in services" → NOT SDG 17
   - General service delivery
   - Routine operations

2. **Generic "Community" References**
   - "Services for our people" → NOT SDG 17
   - "Supporting the community"
   - Without partnership context

3. **General Communication**
   - Communication mechanisms without partnership focus
   - General public information

## False Negatives

1. **Regional Council Collaboration**
   - Joint council initiatives
   - Shared services
   - Regional organization participation

2. **Advocacy Activities**
   - "Advocacy on behalf of constituent councils"
   - Regional representation

## Validation Checklist

- [ ] Does activity involve specific partnerships or coordination?
- [ ] Is it about multi-stakeholder collaboration?
- [ ] Does it include advocacy for constituent groups?
- [ ] Is there explicit partnership context?

**Generic governance language → NOT SDG 17**

## Bias Correction Rules

The SDG 17 bias correction should trigger when:
- Generic "investing in services" without partnership context
- "Our people" or "community" without collaboration focus
- General communication mechanisms

True SDG 17 should be recognized when:
- Regional coordination between councils
- Public-private partnerships
- Advocacy on behalf of member councils
- Joint initiatives with external organizations

## Key Distinction: SDG 17 vs SDG 11 vs SDG 16

| Activity Type | SDG 17 | SDG 11 | SDG 16 |
|---------------|--------|--------|--------|
| Regional coordination | ✓ | ✗ | ✗ |
| Community development | ✗ | ✓ | ✗ |
| Councillor conduct | ✗ | ✗ | ✓ |
| Partnership agreement | ✓ | ✗ | ✗ |
| Governance framework | ✗ | ✗ | ✓ |
| Urban planning | ✗ | ✓ | ✗ |

## Score Thresholds

- **STRONG (0.7+)**: Explicit partnership/coordination
- **MODERATE (0.5-0.7)**: Partnership context
- **WEAK (<0.5)**: Should check for false positive

## Special Note

SDG 17 is **over-triggered** by generic governance language. Apply bias correction for:
- "Investing in services" → NOT SDG 17
- "Our community" without partnership → NOT SDG 17
- General statements without collaboration → NOT SDG 17