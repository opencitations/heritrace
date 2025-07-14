# HERITRACE End User Testing Package

This package contains everything needed to test HERITRACE as an end user with pre-built Docker images.

## Contents

- `docker-compose.yml` - Configuration for Docker containers
- `start.sh` / `start.bat` - Scripts to start the environment
- `stop.sh` / `stop.bat` - Scripts to stop the environment
- `README.md` - These instructions

## Requirements

- Docker and Docker Compose. For installation, see the <a href="https://docs.docker.com/get-docker/" target="_blank">official documentation</a>.
- 4GB RAM minimum
- 10GB free disk space
- Modern web browser
- Computer with screen recording software (OBS, QuickTime, etc.)
- Microphone for voice recording
- Knowledge of bibliographic resource structure and metadata
- Basic web application experience
- Reviewed HERITRACE documentation: https://opencitations.github.io/heritrace/

## Quick Start

1.  Run `start.sh` (Linux/Mac) or `start.bat` (Windows). This will download the necessary Docker images and start the application.
2.  Wait for the script to confirm that the services are ready. This may take a minute or two on the first run.
3.  Open your browser at https://localhost:5000.
4.  You may need to accept a self-signed certificate warning in your browser. This is expected and safe for this testing environment.
5.  Follow the testing protocol instructions below.
6.  When finished, run `stop.sh` or `stop.bat` to shut down all services.

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

> "Task 1: Browse the catalogue to find a Review Article entity type and modify the publication record for 'Conti Bizzarro, F. (2009). Da Esiodo a Saffo e Alceo: due contributi dell'Istituto Papirologico \"G. Vitelli\" [Review Article]. Vichiana, ser. 4, 11(1), 103-107.'
> 
> Please make these specific changes:
> 1. Add a new author 'Vittoria Castrillo' as the first author (before Ferruccio Conti Bizzarro)
> 2. Remove the keyword 'subject>ancient tradition'
> 
> Think aloud as you work through this process."

### Task 2: Merge Duplicate Author Entities (10 minutes)

> "Task 2: Return to the publication from Task 1 and visit the author page for Ferruccio Conti Bizzarro. You'll notice there is a similar entity that is actually a duplication. Use the integrated functionality to merge it. Think aloud about how you approach this data cleanup process."

### Task 3: Restore Previous Version (7 minutes)

> "Task 3: You realize that the modifications you made in Task 1 were incorrect - adding Vittoria Castrillo as author and removing the keyword were mistakes. Use the integrated Time Machine system to restore the previous version before those changes. Think aloud about how you approach this process and what you expect from the version control functionality."

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
- Written answers to reflection questions
