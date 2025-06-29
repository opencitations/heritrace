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
- 50 sample bibliographic records (books, articles, papers)
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

### Task 1: Create New Publication Record (15 minutes)
```
"Task 1: Add a new journal article to the repository. Think aloud as you work through this process."
```

**Scenario**: Add a new journal article to the repository.

### Task 2: Add Missing Information (10 minutes)
```
"Task 2: Add additional information to the article you just created. Continue thinking aloud about your process."
```

**Scenario**: Add additional metadata to the publication created in Task 1.

### Task 3: Correct Publication Error (12 minutes)
```
"Task 3: Make corrections to the publication record. Describe your approach and any challenges you encounter."
```

**Scenario**: A researcher reported multiple errors in Task 1's record that need correction.

### Task 4: Identify and Merge Duplicate Author (15 minutes)
```
"Task 4: Handle duplicate author entities. Think aloud about how you approach this type of data cleanup."
```

**Scenario**: Discover that author exists as a separate author entity and merge with the existing author entity.

### Task 5: Restore Previous Version (8 minutes)
```
"Task 5: Use version control to restore previous state. Describe what you expect and how you navigate this process."
```

**Scenario**: Realize that some changes made in Task 3 were incorrect and need to restore the publication to its state after Task 2.

### **Immediate Reflection (15 minutes)**
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

## Data Analysis Approach

**Grounded Theory Analysis** of recordings:
- **Open coding**: Extract user mental models, expectations, frustrations from natural verbalizations
- **Axial coding**: Connect themes around metadata workflow integration, system comprehension, task effectiveness
- **Selective coding**: Develop theory about end user adoption factors and barriers

**Quantitative measures**:
- Task completion rates and timing
- Error frequency and recovery patterns
- Feature usage and discovery patterns
- SUS usability scores

**Integration**: Combine qualitative insights about user mental models with quantitative task performance to understand both user behavior and underlying motivations.