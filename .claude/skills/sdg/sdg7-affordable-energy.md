---
name: check-sdg7-correction
description: Check SDG 7 (Affordable and Clean Energy) alignment quality
user-invocable: false
---

# SDG 7: Affordable and Clean Energy - Alignment Check

**Official Definition:** "Ensure access to affordable, reliable, sustainable and modern energy for all"

## Sample Activities (from 30 analyzed)

- "New Tesla Superchargers in the Hope Street car park" (Score: 0.822)
- "sustainable LED floodlighting New playground" (Score: 0.751)
- "AGL is one of the country's biggest energy" (Score: 0.997)
- "NORTHERN GRAMPIANS SHIRE COUNCIL... Investing" (Score: 0.465)

## True Positive Activities

1. **Renewable Energy**
   - Solar panel installations
   - Solar rebates and incentives
   - Wind energy projects
   - Battery storage systems

2. **Energy Efficiency**
   - LED lighting programs
   - Energy efficiency upgrades
   - Green power initiatives
   - Energy audits

3. **Electric Vehicle Infrastructure**
   - EV charging stations
   - Tesla superchargers
   - Electric vehicle programs

**Keywords:** energy, solar, renewable, electricity, LED, battery, EV, charging, solar panel, efficiency, sustainable energy

## False Positives

1. **General Electrical Works**
   - Routine electrical maintenance
   - General power supply

2. **Street Lighting (Non-Efficiency)**
   - Standard street lighting replacements
   - General lighting (not efficiency-focused)

3. **Energy Company References**
   - Mentions of energy companies without action

## False Negatives

1. **Energy Efficiency Audits**
   - Building energy assessments
   - Sustainability programs

2. **Green Building Standards**
   - Energy-efficient building requirements

## Validation Checklist

- [ ] Does activity involve renewable energy generation?
- [ ] Is it about energy efficiency improvements?
- [ ] Does it install EV charging infrastructure?
- [ ] Is there explicit mention of solar, wind, or clean energy?

**General electrical works → SDG 9 (Infrastructure), NOT SDG 7**

## Score Thresholds

- **STRONG (0.7+)**: Direct renewable/efficiency project
- **MODERATE (0.5-0.7)**: Energy-related but not clean energy
- **WEAK (<0.5)**: General energy references