---
name: check-sdg9-correction
description: Check SDG 9 (Industry, Innovation and Infrastructure) alignment quality
user-invocable: false
---

# SDG 9: Industry, Innovation and Infrastructure - Alignment Check

**Official Definition:** "Build resilient infrastructure, promote inclusive and sustainable industrialization and foster innovation"

## Sample Activities (from 30 analyzed)

- "Council officers have also partnered with Federation University to explore a Centre of Excellence" (Score: 0.691)
- "Berridale and Kalkite infrastructure studies" (Score: 0.996)
- "airport is a transformational infrastructure project" (Score: 0.723)
- "Introduced a new cloud based Human Resources platform" (Score: 0.881)
- "Recognising the need for a controlled and efficient approach to AI adoption" (Score: 0.807)

## True Positive Activities

1. **Physical Infrastructure**
   - Road construction and maintenance
   - Bridge works
   - Airport development
   - Building construction
   - Drainage infrastructure

2. **Digital Infrastructure**
   - IT system upgrades
   - Cloud platforms
   - Digital transformation
   - Technology adoption

3. **Innovation**
   - Research partnerships
   - Technology pilots
   - Innovation hubs
   - AI adoption

4. **Industrial Development**
   - Industrial zones
   - Manufacturing support
   - Economic infrastructure

**Keywords:** infrastructure, road, bridge, digital, technology, innovation, industrial, airport, IT, cloud, AI

## False Positives

1. **Routine Maintenance**
   - General repairs without innovation context
   - Routine maintenance

2. **General Council Operations**
   - Administrative activities
   - Routine service delivery

## False Negatives

1. **Technology Upgrades**
   - IT system implementations
   - Software adoption

2. **Smart City Initiatives**
   - Digital city programs
   - Technology innovation

## Validation Checklist

- [ ] Does activity involve physical or digital infrastructure?
- [ ] Is it about innovation or technology adoption?
- [ ] Does it relate to industrial development?
- [ ] Is there explicit infrastructure/innovation focus?

**Routine maintenance → May not be SDG 9 without innovation context**

## Score Thresholds

- **STRONG (0.7+)**: Direct infrastructure/innovation project
- **MODERATE (0.5-0.7)**: Infrastructure context
- **WEAK (<0.5)**: General references