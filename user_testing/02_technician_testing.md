# Technician Testing Protocol

## Overview

This document provides a comprehensive testing protocol for technicians responsible for configuring and maintaining HERITRACE systems. The protocol evaluates the system's installation, configuration, and maintenance procedures from a technical perspective.

## Testing Objectives

### Primary Objectives
1. **Installation Evaluation**: Assess the ease and reliability of system installation
2. **Configuration Assessment**: Evaluate the configuration process and documentation quality
3. **SHACL Schema Comprehension**: Test understanding and configuration of provided data validation schemas
4. **Integration Testing**: Test ORCID integration and external database connections
5. **Maintenance Workflows**: Assess ongoing system maintenance requirements
6. **Documentation Quality**: Evaluate technical documentation comprehensiveness

### Secondary Objectives
1. **Error Handling**: Identify common configuration errors and recovery procedures
2. **Performance Optimization**: Assess system performance tuning options
3. **Security Configuration**: Evaluate security setup and best practices
4. **Scalability Planning**: Identify potential scaling considerations

## Pre-Testing Setup

### Environment Requirements

**Testing Environment Setup:**
- Clean virtual machine or container environment
- Debian 12 or equivalent Linux distribution
- Docker and Docker Compose installed
- Basic development tools (git, curl, wget)
- At least 8GB RAM and 20GB storage available

**Documentation Provided:**
- HERITRACE README.md file
- Configuration example files
- Docker compose files
- Shell scripts for database management
- Simplified SHACL schema file (derived from production schema)
- Display rules configuration examples
- Sample valid and invalid entity data for testing

**Prerequisites:**
- Basic understanding of RDF and semantic web concepts
- Familiarity with SHACL (Shapes Constraint Language) syntax and validation principles
- Experience with SPARQL and triple stores
- Docker and containerization knowledge

**Pre-Test Questionnaire:**
Complete the [Technician Pre-Test Questionnaire](questionnaires/technician_pre_test.md) to establish baseline knowledge and experience, particularly regarding SHACL and semantic web technologies.

## Testing Sessions

### Session 1: Initial Setup and Configuration (2-3 hours)

#### Task 1.1: Environment Preparation (30 minutes)

**Objective**: Set up the basic development environment

**Instructions to Participant:**
"You've been tasked with setting up HERITRACE for your institution. Start by preparing your development environment."

**Tasks:**
1. Clone the HERITRACE repository
2. Review the README.md file
3. Identify system requirements
4. Install any missing dependencies

**Success Criteria:**
- Repository successfully cloned
- Dependencies identified and installed
- Basic understanding of system architecture

**Data to Collect:**
- Time to complete setup
- Number of documentation references
- Issues encountered and resolution methods
- Participant confidence level (1-10 scale)

#### Task 1.2: Configuration File Setup (45 minutes)

**Objective**: Create and configure the main application configuration for a provided bibliographic data model

**Instructions to Participant:**
"Configure HERITRACE to work with a provided bibliographic data model. You have been given a SHACL schema that defines the structure for academic publications, journals, and authors that your institution will be managing."

**Pre-provided Materials:**
- Simplified SHACL schema file (based on existing heritrace/resources/shacl.ttl)
- Display rules configuration example
- Sample entity data for testing

**Tasks:**
1. Copy `config.example.py` to `config.py`
2. Configure database connections
3. Set up ORCID integration parameters
4. Configure file paths and directories
5. Set security parameters
6. Verify SHACL schema is properly loaded

**Success Criteria:**
- Valid configuration file created
- All required parameters configured
- SHACL schema successfully loaded
- Configuration validates without errors

**Data to Collect:**
- Configuration time
- Number of configuration errors
- Understanding of SHACL schema structure
- Use of documentation vs. trial-and-error
- Questions and clarifications needed

#### Task 1.3: Database Setup (45 minutes)

**Objective**: Set up the required databases using provided scripts

**Instructions to Participant:**
"Set up the database infrastructure needed for HERITRACE."

**Tasks:**
1. Review database requirements
2. Execute database startup scripts
3. Verify database connectivity
4. Configure database endpoints in application

**Success Criteria:**
- Both databases (dataset and provenance) running
- Successful connection from application
- SPARQL endpoints accessible

**Data to Collect:**
- Setup time and any delays
- Script execution issues
- Network/connectivity problems
- Verification methods used

#### Task 1.4: Application Launch (30 minutes)

**Objective**: Launch the application and verify basic functionality

**Instructions to Participant:**
"Start the HERITRACE application and verify it's working correctly."

**Tasks:**
1. Launch application using Docker Compose
2. Access the web interface
3. Verify all services are running
4. Test basic navigation

**Success Criteria:**
- Application starts without errors
- Web interface accessible
- All expected services running
- Basic interface navigation works

**Data to Collect:**
- Startup time
- Error messages encountered
- Service status verification methods
- Initial interface impressions

### Session 2: Advanced Configuration and Customization (2-3 hours)

#### Task 2.1: SHACL Schema Understanding and Configuration (60 minutes)

**Objective**: Demonstrate understanding of the provided SHACL schema and configure system validation

**Instructions to Participant:**
"You have been provided with a SHACL schema that defines the bibliographic data model for your institution. Your task is to understand this schema structure and ensure the system is properly configured to validate data according to these rules."

**Pre-provided Materials:**
- Complete SHACL schema file (simplified version of the production schema)
- Example entities that should validate successfully
- Example entities with intentional validation errors

**Tasks:**
1. Analyze the SHACL schema structure and identify key entity types
2. Understand property constraints, cardinalities, and data types
3. Identify validation rules for identifiers (DOI, ORCID, ISBN, etc.)
4. Configure the system to use the provided schema
5. Test validation with provided sample data
6. Verify that invalid data is properly rejected

**Success Criteria:**
- Demonstrates understanding of SHACL node shapes and properties
- Can explain validation rules for different entity types
- System correctly validates compliant data
- System correctly rejects non-compliant data
- Can troubleshoot validation errors

**Data to Collect:**
- Time spent understanding SHACL concepts
- Accuracy of schema interpretation
- Ability to explain validation rules
- Success rate in configuring validation
- Troubleshooting effectiveness

#### Task 2.2: Display Rules Customization (60 minutes)

**Objective**: Customize the display rules for the user interface

**Instructions to Participant:**
"Customize the display rules to match your institution's cataloging workflow and terminology preferences."

**Tasks:**
1. Review display rules YAML structure
2. Modify property display names and order
3. Configure search and sorting options
4. Customize entity type presentations
5. Test changes in interface

**Success Criteria:**
- Display rules successfully modified
- Interface reflects customizations
- Search and sorting work as expected
- Changes improve workflow relevance

**Data to Collect:**
- YAML syntax learning curve
- Configuration time
- Testing thoroughness
- Customization effectiveness assessment

#### Task 2.3: ORCID Integration Setup (45 minutes)

**Objective**: Configure ORCID authentication and integration

**Instructions to Participant:**
"Set up ORCID integration to allow researchers to authenticate and link their ORCID profiles."

**Tasks:**
1. Obtain ORCID API credentials (simulated)
2. Configure ORCID settings in application
3. Set up user whitelist/authorization rules
4. Test authentication workflow
5. Verify ORCID data retrieval

**Success Criteria:**
- ORCID configuration parameters set correctly
- Authentication workflow functions
- User authorization rules applied
- ORCID profile data accessible

**Data to Collect:**
- Configuration complexity assessment
- Documentation clarity rating
- Security considerations identified
- Integration testing thoroughness

#### Task 2.4: Performance and Monitoring Setup (30 minutes)

**Objective**: Configure monitoring and performance optimization

**Instructions to Participant:**
"Set up basic monitoring and optimize the system for your expected workload."

**Tasks:**
1. Configure logging levels and output
2. Set up basic performance monitoring
3. Optimize database connection settings
4. Configure caching parameters
5. Set up backup procedures

**Success Criteria:**
- Monitoring configured and functional
- Performance parameters optimized
- Backup procedures documented
- System health verifiable

**Data to Collect:**
- Monitoring setup complexity
- Performance optimization confidence
- Backup strategy appropriateness
- Documentation quality assessment

## Troubleshooting Scenarios

### Scenario A: Database Connection Failure

**Setup**: Simulate database connectivity issues

**Task**: "The application is reporting database connection errors. Diagnose and resolve the issue."

**Expected Actions:**
1. Check database service status
2. Verify connection parameters
3. Test network connectivity
4. Review error logs
5. Implement fix and verify resolution

### Scenario B: SHACL Validation Errors

**Setup**: Provide sample data that violates SHACL constraints

**Task**: "Users are reporting validation errors when trying to create bibliographic entities. The system is rejecting valid-looking data. Investigate the SHACL constraints and determine why the validation is failing."

**Expected Actions:**
1. Examine the provided entity data that's failing validation
2. Analyze relevant SHACL node shapes and property constraints
3. Identify which specific constraints are being violated
4. Explain the validation requirements to resolve the issue
5. Test with corrected data to verify validation passes

**Assessment Criteria:**
- Demonstrates understanding of SHACL validation principles
- Can trace validation errors to specific constraint violations
- Provides clear explanation of data requirements
- Shows competence in SHACL debugging techniques

## Post-Testing Interview

### Technical Assessment Questions

1. **Overall Experience**
   - How would you rate the overall setup experience? (1-10 scale)
   - What was the most challenging aspect of the configuration?
   - What worked better than expected?

2. **Documentation Quality**
   - Was the technical documentation sufficient for your needs?
   - What information was missing or unclear?
   - How could the documentation be improved?

3. **Configuration Process**
   - Which configuration steps were most intuitive?
   - Where did you need to make assumptions or guesses?
   - How confident are you in your final configuration?

4. **SHACL Schema Understanding**
   - How comfortable are you working with the provided SHACL schema?
   - What aspects of SHACL validation were most challenging to understand?
   - How confident are you in troubleshooting SHACL validation errors?
   - What additional SHACL documentation or tools would be helpful?

5. **System Architecture**
   - How well do you understand the system architecture after setup?
   - Are there aspects of the system design that concern you?
   - How would you explain the system to a colleague?

6. **Maintenance Considerations**
   - How comfortable are you with ongoing system maintenance?
   - What maintenance tasks are you most/least confident about?
   - What additional tools or documentation would help with maintenance?

7. **Institutional Fit**
   - How well would this system fit your institution's technical infrastructure?
   - What barriers do you see to institutional adoption?
   - What would make deployment easier for institutions?
   - How realistic is the SHACL knowledge requirement for typical institutional technicians?

### Usability Assessment

**System Usability Scale (SUS)**: Complete the standard SUS questionnaire for configuration interface usability.

**Custom Technical Questions:**
1. The system configuration process is straightforward (1-7 scale)
2. The documentation provides adequate technical detail (1-7 scale)
3. Error messages are helpful for troubleshooting (1-7 scale)
4. The system architecture is appropriate for institutional use (1-7 scale)
5. I feel confident maintaining this system (1-7 scale)

## Data Collection Methods

### Quantitative Metrics

**Task Performance:**
- Task completion rates
- Time to complete each configuration task
- Number of errors encountered per task
- Documentation reference frequency
- Help-seeking behaviors

**System Metrics:**
- Configuration file validation success
- Database connection success rates
- Application startup times
- Resource usage during setup

### Qualitative Data

**Observation Notes:**
- Problem-solving approaches
- Frustration indicators
- Confidence levels during tasks
- Questions and comments during testing

**Think-Aloud Protocol:**
- Encourage verbalization of thought processes
- Record reasoning behind configuration choices
- Capture confusion or uncertainty moments
- Note workarounds or creative solutions

### Video/Screen Recording

**Technical Setup:**
- Screen recording throughout sessions
- Audio recording for think-aloud protocol
- Camera recording for participant reactions
- Backup recording methods

**Recording Focus Areas:**
- Configuration file editing
- Command-line interactions
- Error handling procedures
- Documentation usage patterns

## Success Criteria

### Completion Thresholds

**Minimum Success:**
- 70% of participants complete basic setup successfully
- Average setup time under 3 hours for experienced technicians
- 80% success rate for database configuration
- 60% success rate for advanced customization tasks

**Target Success:**
- 85% completion rate for all configuration tasks
- Average setup time under 2 hours
- 90% success rate for database and application setup
- 75% success rate for SHACL and display rules customization

**Optimal Success:**
- 95% completion rate across all tasks
- Setup time under 1.5 hours for experienced participants
- 95% success rate for standard configuration
- 85% success rate for advanced customization

### Quality Indicators

**Technical Competence:**
- Participants demonstrate understanding of system architecture
- Configuration files are correctly formatted and complete
- Troubleshooting approaches are systematic and effective
- Security considerations are identified and addressed

**Documentation Effectiveness:**
- Participants rely primarily on provided documentation
- Questions indicate documentation gaps rather than comprehension issues
- Participants can explain configured components to others
- Confidence levels remain high throughout testing

### Risk Assessment

**High-Risk Issues:**
- Fundamental architecture misunderstandings
- Security vulnerabilities in configurations
- Data loss risks during setup
- Performance issues that impact usability

**Medium-Risk Issues:**
- Complex troubleshooting procedures
- Documentation gaps for edge cases
- Integration difficulties with existing systems
- Time-intensive configuration processes

**Low-Risk Issues:**
- Minor interface usability concerns
- Preference-based configuration options
- Non-critical feature limitations
- Cosmetic documentation improvements 