---
name: check-sdg8-correction
description: Check SDG 8 (Decent Work and Economic Growth) alignment quality
user-invocable: false
---

# SDG 8: Decent Work and Economic Growth - Alignment Check

**Official Definition:** "Promote sustained, inclusive and sustainable economic growth, full and productive employment and decent work for all"

## Sample Activities (from 30 analyzed)

- "Business and Activity Centre Development is responsible for facilitating business development" (Score: 0.865)
- "By attracting talented individuals, Council can enhance service delivery" (Score: 0.717)
- "Council's objective is to maximise its return on cash and investments" (Score: 0.494)
- "Equal Employment Opportunity (EEO)... fostering a safe, productive workplace" (Score: 0.895)
- "Apprentice/trainee programs" (Score: varies)

## True Positive Activities

1. **Economic Development**
   - Business attraction initiatives
   - Economic development programs
   - Local business support
   - Investment attraction

2. **Employment Programs**
   - Job creation programs
   - Employment services
   - Skills training for employment
   - Apprenticeship programs

3. **Business Support**
   - Small business programs
   - Business networking events
   - Local procurement policies
   - Business grants

4. **Workplace Programs**
   - Equal employment opportunity
   - Workplace safety
   - Industrial relations

**Keywords:** employment, jobs, economic, business, workforce, skills, training, apprenticeship, economic development, industry

## False Positives

1. **General Council Operations**
   - Routine governance activities
   - Internal financial management

2. **Infrastructure Without Employment Focus**
   - Road projects (unless explicitly for jobs)
   - General capital works

3. **Generic "Supporting Community"**
   - Vague community support statements

## False Negatives

1. **Local Jobs Programs**
   - Programs creating local employment
   - Skills development for jobs

2. **Business Networking**
   - Chamber of commerce support
   - Business directories

## Validation Checklist

- [ ] Does activity create or support jobs/employment?
- [ ] Is it economic development or business support?
- [ ] Does it provide skills training for work?
- [ ] Is there explicit employment or economic focus?

**General infrastructure → SDG 9 (Infrastructure), NOT SDG 8**

## Score Thresholds

- **STRONG (0.7+)**: Direct employment/business focus
- **MODERATE (0.5-0.7)**: Economic context
- **WEAK (<0.5)**: General economic references