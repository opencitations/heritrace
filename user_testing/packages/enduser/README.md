# HERITRACE End User Testing Package

This package contains everything needed to test HERITRACE as an end user.

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

**IMPORTANT**: The system is pre-configured and ready to use. During testing, you will modify data through the web interface. Only use the provided scripts to start, stop, and export data. Do not modify configuration files directly.

1.  Run `start.sh` (Linux/Mac) or `start.bat` (Windows). This will download the necessary Docker images and start the application.
2.  Wait for the script to confirm that the services are ready. This may take a minute or two on the first run.
3.  Open your browser at http://localhost:5000.
4.  Follow the testing protocol instructions below.
5.  After completing your testing, fill out the `sus_questionnaire.md` and `written_responses_template.md` files with your responses.
6.  Export the database data using `export-data.sh` (Linux/Mac) or `export-data.bat` (Windows). This will create a file named `export.zip` in the current directory that includes your completed questionnaires and responses.
7.  When finished, run `stop.sh` or `stop.bat` to shut down all services.

---

# End User Testing Protocol

**Duration**: 60 minutes maximum  
**Format**: Self-guided with screen and voice recording

## Testing Session Structure

### **Session Start**

> "**IMPORTANT: Start your screen recording software now and ensure it captures both your screen and microphone audio.** Make sure the recording includes your voice as you think aloud throughout the session.
> 
> You'll be working through several metadata management tasks. Think aloud throughout. Describe what you're doing, what you expect, and any questions or reactions you have.
> 
> There are no right or wrong approaches. We want to understand your natural workflow."

### **Warm-up Exploration (max 2 minutes)**

> "Begin by exploring this HERITRACE system. Think aloud as you navigate. Describe what you see, what you expect, and any questions that arise.
> 
> Your goal is to get familiar with the interface and understand how to browse and work with bibliographic metadata in this system."

## Metadata Management Tasks (45 minutes)

### Task 1: Edit Existing Publication Record (8 minutes)

> "Task 1: Your first task is to edit a specific bibliographic record for a Journal Article. Look for the record that appears as 'Carew, R. & Florkowski, W. & Smith, E. (2006). Apple Industry Performance, Intellectual Property Rights And Innovation. International Journal Of Fruit Science, 6(1), 93-116.' in the interface. This should be the fourth item in the Catalogue list. We're providing the exact position since browsing functionality is not part of this usability test. HERITRACE is focused on metadata editing, not on browsing.
> 
> Please make the following change:
> 1. Add 'Carolyn Scagel' as the first author, specifying that this is the author with ORCID identifier 0000-0002-4269-6240, with 'Carolyn' as the given name and 'Scagel' as the family name.
>
> Think aloud as you work through this process."

### Task 2: Merge Duplicate Author Entities (10 minutes)

> "Task 2: Return to the 'Journal Article' from Task 1. Navigate to the author page for 'Richard Carew'. Your task is to merge any duplicate author entities you find. Think aloud about how you approach this data cleanup process."

### Task 3: Restore Previous Version (7 minutes)

> "Task 3: You realize that the modification you made in Task 1 was incorrect. Use the integrated Time Machine system to restore the record to the version before you added 'Carolyn Scagel' as an author. Think aloud about how you approach this process and what you expect from the version control functionality."

### Task 4: Create New Publication Record (20 minutes)

> "Task 4: Add this specific journal article to the repository: https://doi.org/10.1162/qss_a_00292. You must include the following metadata fields:
> 
> - **DOI**: The DOI identifier
> - **Title**: Complete article title
> - **Authors**: All authors in the correct order, with given name and family name separated for each author
> - **ORCID identifiers**: Each author must have their ORCID identifier
> - **Publisher**: Article publisher
> - **Pages**: Page numbers (start and end)
> - **Date**: Publication date
> - **Issue**: Issue number
> - **Volume**: Volume number
> - **Journal**: Journal name
> - **ISSN**: Journal ISSN identifier
> 
> You have access to the article's webpage to gather this information. Think aloud as you work through this process."

### **SUS Questionnaire Completion (3 minutes)**

> "Now please complete the SUS (System Usability Scale) questionnaire provided in the `sus_questionnaire.md` file included in this package."

### **Written Reflection (10 minutes)**

> "After completing the SUS, please fill out the `written_responses_template.md` file with your written answers to the reflection questions about your experience with HERITRACE's metadata management features."

## Post-Session Requirements

**Participants must submit**:
- Complete screen+voice recording file
- The `export.zip` file generated by `export-data.sh` (Linux/Mac) or `export-data.bat` (Windows)

**Note**: The `export.zip` file automatically includes:
- Your database modifications and testing data
- Your completed SUS questionnaire (`sus_questionnaire.md`)
- Your written responses to reflection questions (`written_responses_template.md`)