# Technician Testing Protocol

**Target**: 4-6 technical staff configuring semantic systems
**Duration**: 60 minutes maximum
**Format**: Self-guided with screen and voice recording

## Pre-Requirements

Participants must have:
- Working knowledge of SHACL (Shapes Constraint Language)
- Technical experience with semantic systems configuration
- Reviewed HERITRACE documentation: https://opencitations.github.io/heritrace/

## Equipment Setup Instructions

**Required**:
- Computer with screen recording software (OBS, QuickTime, etc.)
- Microphone for voice recording
- Access to test HERITRACE instance
- 1GB RAM minimum
- 5GB free disk space
- Test materials provided

## Testing Session Structure

### **Warm-up Exploration (max 2 minutes)**
```
"Start your screen and voice recording now. 

You are working with a HERITRACE system that has been partially configured. Some entities already have complete SHACL schemas and display rules that allow end users to work with them effectively, while other entities are missing these configurations.

Begin by exploring this HERITRACE system using the test materials provided. Think aloud as you navigate. Describe what you see, what you expect, and any questions that arise.

Your goal is to get familiar with the interface, understand the current configuration state, and identify which entities are fully configured versus those that need additional configuration work."
```

### **Configuration Tasks (45 minutes total)**

**Task 1: Add Abstract Display Support (23 minutes)**
```
"Your institution has provided preexisting data with a partial configuration for journal articles. The data contains abstracts associated with journal articles using the dcterms:abstract property, but these abstracts are not being displayed in the interface because the specific display rule is missing.

Currently, in the display rules for 'fabio:JournalArticle' entities, various properties are defined but the abstract property is not configured for display.

Your task is to configure the display rules for the dcterms:abstract property with the following requirements:

1. The property display name should be "Abstract"
2. The property must be visible to users
3. The input type must be a textarea (multi-line text area)
4. The property should not be searchable, meaning that users should not be able to look for similar journal articles based on their abstracts.

Think aloud as you work through this. Describe your approach, what you're looking for, and any challenges you encounter. Consult the documentation to understand how to properly configure display rules.

Once completed, verify from the user interface that the abstracts present in the data become visible to end users."
```

**Task 2: Add SHACL Validation for Abstract (22 minutes)**  
```
"Currently, there's nothing preventing users from adding multiple abstracts to a journal article. You need to modify the SHACL shape for journal articles to specify that there can be at most one abstract.

Continue thinking aloud about your process and any difficulties you encounter when working with SHACL constraints."
```

### **SUS Questionnaire Completion (3 minutes)**
```
"Now please complete the SUS (System Usability Scale) questionnaire provided."
```

### **Written Reflection (10 minutes)**
```
"After completing the SUS, please provide written answers to the following questions.

1. How effectively did HERITRACE support you in these configuration tasks?
2. What were the most useful features that helped you accomplish your work?
3. What were the main weaknesses or frustrations you encountered?
4. What additional features would have made these tasks easier?

Take your time with each answer - we want your complete thoughts."
```

## Post-Session Requirements

**Participants must submit**:
- Complete screen+voice recording file
- Modified SHACL schema files
- Modified display rules files
- Completed SUS questionnaire
- Written answers to reflection questions