---
name: check-sdg5-correction
description: Check SDG 5 (Gender Equality) alignment quality
user-invocable: false
---

# SDG 5: Gender Equality - Alignment Check

**Official Definition:** "Achieve gender equality and empower all women and girls"

## Sample Activities (from analyzed reports)

- "Women's Safety Program: domestic violence support services" (Score: 0.92)
- "Gender Equity Policy: workplace diversity and inclusion initiatives" (Score: 0.88)
- "Women in Leadership: mentoring program for female staff" (Score: 0.85)
- "Safe Spaces: women's shelter and crisis support services" (Score: 0.91)
- "Parenting Programs: childcare services and family support" (Score: 0.79)

## True Positive Activities

1. **Women's Services**
   - Women's centers and shelters
   - Domestic violence support
   - Sexual assault services
   - Women's safety programs

2. **Gender Equity Programs**
   - Gender equity policies
   - Equal opportunity initiatives
   - Diversity and inclusion programs
   - Women's representation targets

3. **Women's Health & Wellbeing**
   - Maternal health services
   - Women's health programs
   - Breastfeeding support facilities
   - Reproductive health services

4. **Women's Economic Participation**
   - Women in leadership programs
   - Women's employment initiatives
   - Entrepreneurship support for women
   - Pay equity initiatives

**Keywords:** gender equality, women's rights, gender equity, female empowerment, women's safety, domestic violence, equal opportunity, gender discrimination, women's leadership, girls' programs

## False Positives

1. **General Community Programs**
   - Community centers open to all (SDG 11)
   - General youth programs (SDG 4)
   - Health services without gender focus (SDG 3)

2. **Parenting Programs (Context-Dependent)**
   - General parenting programs (SDG 4)
   - Childcare without gender equity focus (SDG 4)

## False Negatives

1. **Implicit Gender Programs**
   - Family violence prevention (if not explicitly women-focused)
   - Flexible work arrangements (gender equity impact)

2. **Intersectional Programs**
   - Programs addressing multiple disadvantages
   - Youth programs with gender components

## Validation Checklist

- [ ] Does activity specifically address women and girls?
- [ ] Is there explicit gender equity focus?
- [ ] Does it address gender-based violence or discrimination?
- [ ] Does it promote women's participation or leadership?

**General parenting programs → SDG 4 (Education), unless explicitly gender-focused**

## Score Thresholds

- **STRONG (0.8+)**: Direct women's services, domestic violence support
- **MODERATE (0.6-0.8)**: Gender equity policies, women's leadership
- **WEAK (<0.6)**: General diversity without specific gender focus