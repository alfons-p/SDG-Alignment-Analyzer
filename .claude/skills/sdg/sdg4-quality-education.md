---
name: check-sdg4-correction
description: Check SDG 4 (Quality Education) alignment quality
user-invocable: false
---

# SDG 4: Quality Education - Alignment Check

**Official Definition:** "Ensure inclusive and equitable quality education and promote lifelong learning opportunities for all"

## Sample Activities (from 30 analyzed)

- "Care Sector Bootcamp delivered to 20 students from local high schools" (Score: 0.994)
- "Staff engage in a wide range of learning and development programs" (Score: 0.690)
- "Belong Workshops to local high school support units" (Score: 0.917)
- "In partnership with the Food Embassy as our key educational provider" (Score: 0.738)
- "Children, Youth and Family Strategic Plan" (Score: 0.948)

## True Positive Activities

1. **Library Services**
   - Public library programs
   - Digital literacy training
   - Community education classes

2. **Youth Education**
   - School support programs
   - Tutoring services
   - Vocational training
   - Career workshops

3. **Early Childhood**
   - Childcare services
   - Early learning programs
   - Preschool programs

4. **Scholarships & Training**
   - Scholarship programs
   - Training and skills development
   - Professional development (if public-facing)

**Keywords:** education, training, library, learning, school, scholarship, childcare, youth, workshop, course

## False Positives

1. **Internal Staff Training**
   - Employee training programs (unless public-facing)
   - Professional development for council staff

2. **General Community Facilities**
   - Community halls (no education focus)
   - Recreation centers

3. **General Youth Programs**
   - Youth activities without education component
   - Sports programs

## False Negatives

1. **Digital Literacy Programs**
   - Often overlooked
   - Computer training classes

2. **Community Education Classes**
   - Adult learning programs
   - Skills workshops

## Validation Checklist

- [ ] Does activity provide educational services or programs?
- [ ] Is it public-facing (not internal staff training)?
- [ ] Does it support learning and skills development?
- [ ] Is it library, childcare, or education-related?

**Internal staff training → Not SDG 4 (internal operations)**

## Score Thresholds

- **STRONG (0.8+)**: Direct educational programs
- **MODERATE (0.6-0.8)**: Library or training programs
- **WEAK (<0.6)**: General learning references