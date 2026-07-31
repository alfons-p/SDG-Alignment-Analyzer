---
name: check-sdg2-correction
description: Check SDG 2 (Zero Hunger) alignment quality
user-invocable: false
---

# SDG 2: Zero Hunger - Alignment Check

**Official Definition:** "End hunger, achieve food security and improved nutrition and promote sustainable agriculture"

## Sample Activities (from 30 analyzed)

- "Council endorsed Food Organics and Garden Organics (FOGO) service" (Score: 0.552)
- "Inspect all medium and high-risk retail food premises annually" (Score: 0.979)
- "Create and adopt strategies... improve quality and efficiency of Coonamble Livestock Regional Saleyards" (Score: 0.910)
- "Prepare an Agricultural Land Use Strategy" (Score: 0.923)
- "Wheatbelt Agcare Community Support Services" (Score: 0.913)

## True Positive Activities

1. **Food Security Programs**
   - Food banks and food distribution
   - School breakfast programs
   - Community meals
   - Emergency food relief

2. **Agricultural Support**
   - Farmers markets support
   - Agricultural land use planning
   - Livestock saleyards
   - Rural economy programs

3. **Nutrition Programs**
   - Community nutrition education
   - Healthy eating initiatives
   - School nutrition programs

4. **Community Gardens/Food Production**
   - Community garden programs
   - Urban farming initiatives
   - Permaculture projects

**Keywords:** food, hunger, nutrition, agriculture, farming, garden, food security, meal, livestock, harvest

## False Positives

1. **General Waste Management**
   - FOGO collection (environmental focus, not food security)
   - General recycling programs

2. **General Park Maintenance**
   - Parks that aren't specifically for food production
   - General landscaping

3. **Food Safety Regulation**
   - Food premise inspections (regulatory, not food security)
   - Health compliance (SDG 3, not SDG 2)

## False Negatives

1. **FOGO Programs**
   - Organic waste collection CAN relate to SDG 2 if it supports local food production
   - Need context about composting for gardens

2. **Community Garden Programs**
   - Often missed if not explicitly called "food security"

## Validation Checklist

- [ ] Does activity relate to food production, distribution, or access?
- [ ] Is there explicit mention of agriculture, farming, or food security?
- [ ] Does it address hunger or nutrition directly?
- [ ] Is it a community garden or food growing initiative?

**Food safety inspections → SDG 3 (Health), NOT SDG 2**

## Score Thresholds

- **STRONG (0.7+)**: Explicit food/agriculture focus
- **MODERATE (0.5-0.7)**: Indirect food connection
- **WEAK (<0.5)**: Tangential food reference