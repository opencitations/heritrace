# Technician Testing Protocol

**Target**: 4-6 technical staff configuring semantic systems
**Duration**: 60 minutes maximum
**Format**: Self-guided with screen and voice recording

## Pre-Requirements

Participants must complete:
- Pre-test questionnaire ([questionnaires/technician_pre_test.md](questionnaires/technician_pre_test.md)) 
- Technical requirements verification
- SHACL knowledge assessment (minimum level 4/7)

## Equipment Setup Instructions

**Required**:
- Computer with screen recording software (OBS, QuickTime, etc.)
- Microphone for voice recording
- Access to test HERITRACE instance
- Test materials provided

## Testing Session Structure

### **Warm-up Exploration (max 10 minutes)**
```
"Start your screen and voice recording now. 

Begin by exploring this HERITRACE system using the test materials provided. Think aloud as you navigate - describe what you see, what you expect, and any questions that arise.

Your goal is to get familiar with the interface and understand the current configuration."
```

### **Configuration Tasks (35 minutes total)**

**Task 1: Add Abstract Support (15 minutes)**
```
"Your institution needs to add abstract support to journal articles. 

Think aloud as you work through this. Describe your approach, what you're looking for, and any challenges you encounter.

Add the dcterms:abstract property with appropriate validation rules."
```

**Task 2: Add Keywords Support (10 minutes)**  
```
"Now add support for multiple keywords per article using prism:keyword.

Continue thinking aloud about your process and any difficulties."
```

**Task 3: Configure Display Rules (10 minutes)**
```
"Configure the display rules so that abstracts and keywords appear properly in the interface.

Describe what you expect to happen and whether the results match your expectations."
```

### **Immediate Reflection (10 minutes)**
```
"Without stopping the recording, please answer these questions aloud:

1. How effectively did HERITRACE support you in these configuration tasks?
2. What were the most useful features that helped you accomplish your work?
3. What were the main weaknesses or frustrations you encountered?
4. What additional features would have made these tasks easier?

Take your time with each answer - we want your complete thoughts."
```

### **Final Wrap-up (5 minutes)**
```
"Final thoughts for your institution:
- Would you recommend HERITRACE for bibliographic metadata management?
- What would need to change for real-world deployment?
- Any other observations about the configuration process?"
```

## Post-Session Requirements

**Participants must submit**:
- Complete screen+voice recording file
- Modified SHACL schema files
- Modified display rules files
- SUS questionnaire (sus_questionnaire.md)

## Data Analysis Approach

**Grounded Theory Analysis** of recordings:
- **Open coding**: Extract concepts, frustrations, successes from verbalizations
- **Axial coding**: Connect emerging themes around usability, workflow integration, technical barriers
- **Selective coding**: Develop theory about technician adoption factors

**Quantitative measures**:
- Task completion rates
- Time to completion  
- Error frequency
- SUS usability scores

**Integration**: Combine qualitative insights with quantitative metrics to understand both what happens and why it happens from the technician perspective.

## Success Criteria

**Technical completion**: Participant successfully adds abstract and keyword support with working display rules

**Usability threshold**: Average SUS score ≥ 65 for acceptable usability

**Qualitative insights**: Rich verbalization data capturing decision-making processes, expectations, and pain points for grounded theory analysis