---
name: check-sdg6-correction
description: Check SDG 6 (Clean Water and Sanitation) alignment quality
user-invocable: false
---

# SDG 6: Clean Water and Sanitation - Alignment Check

**Official Definition:** "Ensure availability and sustainable management of water and sanitation for all"

## Sample Activities (from 30 analyzed)

- "Mitchell Treatment Plant Feasibility: Completed... inlet channel mechanical screen" (Score: 0.977)
- "Respond to sewer chokes and boundary trap blockages within two hours" (Score: 0.860)
- "Swimming Pools provides premium aquatic centres" (Score: 0.814)
- "Develop a sewerage strategy that addresses the growing" (Score: 0.989)
- "Council completed four Review of Environmental Factors supporting aquatic habitat works" (Score: 0.963)

## True Positive Activities

1. **Water Supply**
   - Water treatment plants
   - Water supply infrastructure
   - Drinking water programs
   - Water quality monitoring

2. **Wastewater/Sanitation**
   - Sewerage systems
   - Wastewater treatment
   - Septic tank management
   - Sewer maintenance

3. **Stormwater Management**
   - Stormwater drainage
   - Stormwater quality programs
   - Urban drainage systems

4. **Water Quality**
   - Water quality testing
   - Catchment management
   - Riparian restoration

**Keywords:** water, wastewater, sewerage, stormwater, sanitation, drainage, treatment plant, aquatic, sewer, water quality

## False Positives

1. **Swimming Pools (Recreation)**
   - Swimming pools for recreation (SDG 11)
   - Aquatic centers (unless water quality focused)

2. **General Drainage**
   - Road drainage (SDG 9 infrastructure)
   - General stormwater (unless quality-focused)

## False Negatives

1. **Water Efficiency Programs**
   - Rainwater tank incentives
   - Water recycling programs

2. **Riparian Works**
   - Waterway restoration
   - Creek rehabilitation

## Validation Checklist

- [ ] Does activity relate to water supply or quality?
- [ ] Is it wastewater or sewerage management?
- [ ] Does it address stormwater quality (not just drainage)?
- [ ] Is it about water treatment or purification?

**Recreational swimming pools → SDG 11 (Communities), NOT SDG 6**

## Score Thresholds

- **STRONG (0.8+)**: Direct water/wastewater infrastructure
- **MODERATE (0.6-0.8)**: Stormwater or water quality
- **WEAK (<0.6)**: General water references