---
name: check-sdg12-correction
description: Check SDG 12 (Responsible Consumption and Production) alignment quality
user-invocable: false
---

# SDG 12: Responsible Consumption and Production - Alignment Check

**Official Definition:** "Ensure sustainable consumption and production patterns"

## Sample Activities (from 30 analyzed)

- "We manage the collection and disposal of your waste while recovering recyclable materials" (Score: 0.992)
- "Council introduced a new drop-off service... waste reduction goals" (Score: 0.992)
- "no single use coffee cups... recycling" (Score: 0.991)
- "Council's Procurement Policy... sustainable procurement" (Score: 0.810)
- "self-haul voucher for disposal of bulk waste" (Score: 0.984)

## True Positive Activities

1. **Waste Management**
   - Waste collection services
   - Recycling programs
   - FOGO (Food Organics Garden Organics)
   - Waste reduction initiatives

2. **Sustainable Procurement**
   - Sustainable purchasing policies
   - Green procurement
   - Ethical sourcing

3. **Circular Economy**
   - Reuse and repair programs
   - Resource recovery
   - Product stewardship

4. **Consumption Reduction**
   - Single-use plastic reduction
   - Packaging reduction
   - Sustainable lifestyle programs

**Keywords:** recycling, waste, sustainable, circular, consumption, procurement, reuse, FOGO, compost, reduction

## False Positives

1. **General Waste Collection**
   - Routine waste collection (unless sustainability-focused)
   - Basic garbage services

2. **Environmental Programs Without Consumption Focus**
   - Biodiversity programs (SDG 15)
   - Climate programs (SDG 13)

## False Negatives

1. **Sustainable Purchasing Policies**
   - Green procurement initiatives

2. **Reuse Programs**
   - Repair cafes
   - Second-hand initiatives

## Validation Checklist

- [ ] Does activity relate to waste reduction or recycling?
- [ ] Is it about sustainable consumption?
- [ ] Does it involve sustainable procurement?
- [ ] Is there explicit sustainability focus?

**Basic waste collection → May not be SDG 12 without sustainability focus**

## Score Thresholds

- **STRONG (0.8+)**: Explicit waste reduction/recycling
- **MODERATE (0.6-0.8)**: Waste management with sustainability
- **WEAK (<0.6)**: General waste references