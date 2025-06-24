# End User Testing Protocol

## Overview

This document provides a comprehensive testing protocol for end users of HERITRACE, focusing on graduate students, researchers, academic professionals, and information specialists who will use the system for bibliographic metadata creation, editing, and management. The protocol evaluates usability, effectiveness, and user experience for academic research workflows.

## Testing Objectives

### Primary Objectives
1. **Usability Assessment**: Evaluate ease of use for metadata creation and editing tasks
2. **Workflow Integration**: Assess how well HERITRACE fits into academic research and scholarly workflows
3. **Feature Effectiveness**: Test core functionality including entity editing, relationships management, and provenance tracking
4. **Learning Curve**: Evaluate time and effort required to become proficient with the system (particularly for users new to semantic metadata)
5. **Interface Design**: Assess visual design, navigation, and information architecture

### Secondary Objectives
1. **Error Prevention**: Identify common user errors and interface design issues
2. **Accessibility**: Evaluate compliance with accessibility standards and guidelines
3. **Performance Perception**: Assess user perception of system responsiveness
4. **Collaborative Features**: Test multi-user workflows and change tracking
5. **Data Quality**: Evaluate how the system supports high-quality metadata creation

## Pre-Testing Setup

### Environment Requirements

**Testing Environment:**
- Pre-configured HERITRACE instance with sample data
- Flexible testing setup (participant's own computer or provided workstation)
- Modern web browser (Chrome, Firefox, Safari, or Edge)
- Stable internet connection
- Audio recording capability for think-aloud protocols

**Sample Data Provided:**
- Collection of 100 sample bibliographic records for editing
- Mix of books, journal articles, conference papers, and theses
- Various completion states (complete, incomplete, with errors for correction)
- Examples of complex relationships (series, collections, authorship)
- Duplicate entities requiring merge operations
- Entities with conflicting information for conflict resolution testing

**Pre-Test Questionnaire:**
Complete the [End User Pre-Test Questionnaire](questionnaires/end_user_pre_test.md) to establish baseline experience and expectations.

## Testing Sessions

### Integration with User Scenarios

**Important Note**: The tasks described in each session below provide the methodological framework for testing. For actual testing sessions, these generic tasks should be replaced with **realistic, contextual scenarios** from [User Scenarios](04_user_scenarios.md) that match the participant's professional background and experience level.

**Scenario Selection Guidelines**:
- **Academic Librarians**: Use Academic Library Scenarios (A1-A3)
- **Archivists**: Use Archive Management Scenarios (AR1-AR2)  
- **Museum Professionals**: Use Museum Curation Scenarios (M1-M2)
- **Researchers**: Use Research Project Scenarios (R1-R2)

Each scenario provides realistic context, background materials, and success criteria that replace the generic task descriptions below while maintaining the same testing objectives and data collection methods.

### Session 1: Initial Exploration and Basic Tasks (1-2 hours, flexible timing)

#### Task 1.1: First Impressions and System Overview (20 minutes)

**Objective**: Gather initial reactions and assess intuitive understanding

**Instructions to Participant:**
"You're being introduced to HERITRACE, a new tool for managing bibliographic metadata. Take some time to explore the interface and get familiar with its layout and features."

**Tasks:**
1. Log into the system (simulated authentication)
2. Explore the main interface without specific goals
3. Try to understand what the system does
4. Identify main navigation elements and features

**Success Criteria:**
- Participant can navigate basic interface elements
- Basic understanding of system purpose achieved
- Main functional areas identified

**Data to Collect:**
- Initial reaction and comments
- Time spent on different interface areas
- Questions and confusion points
- Intuitive vs. counterintuitive elements

#### Task 1.2: Record Examination and Understanding (25 minutes)

**Objective**: Assess comprehension of metadata display and organization

**Instructions to Participant:**
"You'll be working with some bibliographic records in the system. Start by examining this sample record to understand how information is presented and organized."

**Tasks:**
1. Open a provided complex bibliographic record
2. Examine all displayed metadata fields and their structure
3. Understand relationships to other entities (authors, publications, etc.)
4. Identify how the data is organized for editing purposes

**Success Criteria:**
- Participant can interpret all major metadata fields
- Relationships between entities are understood
- Data structure comprehension for editing
- Display organization is logical to participant

**Data to Collect:**
- Comprehension of metadata fields and structure
- Questions about field meanings or relationships
- Time spent examining different sections
- Understanding of editing-relevant organization

#### Task 1.3: Basic Navigation and Interface Interaction (15 minutes)

**Objective**: Test fundamental interface usability

**Instructions to Participant:**
"Practice moving around the system. Try to visit different sections and understand how to navigate efficiently."

**Tasks:**
1. Navigate between different system sections
2. Use breadcrumb navigation and back/forward
3. Access help or documentation features
4. Test responsive design elements (if applicable)

**Success Criteria:**
- Efficient navigation between sections
- Successful use of navigation aids
- Ability to access help when needed
- Interface responds predictably to interactions

**Data to Collect:**
- Navigation efficiency and patterns
- Use of navigation aids
- Help-seeking behavior
- Interface response satisfaction

### Session 2: Metadata Creation, Editing, and Entity Management (1.5-2 hours)

#### Task 2.1: Creating a New Bibliographic Record (45 minutes)

**Objective**: Test the metadata creation workflow for new resources

**Instructions to Participant:**
"You need to create a record for a new journal article that was just published by a colleague or someone in your research field. Use the provided citation information to create a complete record."

**Provided Information:**
- Complete citation details for a fictional journal article
- Author information including ORCID IDs
- Publication details (journal, volume, pages, DOI)
- Abstract and keywords

**Tasks:**
1. Initiate new record creation process
2. Select appropriate resource type
3. Enter all provided metadata
4. Establish relationships to existing entities (authors, journal)
5. Validate and save the record

**Success Criteria:**
- Record creation workflow completed successfully
- All metadata fields populated correctly
- Appropriate resource type selected
- Relationships established where applicable
- Record validates without errors

**Data to Collect:**
- Time to complete record creation
- Number of errors or validation issues
- Use of help or guidance features
- Confidence level throughout process
- Workflow satisfaction rating

#### Task 2.2: Editing an Existing Record (30 minutes)

**Objective**: Test metadata editing and update workflows

**Instructions to Participant:**
"A record in the system has some errors and missing information. Please update and correct the record using the provided information."

**Scenario Setup:**
- Present a record with obvious errors (wrong dates, missing fields, incorrect relationships)
- Provide correct information for updates

**Tasks:**
1. Locate the record requiring updates
2. Identify errors and missing information
3. Edit metadata fields with corrections
4. Add missing information
5. Save changes and verify updates

**Success Criteria:**
- Record successfully located and opened for editing
- Errors correctly identified and fixed
- Missing information added appropriately
- Changes saved successfully
- Updated record displays correctly

**Data to Collect:**
- Time to identify and correct errors
- Editing workflow efficiency
- Use of validation features
- Change tracking awareness
- Overall editing satisfaction

#### Task 2.3: Managing Relationships and Hierarchies (30 minutes)

**Objective**: Test complex relationship management capabilities

**Instructions to Participant:**
"You need to establish relationships between several related publications: a book, its chapters, and related conference papers. Create and manage these complex relationships."

**Tasks:**
1. Identify resources that should be related
2. Establish hierarchical relationships (book/chapter)
3. Create cross-references between related works
4. Verify relationships display correctly
5. Navigate through established relationships

**Success Criteria:**
- Appropriate relationships identified and created
- Hierarchical structures established correctly
- Cross-references function properly
- Relationship navigation works intuitively
- Complex structures remain comprehensible

**Data to Collect:**
- Time to understand relationship options
- Success rate for relationship creation
- Navigation through established relationships
- Comprehension of hierarchical displays
- Confidence in relationship management

#### Task 2.4: Entity Merging and Conflict Resolution (30 minutes)

**Objective**: Test entity merging capabilities and duplicate resolution

**Instructions to Participant:**
"You've discovered that there are duplicate entities in the system representing the same author/publication. Use HERITRACE's merge functionality to consolidate these duplicates."

**Scenario Setup:**
- Present clearly duplicate entities (same author with slight name variations, same publication with different metadata)
- Include entities with conflicting information that need reconciliation

**Tasks:**
1. Identify duplicate entities that should be merged
2. Initiate the merge process between selected entities
3. Resolve conflicts between different metadata values
4. Choose or combine information from multiple sources
5. Complete the merge and verify the result

**Success Criteria:**
- Duplicate entities correctly identified
- Merge process completed successfully
- Conflicts resolved appropriately
- Merged entity contains complete and accurate information
- No data loss occurred during merge

**Data to Collect:**
- Time to understand merge workflow
- Success rate for conflict resolution
- Decision-making process for conflicting data
- Confidence in merge results
- Satisfaction with merge interface

#### Task 2.5: Quality Control and Validation (15 minutes)

**Objective**: Test data quality features and validation processes

**Instructions to Participant:**
"Review your created and edited records for quality and completeness. Use any available validation or quality control features."

**Tasks:**
1. Access quality control or validation features
2. Review records for completeness and accuracy
3. Address any validation warnings or errors
4. Understand quality indicators and recommendations
5. Finalize records for publication/sharing

**Success Criteria:**
- Quality control features successfully accessed and used
- Validation messages understood and addressed
- Record quality assessed effectively
- Quality improvements implemented
- Confidence in record quality achieved

**Data to Collect:**
- Use of validation features
- Understanding of quality indicators
- Time spent on quality control
- Satisfaction with quality tools
- Confidence in final record quality

### Session 3: Advanced Features and Collaboration (1-1.5 hours)

#### Task 3.1: Change Tracking and Version History (20 minutes)

**Objective**: Test provenance and change tracking features

**Instructions to Participant:**
"Examine the change history for records you've modified and understand who made what changes and when."

**Tasks:**
1. Access change history for modified records
2. Review provenance information
3. Compare different versions of records
4. Understand attribution and timing of changes
5. Restore a previous version if needed

**Success Criteria:**
- Change history successfully accessed and understood
- Provenance information clearly interpreted
- Version comparison features used effectively
- Change attribution clearly understood
- Version restoration completed if applicable

**Data to Collect:**
- Understanding of change tracking displays
- Time to interpret version information
- Use of comparison features
- Confidence in provenance tracking
- Perceived value of change tracking

## Post-Testing Interview

### User Experience Assessment

1. **Overall Satisfaction**
   - How would you rate your overall experience with HERITRACE? (1-10 scale)
   - What did you like most about the system?
   - What frustrated you the most?
   - How does it compare to tools you currently use?

2. **Workflow Integration**
   - How well would HERITRACE fit into your research or academic workflow?
   - What research tasks would be easier/harder with this system?
   - How could this tool support your academic or research activities?

3. **Learning and Training**
   - How long do you think it would take to become proficient with HERITRACE?
   - What training or support would you need?
   - What was most difficult to learn or understand?

4. **Feature Priorities**
   - Which features are most valuable for your work?
   - Which features seemed unnecessary or confusing?
   - What missing features would be important to add?

5. **System Performance**
   - How responsive did the system feel?
   - Were there any performance issues that affected your work?
   - How important is performance for this type of tool?

### Detailed Usability Questions

**Navigation and Interface:**
1. The system navigation is intuitive and logical (1-7 scale)
2. Information is well-organized and easy to find (1-7 scale)
3. The visual design supports efficient work (1-7 scale)
4. Error messages are helpful and actionable (1-7 scale)

**Functionality and Features:**
1. Metadata creation/editing workflows are efficient (1-7 scale)
2. Relationship management is intuitive (1-7 scale)
3. Entity merging functionality is effective (1-7 scale)
4. Quality control features are helpful (1-7 scale)
5. Change tracking provides valuable information (1-7 scale)

**Professional Workflow:**
1. This system would improve my metadata work quality (1-7 scale)
2. This system would make my work more efficient (1-7 scale)
3. I would recommend this system to colleagues (1-7 scale)
4. This system addresses real problems in my current workflow (1-7 scale)

## Data Collection Methods

### Quantitative Metrics

**Task Performance:**
- Task completion rates and success levels
- Time to complete each major task
- Number of errors or failed attempts
- Help/documentation access frequency
- Feature usage patterns and preferences

**Interaction Metrics:**
- Mouse clicks and keyboard inputs
- Page views and navigation patterns
- Search query types and refinements
- Form completion times and error rates

### Qualitative Data

**Think-Aloud Protocol:**
- Continuous verbalization of thoughts and reactions
- Problem-solving approaches and reasoning
- Emotional reactions and frustration points
- Confidence levels and uncertainty expressions

**Observational Notes:**
- Body language and non-verbal reactions
- Hesitation points and confusion indicators
- Workaround behaviors and creative solutions
- Engagement levels and attention patterns

**Interview Responses:**
- Detailed feedback on specific features
- Workflow integration insights
- Comparison with existing tools
- Suggestions for improvements

### Screen and Audio Recording

**Recording Setup:**
- Full screen recording throughout all sessions
- High-quality audio for think-aloud protocols
- Optional webcam recording for reactions
- Backup recording systems for reliability

**Analysis Focus:**
- User interface interaction patterns
- Problem-solving behaviors
- Error recovery strategies
- Feature discovery and usage

## Success Criteria

### Task Completion Metrics

**Minimum Success Thresholds:**
- 70% task completion rate across all participants (considering varying experience levels)
- 75% success rate for basic record examination and navigation
- 65% success rate for record creation and editing
- 55% success rate for entity merging and advanced features

**Target Success Goals:**
- 85% overall task completion rate
- 90% success for fundamental editing workflows
- 80% success for metadata creation/editing and merging
- 70% success for collaborative and advanced features

**Optimal Success Targets:**
- 95% completion rate for core functionality
- 85% success for all tested features
- Average task completion time within expected ranges
- High confidence levels (>7/10) for completed tasks

### User Satisfaction Metrics

**System Usability Scale (SUS):**
- Target average SUS score: 70+
- Optimal average SUS score: 80+
- Minimum acceptable individual scores: 60+

**Custom Satisfaction Measures:**
- Overall satisfaction rating: 7+ (1-10 scale)
- Workflow integration rating: 6+ (1-10 scale)
- Feature usefulness rating: 7+ (1-10 scale)
- Recommendation likelihood: 70%+ would recommend

### Quality Indicators

**Interface Usability:**
- Intuitive navigation without training
- Self-explanatory feature functionality
- Effective error prevention and recovery
- Accessible design for diverse users

**Professional Workflow Support:**
- Realistic task completion within reasonable timeframes
- Quality metadata creation capabilities
- Effective collaboration and sharing features
- Integration potential with existing systems

### Risk Assessment

**Critical Usability Issues:**
- Task completion failures due to interface problems
- Data loss or corruption during normal operations
- Accessibility barriers for users with disabilities
- Fundamental workflow mismatches

**Moderate Concerns:**
- Extended learning curves for complex features
- Performance issues affecting productivity
- Missing features important to specific user groups
- Integration challenges with existing systems

**Minor Issues:**
- Cosmetic interface improvements
- Preference-based feature modifications
- Documentation and help system enhancements
- Non-critical feature additions or refinements
