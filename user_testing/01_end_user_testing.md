# End User Testing Protocol

**Target**: 8-12 academic professionals working with bibliographic metadata  
**Duration**: 60 minutes maximum  
**Format**: Self-guided with screen and voice recording

## Pre-Requirements

Participants must have:
- Knowledge of bibliographic resource structure and metadata
- Basic web application experience
- Reviewed HERITRACE documentation: https://opencitations.github.io/heritrace/

## Equipment Setup Instructions

**Required**:
- Computer with screen recording software (OBS, QuickTime, etc.)
- Microphone for voice recording
- Access to HERITRACE instance with test data
- 1GB RAM minimum
- 5GB free disk space
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

### **Warm-up Exploration (max 2 minutes)**
```
"Begin by exploring this HERITRACE system. Think aloud as you navigate. Describe what you see, what you expect, and any questions that arise.

Your goal is to get familiar with the interface and understand how to browse and work with bibliographic metadata in this system."
```

## Metadata Management Tasks (45 minutes)

### Task 1: Edit Existing Publication Record (8 minutes)
```
"Task 1: Your first task is to locate a specific bibliographic record of the type 'Journal Article': 'Carew, R. & Florkowski, W. & Smith, E. (2006). Apple Industry Performance, Intellectual Property Rights And Innovation. International Journal Of Fruit Science, 6(1), 93-116.'. We are specifying that this is the fourth article in the list because the catalog's interface deliberately lacks advanced search tools, as HERITRACE's primary focus is on editing, not searching.

Please make the following change:
1. Add 'Carolyn Scagel' as the first author, with 'Carolyn' as the given name and 'Scagel' as the family name.

Think aloud as you work through this process."
```

### Task 2: Merge Duplicate Author Entities (10 minutes)
```
"Task 2: Return to the 'Journal Article' from Task 1. You'll notice that the author 'Richard Carew' is duplicated. Navigate to the author page for 'Richard Carew' and use the available tools to merge the duplicates. Think aloud about how you approach this data cleanup process."
```

### Task 3: Restore Previous Version (7 minutes)
```
"Task 3: You realize that the modification you made in Task 1 was incorrect. Use the integrated Time Machine system to restore the record to the version before you added 'Carolyn Scagel' as an author. Think aloud about how you approach this process and what you expect from the version control functionality."
```

### Task 4: Create New Publication Record (20 minutes)
```
"Task 4: Add this specific journal article to the repository: https://doi.org/10.1162/qss_a_00292. Include as many metadata fields as possible. You have access to the article's webpage to gather information. Think aloud as you work through this process."
```

### **SUS Questionnaire Completion (3 minutes)**
```
"Now please complete the SUS (System Usability Scale) questionnaire provided."
```

### **Written Reflection (10 minutes)**
```
"After completing the SUS, please provide written answers to the following questions.

1. How effectively did HERITRACE support you in these metadata management tasks?
2. What were the most useful features for your bibliographic workflow?
3. What were the main weaknesses or frustrating aspects you encountered?
4. What additional features would have made this more useful for your academic work?

Take your time with each answer - we want your complete thoughts."
```

## Post-Session Requirements

**Participants must submit**:
- Complete screen+voice recording file
- Completed SUS questionnaire
- Written answers to reflection questions