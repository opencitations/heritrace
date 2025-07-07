# End User Testing Protocol

**Target**: 8-12 academic professionals working with bibliographic metadata  
**Duration**: 60 minutes maximum  
**Format**: Self-guided with screen and voice recording

## Pre-Requirements

Participants must complete:
- Pre-test questionnaire ([questionnaires/end_user_pre_test.md](questionnaires/end_user_pre_test.md))
- Basic web application experience verification

## Equipment Setup Instructions

**Required**:
- Computer with screen recording software (OBS, QuickTime, etc.)
- Microphone for voice recording
- Access to HERITRACE instance with test data
- Modern web browser

### Sample Data Provided
- ParaText dataset: 17,799 quadruples and 562 bibliographic resources
- Examples of incomplete records needing editing
- Duplicate entities for merge testing

## Testing Session Structure

### **Session Start**
```
"Start your screen and voice recording now. 

You'll be working through several metadata management tasks. Think aloud throughout - describe what you're doing, what you expect, and any questions or reactions you have.

There are no right or wrong approaches - we want to understand your natural workflow."
```

## Metadata Management Tasks (60 minutes)

### Task 1: Edit Existing Publication Record (10 minutes)
```
"Task 1: Browse the catalogue to find a Review Article entity type and modify the publication record for 'Conti Bizzarro, F. (2009). Da Esiodo a Saffo e Alceo: due contributi dell'Istituto Papirologico \"G. Vitelli\" [Review Article]. Vichiana, ser. 4, 11(1), 103-107.'

Please make these specific changes:
1. Add a new author 'Vittoria Castrillo' as the first author (before Ferruccio Conti Bizzarro)
2. Remove the keyword 'subject>ancient tradition'

Think aloud as you work through this process."
```

### Task 2: Merge Duplicate Author Entities (12 minutes)
```
"Task 2: Return to the publication from Task 1 and visit the author page for Ferruccio Conti Bizzarro. You'll notice there is a similar entity that is actually a duplication. Use the integrated functionality to merge it. Think aloud about how you approach this data cleanup process."
```

### Task 3: Restore Previous Version (8 minutes)
```
"Task 3: You realize that the modifications you made in Task 1 were incorrect - adding Vittoria Castrillo as author and removing the keyword were mistakes. Use the integrated Time Machine system to restore the previous version before those changes. Think aloud about how you approach this process and what you expect from the version control functionality."
```

### Task 4: Create New Publication Record (13 minutes)
```
"Task 4: Add this specific journal article to the repository: https://doi.org/10.1162/qss_a_00292. Include as many metadata fields as possible. You have access to the article's webpage to gather information. Think aloud as you work through this process."
```

### **Immediate Reflection (5 minutes)**
```
"Without stopping the recording, please answer these questions aloud:

1. How effectively did HERITRACE support you in these metadata management tasks?
2. What were the most useful features for your bibliographic workflow?
3. What were the main weaknesses or frustrating aspects you encountered?
4. What additional features would have made this more useful for your academic work?

Take your time with each answer - we want your complete thoughts."
```

## Post-Session Requirements

**Participants must submit**:
- Complete screen+voice recording file
- SUS questionnaire ([questionnaires/sus_questionnaire.md](questionnaires/sus_questionnaire.md))