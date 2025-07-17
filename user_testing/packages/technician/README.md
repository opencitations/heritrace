# HERITRACE Configurator Testing Package

This package contains everything needed to test HERITRACE configuration features using pre-built Docker images.

## Contents

- `docker-compose.yml` - Docker container configuration
- `resources/` - Configuration files to modify:
  - `display_rules.yaml` - Controls property display in UI
  - `shacl.ttl` - Defines entity validation rules
- `start.sh` / `start.bat` - Start environment
- `stop.sh` / `stop.bat` - Stop environment
- `export-resources.sh` / `export-resources.bat` - Export modified resources
- `sus_questionnaire.md` - SUS (System Usability Scale) questionnaire
- `written_responses_template.md` - Written reflection template
- `README.md` - These instructions


## Requirements

- Docker and Docker Compose. For installation, see the <a href="https://docs.docker.com/get-docker/" target="_blank">official documentation</a>.
- 1GB RAM minimum
- 5GB free disk space
- Modern web browser
- Screen recording software (OBS, QuickTime, etc.)
- Microphone for voice recording
- Working knowledge of SHACL
- Reviewed HERITRACE documentation: https://opencitations.github.io/heritrace/

## Quick Start

1. Run `start.sh` (Linux/Mac) or `start.bat` (Windows) to download images and start the application
2. Wait for the script to confirm services are ready (may take 1-2 minutes on first run)
3. Open your browser at http://localhost:5000
4. Follow the testing protocol below
5. Complete the `sus_questionnaire.md` and `written_responses_template.md` files
6. Export modified resources using `export-resources.sh` (Linux/Mac) or `export-resources.bat` (Windows) to create `export.zip`
7. Run `stop.sh` or `stop.bat` to shut down services

## Configuration Files

**Modify during testing**:
- `resources/display_rules.yaml`: Controls property display in UI
- `resources/shacl.ttl`: Defines entity validation rules

**Do not modify**: `docker-compose.yml`, script files, or any configuration files outside the `resources` directory.

---

# Configurator Testing Protocol

**Duration**: 60 minutes maximum
**Format**: Self-guided with screen and voice recording

## Testing Session Structure

### **Warm-up Exploration (2 minutes)**

> "**IMPORTANT: Start your screen recording software now and ensure it captures both screen and microphone audio.** Think aloud throughout the session.
> 
> You are working with a partially configured HERITRACE system. Some entities have complete SHACL schemas and display rules, while others are missing these configurations.
> 
> Explore the system and think aloud as you navigate. Describe what you see, what you expect, and any questions that arise.
> 
> Your goal is to understand the interface, identify the current configuration state, and distinguish between fully configured entities and those needing additional work."

### **Configuration Tasks (45 minutes total)**

**Task 1: Add SHACL Validation for Abstract (22 minutes)**  

> "Your institution wants to enable users to add abstracts to journal articles using the `dcterms:abstract` property. To do this, you must first extend the SHACL shape for `fabio:JournalArticle` to include the abstract property.
>
> As part of this configuration, you also need to ensure that users can add at most one abstract per journal article.
> 
> Your task is to modify the SHACL shape to:
> 1. Include the `dcterms:abstract` property for `fabio:JournalArticle`.
 > 2. Add a constraint to allow a maximum of one abstract and a minimum of zero (i.e., the abstract is optional).
>
> Continue thinking aloud about your process and any difficulties you encounter when working with SHACL constraints."

> **Note on Hot-Reloading**: After modifying configuration files, manually reload the browser page to see UI changes. The backend detects changes automatically, but the frontend requires a refresh.
>
> **Note on Debugging**: If the application breaks after modifying SHACL files, run `docker logs heritrace-app` to see detailed error messages.

**Task 2: Add Abstract Display Support (23 minutes)**

> "After Task 1, you can add abstracts to journal articles. However, the default text input is not ideal for long-form text. Without specific display rules, the user experience is suboptimal.
> 
> Configure display rules for the dcterms:abstract property with these requirements:
> 
> 1. Property display name: "Abstract"
> 2. Input type: appropriate for long-form text
> 3. Property should appear under the title in the display order
> 
> Think aloud as you work. Describe your approach, what you're looking for, and any challenges. Consult the documentation to understand display rule configuration.
> 
> Once completed, verify in the UI that the 'Abstract' input has changed from a simple text field to a multi-line textarea."

### **SUS Questionnaire Completion (3 minutes)**

> "Now please complete the SUS (System Usability Scale) questionnaire provided in the `sus_questionnaire.md` file included in this package."

### **Written Reflection (10 minutes)**

> "After completing the SUS, please fill out the `written_responses_template.md` file with your written answers to the reflection questions about your experience with HERITRACE's configuration features."

## Post-Session Requirements

**Participants must submit**:
- Complete screen+voice recording file
- The `export.zip` file generated by `export-resources.sh` (Linux/Mac) or `export-resources.bat` (Windows)

**Note**: The `export.zip` file includes:
- Modified configuration files (`display_rules.yaml`, `shacl.ttl`)
- Completed SUS questionnaire (`sus_questionnaire.md`)
- Written responses (`written_responses_template.md`)
