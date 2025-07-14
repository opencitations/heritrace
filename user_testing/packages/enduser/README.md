# HERITRACE End User Testing Package

This package contains everything needed to test HERITRACE as an end user with pre-built Docker images.

## Contents

- `docker-compose.yml` - Configuration for Docker containers
- `start.sh` / `start.bat` - Scripts to start the environment
- `stop.sh` / `stop.bat` - Scripts to stop the environment
- `README.md` - These instructions

## Requirements

- Docker and Docker Compose. For installation, see the <a href="https://docs.docker.com/get-docker/" target="_blank">official documentation</a>.
- 1GB RAM minimum
- 5GB free disk space
- Modern web browser
- Computer with screen recording software (OBS, QuickTime, etc.)
- Microphone for voice recording
- Knowledge of bibliographic resource structure and metadata
- Basic web application experience
- Reviewed HERITRACE documentation: https://opencitations.github.io/heritrace/

## Quick Start

1.  Run `start.sh` (Linux/Mac) or `start.bat` (Windows). This will download the necessary Docker images and start the application.
2.  Wait for the script to confirm that the services are ready. This may take a minute or two on the first run.
3.  Open your browser at http://localhost:5000.
4.  Follow the testing protocol instructions below.
5.  When finished, run `stop.sh` or `stop.bat` to shut down all services.

---

# End User Testing Protocol

**Duration**: 60 minutes maximum  
**Format**: Self-guided with screen and voice recording

## Testing Session Structure

### **Session Start**

> "Start your screen and voice recording now. 
> 
> You'll be working through several metadata management tasks. Think aloud throughout - describe what you're doing, what you expect, and any questions or reactions you have.
> 
> There are no right or wrong approaches - we want to understand your natural workflow."

### **Warm-up Exploration (max 2 minutes)**

> "Begin by exploring this HERITRACE system. Think aloud as you navigate. Describe what you see, what you expect, and any questions that arise.
> 
> Your goal is to get familiar with the interface and understand how to browse and work with bibliographic metadata in this system."

## Metadata Management Tasks (45 minutes)

### Task 1: Edit Existing Publication Record (8 minutes)

> "Task 1: Your first task is to locate a specific bibliographic record of the type 'Journal Article': 'Carew, R. & Florkowski, W. & Smith, E. (2006). Apple Industry Performance, Intellectual Property Rights And Innovation. International Journal Of Fruit Science, 6(1), 93-116.'. We are specifying that this is the fourth article in the list because the catalog's interface deliberately lacks advanced search tools, as HERITRACE's primary focus is on editing, not searching.
> 
> Please make the following change:
> 1. Add 'Carolyn Scagel' as the first author, with 'Carolyn' as the given name and 'Scagel' as the family name.
> 
> Think aloud as you work through this process."

### Task 2: Merge Duplicate Author Entities (10 minutes)

> "Task 2: Return to the 'Journal Article' from Task 1. You'll notice that the author 'Richard Carew' is duplicated. Navigate to the author page for 'Richard Carew' and use the available tools to merge the duplicates. Think aloud about how you approach this data cleanup process."

### Task 3: Restore Previous Version (7 minutes)

> "Task 3: You realize that the modification you made in Task 1 was incorrect. Use the integrated Time Machine system to restore the record to the version before you added 'Carolyn Scagel' as an author. Think aloud about how you approach this process and what you expect from the version control functionality."

### Task 4: Create New Publication Record (20 minutes)

> "Task 4: Add this specific journal article to the repository: https://doi.org/10.1162/qss_a_00292. Include as many metadata fields as possible. You have access to the article's webpage to gather information. Think aloud as you work through this process."

### **SUS Questionnaire Completion (3 minutes)**

> "Now please complete the SUS (System Usability Scale) questionnaire provided."

### **Written Reflection (10 minutes)**

> "After completing the SUS, please provide written answers to the following questions.
> 
> 1. How effectively did HERITRACE support you in these metadata management tasks?
> 2. What were the most useful features for your bibliographic workflow?
> 3. What were the main weaknesses or frustrating aspects you encountered?
> 4. What additional features would have made this more useful for your academic work?
> 
> Take your time with each answer - we want your complete thoughts."

## Post-Session Requirements

**Participants must submit**:
- Complete screen+voice recording file
- Completed SUS questionnaire
- Written answers to reflection questions