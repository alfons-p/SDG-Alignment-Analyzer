---
name: check-sdg11-correction
description: Check SDG 11 (Sustainable Cities and Communities) alignment quality
user-invocable: false
---

# SDG 11: Sustainable Cities and Communities - Alignment Check

**Official Definition:** "Make cities and human settlements inclusive, safe, resilient and sustainable"

## Sample Activities (from 30 analyzed)

- "Implement Urban Stormwater Management Plan" (Score: 0.822)
- "upgraded and built new accessible recreation and cultural facilities" (Score: 1.000)
- "Council has progressively reviewed... Disability Inclusion Action Plan" (Score: 0.852)
- "In the second half of the year, we engaged with you... community responses into final reports" (Score: 0.843)
- "Develop the 2024-2033 Financial Plan" (Score: 0.719)

## True Positive Activities

1. **Urban Infrastructure**
   - Road construction and maintenance
   - Stormwater management
   - Urban drainage
   - Public facilities

2. **Housing and Planning**
   - Housing programs
   - Urban planning
   - Zoning and development

3. **Public Transport**
   - Transport systems
   - Public transit
   - Active transport (cycling, walking)

4. **Cultural Heritage (Target 11.4)**
   - Museums and archives
   - Digital preservation of collections
   - Heritage protection
   - Historical preservation

5. **Waste Management (Target 11.6)**
   - Waste collection
   - Recycling programs
   - Stormwater quality

**Keywords:** urban, city, housing, transport, waste, planning, heritage, community, infrastructure, stormwater, facilities

## False Positives (BIAS CORRECTION NEEDED)

1. **Generic "Community Development"**
   - Activities without specific urban/city context
   - General "community support" without infrastructure

2. **Governance Activities**
   - Councillor facilities (SDG 16, not SDG 11)
   - Policy development without urban focus
   - Administrative activities

3. **Regional Coordination**
   - Partnership activities (SDG 17)
   - Regional advocacy (SDG 17)

## False Negatives

1. **Cultural Heritage Preservation (SDG 11.4)**
   - Digital preservation of photos/documents
   - Archive collections
   - Museum programs
   - Historical society activities

2. **Smart City Initiatives**
   - Digital infrastructure for cities
   - Smart city technology

## Validation Checklist

- [ ] Does activity relate to urban infrastructure or planning?
- [ ] Is it about housing, transport, or waste management?
- [ ] Does it preserve cultural heritage (museums, archives)?
- [ ] Is it specifically community-focused (not just "community" keyword)?

**Governance/advocacy activities → SDG 16 or 17, NOT SDG 11**

## Score Thresholds

- **STRONG (0.7+)**: Direct urban/community infrastructure
- **MODERATE (0.5-0.7)**: Community context
- **WEAK (<0.5)**: Generic community references

## Bias Correction Notes

The model tends to overestimate SDG 11 for:
- Activities with "community" or "development" keywords
- Governance activities (should be SDG 16)
- Regional coordination (should be SDG 17)

**Apply SDG 11 bias correction** when:
- Activity is about councillor entitlements → SDG 16
- Activity is about regional advocacy → SDG 17
- Activity is generic governance → SDG 16