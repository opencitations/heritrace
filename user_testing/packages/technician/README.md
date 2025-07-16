# HERITRACE Configurator Testing Package

This package contains everything needed to test HERITRACE from a configurator's perspective with pre-built Docker images.

## Contents

- `docker-compose.yml` - Configuration for Docker containers
- `resources/` - Directory containing configuration files to be modified:
  - `display_rules.yaml` - Controls how properties are displayed in the UI
  - `shacl.ttl` - Defines validation rules for entities
- `start.sh` / `start.bat` - Scripts to start the environment
- `stop.sh` / `stop.bat` - Scripts to stop the environment
- `export-resources.sh` / `export-resources.bat` - Scripts to export modified resources
- `README.md` - These instructions

## Requirements

- Docker and Docker Compose. For installation, see the <a href="https://docs.docker.com/get-docker/" target="_blank">official documentation</a>.
- 1GB RAM minimum
- 5GB free disk space
- Modern web browser
- Computer with screen recording software (OBS, QuickTime, etc.)
- Microphone for voice recording
- Working knowledge of SHACL (Shapes Constraint Language)
- Reviewed HERITRACE documentation: https://opencitations.github.io/heritrace/

## Quick Start

1.  Run `start.sh` (Linux/Mac) or `start.bat` (Windows). This will download the necessary Docker images and start the application.
2.  Wait for the script to confirm that the services are ready. This may take a minute or two on the first run.
3.  Open your browser at http://localhost:5000.
4.  Follow the testing protocol instructions below.
5.  After completing your configuration changes, fill out the `sus_questionnaire.md` and `written_responses_template.md` files with your responses.
6.  Export the modified resources using `export-resources.sh` (Linux/Mac) or `export-resources.bat` (Windows). This will create a file named `export.zip` in the current directory that includes your completed questionnaires and responses.
7.  When finished, run `stop.sh` or `stop.bat` to shut down all services.

## Configuration Files

**Files you should modify during testing**:
- `resources/display_rules.yaml`: Controls how properties are displayed in the UI
- `resources/shacl.ttl`: Defines validation rules for entities

**Do not modify any other files** including `docker-compose.yml`, script files, or any files outside the `resources` directory.

---

# Configurator Testing Protocol

**Duration**: 60 minutes maximum
**Format**: Self-guided with screen and voice recording

## Testing Session Structure

### **Warm-up Exploration (max 2 minutes)**

> "**IMPORTANT: Start your screen recording software now and ensure it captures both your screen and microphone audio.** Make sure the recording includes your voice as you think aloud throughout the session.
> 
> You are working with a HERITRACE system that has been partially configured. Some entities already have complete SHACL schemas and display rules that allow end users to work with them effectively, while other entities are missing these configurations.
> 
> Begin by exploring this HERITRACE system using the test materials provided. Think aloud as you navigate. Describe what you see, what you expect, and any questions that arise.
> 
> Your goal is to get familiar with the interface, understand the current configuration state, and identify which entities are fully configured versus those that need additional configuration work."

### **Configuration Tasks (45 minutes total)**

**Task 1: Add Abstract Display Support (23 minutes)**

> "Your institution wants to enable users to add abstracts to journal articles using the dcterms:abstract property. Currently, users cannot add abstracts because the configuration is missing.
> 
> Currently, in the display rules for 'fabio:JournalArticle' entities, various properties are defined but the abstract property is not configured for display.
> 
> Your task is to configure the display rules for the dcterms:abstract property with the following requirements:
> 
> 1. The property display name should be "Abstract"
> 2. The property must be visible to users
> 3. The input type must be a textarea (multi-line text area)
> 4. The property should not be searchable, meaning that users should not be able to look for similar journal articles based on their abstracts.
> 
> Think aloud as you work through this. Describe your approach, what you're looking for, and any challenges you encounter. Consult the documentation to understand how to properly configure display rules.
> 
> Once completed, verify from the user interface that users can now add abstracts to journal articles where they previously could not."

**Task 2: Add SHACL Validation for Abstract (22 minutes)**  

> "Currently, there's nothing preventing users from adding multiple abstracts to a journal article. You need to modify the SHACL shape for journal articles to specify that there can be at most one abstract.
> 
> Continue thinking aloud about your process and any difficulties you encounter when working with SHACL constraints."

### **SUS Questionnaire Completion (3 minutes)**

> "Now please complete the SUS (System Usability Scale) questionnaire provided in the `sus_questionnaire.md` file included in this package."

### **Written Reflection (10 minutes)**

> "After completing the SUS, please fill out the `written_responses_template.md` file with your written answers to the reflection questions about your experience with HERITRACE's configuration features."

## Post-Session Requirements

**Participants must submit**:
- Complete screen+voice recording file
- The `export.zip` file generated by `export-resources.sh` (Linux/Mac) or `export-resources.bat` (Windows)

**Note**: The `export.zip` file automatically includes:
- Your modified configuration files (`display_rules.yaml`, `shacl.ttl`)
- Your completed SUS questionnaire (`sus_questionnaire.md`)
- Your written responses to reflection questions (`written_responses_template.md`)
