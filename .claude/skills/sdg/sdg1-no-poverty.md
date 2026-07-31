---
name: check-sdg1-correction
description: Check SDG 1 (No Poverty) alignment quality
user-invocable: false
---

# SDG 1: No Poverty - Alignment Check

**Official Definition:** "End poverty in all its forms everywhere"

## Sample Activities (from 30 analyzed)

High-scoring examples from real council reports:
- "Council provided two free microchipping days open for all residents... ran a successful desexing initiative" (Score: 0.619)
- "Council has partnered with Victorian Government to broker funding... for 12 organisations to support social..." (Score: 0.754)
- "face of homelessness and break down stereotypes and barriers" (Score: 0.633)
- "Woollahra Connect Program supporting those who are socially isolated" (Score: 0.885)

## True Positive Activities

Activities that SHOULD align to SDG 1:

1. **Financial Assistance Programs**
   - Rate relief for pensioners/low-income households
   - Hardship grants and emergency relief
   - Debt counseling services
   - Financial support programs

2. **Homeless Support Services**
   - Homeless shelters and accommodation
   - Housing for at-risk populations
   - Homelessness prevention programs

3. **Welfare Support**
   - Food banks and emergency food
   - Community meals programs
   - Material aid (clothing, furniture)

4. **Social Safety Net**
   - Discounted services for concession card holders
   - Fee waivers for low-income residents
   - Utility assistance programs

**Keywords:** poverty, low-income, hardship, homeless, welfare, disadvantaged, vulnerable, financial assistance, rate relief, concession

## False Positives (Should NOT align to SDG 1)

1. **Generic Community Programs**
   - General community facilities without poverty focus
   - Parks and recreation (unless targeting disadvantaged)
   - General library services

2. **Economic Development Without Poverty Focus**
   - Business attraction initiatives
   - Job creation programs (these are SDG 8)
   - General infrastructure projects

3. **Social Programs Without Poverty Targeting**
   - General youth programs
   - Community events
   - Recreation facilities

**Common Misclassifications:**
- "Community support" → Often SDG 11 or SDG 17, not SDG 1
- "Services for residents" → Generic, not poverty-specific

## False Negatives (Often Missed)

1. **Indirect Poverty Alleviation**
   - Free microchipping for pets (cost barrier removal)
   - Desexing programs for low-income pet owners
   - Free medical/health services

2. **Rate Relief Programs**
   - Pensioner rate rebates
   - Hardship rate deferrals

## Validation Checklist

When checking SDG 1 alignment:

- [ ] Does activity specifically target low-income/disadvantaged populations?
- [ ] Is there explicit mention of poverty, hardship, or vulnerability?
- [ ] Does it provide direct financial or material assistance?
- [ ] Is it a homeless or housing support service?

**If only "community" or "support" mentioned without poverty focus → Likely SDG 11 or 17, not SDG 1**

## Score Thresholds

- **STRONG (0.7+)**: Explicit poverty/welfare targeting
- **MODERATE (0.5-0.7)**: Indirect poverty impact
- **WEAK (<0.5)**: Generic community activity