---
name: check-sdg15-correction
description: Check SDG 15 (Life on Land) alignment quality
user-invocable: false
---

# SDG 15: Life on Land - Alignment Check

**Official Definition:** "Protect, restore and promote sustainable use of terrestrial ecosystems, sustainably manage forests, combat desertification, and halt and reverse land degradation and halt biodiversity loss"

## Sample Activities (from 30 analyzed)

- "Biodiversity Conservation through compliance" (Score: 0.983)
- "Management of Private Watercourses and Creeklines project" (Score: 0.997)
- "Biodiversity Strategy Development" (Score: 0.984)
- "Animal rehoming facilities" (Score: 0.776)
- "Native tree programs" (Score: varies)

## True Positive Activities

1. **Biodiversity Conservation**
   - Biodiversity programs
   - Native vegetation protection
   - Wildlife corridors
   - Habitat restoration

2. **Land Management**
   - Weed control
   - Pest management
   - Land restoration
   - Bush regeneration

3. **Forest Management**
   - Tree planting programs
   - Forest conservation
   - Sustainable forestry

4. **Ecosystem Protection**
   - Wetland conservation
   - Riparian restoration
   - Creek rehabilitation

**Keywords:** biodiversity, conservation, forest, native, ecosystem, habitat, wildlife, land, bush, vegetation, tree, weed

## False Positives (NEEDS BIAS CORRECTION)

1. **Cultural Heritage Collections**
   - Digital preservation of photos → NOT SDG 15 (SDG 11.4)
   - Museum archives → NOT SDG 15 (SDG 11.4)
   - Historical collections → NOT SDG 15 (SDG 11.4)

2. **Collections in General**
   - Library collections
   - Photo collections
   - Archive preservation

3. **Animal Shelters (Debated)**
   - Pet shelters → May be SDG 11 (community facilities)
   - Not specifically biodiversity conservation

## False Negatives

1. **Green Corridors**
   - Wildlife corridors
   - Habitat connections

2. **Native Tree Programs**
   - Indigenous planting
   - Revegetation

## Validation Checklist

- [ ] Does activity relate to terrestrial ecosystems or biodiversity?
- [ ] Is it about forests, native vegetation, or wildlife?
- [ ] Does it address land degradation or restoration?
- [ ] Is "preserve" about nature (not cultural heritage)?

**Cultural heritage preservation → SDG 11.4, NOT SDG 15**

## Key Distinction: SDG 11.4 vs SDG 15

| Context | SDG 11.4 (Cultural Heritage) | SDG 15 (Life on Land) |
|---------|------------------------------|----------------------|
| Digital preservation | ✓ | ✗ |
| Museum/archives | ✓ | ✗ |
| Historical photos | ✓ | ✗ |
| Native vegetation | ✗ | ✓ |
| Wildlife habitat | ✗ | ✓ |
| Biodiversity | ✗ | ✓ |
| Forest management | ✗ | ✓ |

## Score Thresholds

- **STRONG (0.8+)**: Explicit biodiversity/ecosystem focus
- **MODERATE (0.5-0.8)**: Land management context
- **WEAK (<0.5)**: Should check for false positive