# Technician Testing Protocol

## Overview

This protocol evaluates HERITRACE's installation, configuration, and maintenance procedures for technicians responsible for system setup.

## Objectives

**Primary**: Assess installation/configuration ease, SHACL schema comprehension, ORCID integration, maintenance requirements, documentation quality

**Secondary**: Identify configuration errors, security configuration, scaling considerations

## Pre-Testing Setup

### Environment Requirements
- Clean virtual machine or container environment
- Debian 12 or equivalent Linux distribution
- Docker and Docker Compose installed
- Basic development tools (git, curl, wget)
- 8GB RAM and 20GB storage minimum

### Materials Provided
- HERITRACE README.md and configuration files
- Docker compose files and database scripts  
- Simplified SHACL schema file (production-derived)
- Display rules configuration examples
- Sample valid/invalid entity data for testing

### Prerequisites (Mandatory)
- **RDF and semantic web concepts proficiency**
- **SHACL (Shapes Constraint Language) working knowledge**
- **SPARQL and triple stores experience**
- Docker and containerization knowledge

## Testing Sessions

### Session 1: Setup and Configuration (2-3 hours)

#### Task 1.1: Environment Preparation (30 minutes)
1. Clone HERITRACE repository
2. Review README.md file  
3. Identify system requirements
4. Install missing dependencies

#### Task 1.2: Configuration Setup (45 minutes)
**Pre-provided**: Simplified SHACL schema, display rules, sample data
1. Copy and configure `config.py` from example
2. Configure database connections
3. Set up ORCID integration parameters
4. Configure file paths and security parameters
5. Verify SHACL schema loading

#### Task 1.3: Database Setup (45 minutes)
1. Review database requirements
2. Execute database startup scripts
3. Verify database connectivity
4. Configure application endpoints

#### Task 1.4: Application Launch (30 minutes)
1. Launch application using Docker Compose
2. Access web interface
3. Verify all services running
4. Test basic navigation

### Session 2: Advanced Configuration (2-2.5 hours)

#### Task 2.1: SHACL Schema Configuration (60 minutes)
**Materials**: Complete SHACL schema, example entities (valid/invalid)
1. Analyze SHACL schema structure and entity types
2. Understand property constraints and validation rules
3. Configure system to use provided schema
4. Test validation with sample data
5. Verify error rejection for invalid data

#### Task 2.2: Display Rules Customization (60 minutes)
1. Review display rules YAML structure
2. Modify property display names and order
3. Configure search and sorting options
4. Customize entity type presentations
5. Test interface changes

#### Task 2.3: ORCID Integration (45 minutes)
1. Obtain ORCID API credentials (simulated)
2. Configure ORCID application settings
3. Set up user authorization rules
4. Test authentication workflow
5. Verify ORCID data retrieval



## Troubleshooting Scenarios

### Scenario A: Database Connection Failure
**Task**: Diagnose and resolve database connection errors
**Expected Actions**: Check service status, verify parameters, test connectivity, review logs, implement fix

### Scenario B: SHACL Validation Errors
**Task**: Investigate validation failures and explain requirements
**Expected Actions**: Examine failing data, analyze SHACL constraints, identify violations, explain requirements, test corrections

## Post-Testing Interview

### Assessment Questions
1. **Overall Experience**: Setup experience rating, most challenging aspects
2. **Documentation Quality**: Sufficiency, missing information, improvement suggestions
3. **Configuration Process**: Most intuitive steps, assumptions needed, confidence level
4. **SHACL Understanding**: Comfort level, challenging aspects, confidence in troubleshooting
5. **System Architecture**: Understanding level, design concerns
6. **Maintenance**: Confidence level, concerning tasks
7. **Institutional Fit**: Infrastructure compatibility, adoption barriers

### Usability Assessment
- **System Usability Scale (SUS)**: [Standard questionnaire](../questionnaires/sus_questionnaire.md)
- **Custom Questions** (1-7 scale): Configuration process straightforward, Documentation adequate, Error messages helpful, System architecture appropriate, Confident in maintenance

## Data Collection

### Quantitative Metrics
- Task completion rates and timing
- Error frequency per task
- Documentation reference frequency
- Configuration validation success
- Database connection success rates


### Qualitative Data
- Problem-solving approaches
- Frustration/confidence indicators
- Think-aloud protocol insights
- Questions and comments
- Workarounds and solutions

### Recording
- Screen recording throughout sessions
- Audio recording for think-aloud protocol
- Focus on configuration editing, command-line interactions, error handling

## Success Criteria

### Completion Thresholds
- **Minimum**: 70% basic setup completion, <3 hours average setup, 80% database success, 60% advanced customization
- **Target**: 85% all tasks completion, <2 hours average setup, 90% database/application setup, 75% SHACL/display customization
- **Optimal**: 95% all tasks completion, <1.5 hours setup, 95% standard configuration, 85% advanced customization

### Quality Indicators
- System architecture understanding demonstration
- Correct and complete configuration files
- Systematic troubleshooting approaches
- Security considerations identification
- Primary reliance on provided documentation
- High confidence levels throughout testing 