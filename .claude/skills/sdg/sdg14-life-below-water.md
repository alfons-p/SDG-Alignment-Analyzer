---
name: check-sdg14-correction
description: Check SDG 14 (Life Below Water) alignment quality
user-invocable: false
---

# SDG 14: Life Below Water - Alignment Check

**Official Definition:** "Conserve and sustainably use the oceans, seas and marine resources for sustainable development"

## Sample Activities (from 30 analyzed)

- "Bush Nippers Swimming Safety Program at Thompsons Beach Cobram" (Score: 0.873)
- "Newcastle Ocean Baths for inclusion on NSW State Heritage Register" (Score: 0.878)
- "OzFish... Local Government Procurement in circular economy initiatives" (Score: 0.997)
- "Aqua Fitness Aqua Zumba Mums and Bubs Fit 4 Life" (Score: 0.683)
- "Waves opened in September 2022... community aquatic centre" (Score: 0.668)

## True Positive Activities

1. **Marine Conservation**
   - Marine protected areas
   - Ocean biodiversity programs
   - Marine ecosystem restoration
   - Seagrass/mangrove protection

2. **Coastal Management**
   - Coastal erosion management
   - Beach conservation
   - Dune restoration
   - Coastal water quality

3. **Sustainable Fisheries**
   - Fisheries management
   - Sustainable fishing programs
   - Aquaculture

4. **Marine Pollution**
   - Ocean cleanup programs
   - Marine debris prevention
   - Beach cleaning (for marine health)

**Keywords:** marine, ocean, coastal, fisheries, sea, estuary, beach conservation, marine biodiversity, seagrass, mangrove

## False Positives (BIAS CORRECTION APPLIES)

1. **Road Names with Coastal Keywords**
   - "South Beach Road" → NOT SDG 14
   - "Coastal Highway" → NOT SDG 14
   - Infrastructure near beaches

2. **Coastal Place Names**
   - "Brunswick Heads" (location name)
   - "Byron Bay" projects
   - Activities in coastal towns

3. **Recreational Aquatic Activities**
   - Swimming pools (SDG 11)
   - Aquatic centers (SDG 11)
   - Swimming lessons (SDG 3 or 11)

4. **Infrastructure Near Water**
   - Drainage works near coast
   - Road improvements at beach locations

## False Negatives

1. **True Marine Conservation**
   - Marine habitat restoration
   - Ocean biodiversity programs
   - Coastal ecosystem management

2. **Marine Water Quality**
   - Stormwater quality near marine areas
   - Estuary health programs

## Validation Checklist

- [ ] Does activity specifically relate to marine/ocean conservation?
- [ ] Is it about marine biodiversity or ecosystems?
- [ ] Is it coastal MANAGEMENT (not just coastal location)?
- [ ] Does "beach" refer to conservation (not infrastructure)?

**Road names with "beach/coastal" → Apply SDG 14 bias correction**

## Bias Correction Rules

The SDG 14 bias correction should trigger when:
- Road patterns: "Beach Road", "Coastal Highway", "Bay Street"
- Infrastructure keywords: "improvement", "upgrade", "repair" near coastal terms
- Place names: Coastal town names used as locations (not marine activities)

True SDG 14 should boost when:
- Marine keywords: "marine conservation", "ocean health", "seagrass"
- Ecosystem focus: "marine biodiversity", "coastal ecosystem"

## Score Thresholds

- **STRONG (0.7+)**: Direct marine conservation
- **MODERATE (0.4-0.7)**: Coastal management
- **WEAK (<0.4)**: Should trigger bias correction check