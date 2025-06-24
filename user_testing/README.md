# HERITRACE User Testing Protocol

This directory contains comprehensive user testing protocols for HERITRACE (Heritage Enhanced Repository Interface for Tracing, Research, Archival Curation, and Engagement).

## Overview

HERITRACE is a semantic editor designed for GLAM (Galleries, Libraries, Archives, and Museums) professionals to facilitate metadata enrichment and editing in a semantically robust manner. The user testing protocol is designed to evaluate the system's usability, effectiveness, and user experience across two primary user categories.

## User Categories

### 1. Technicians
Research developers, technical staff, and students with technical backgrounds responsible for:
- Initial system setup and configuration
- Database configuration and management
- SHACL schema customization
- Display rules configuration
- Integration setup (ORCID, external databases)
- System evaluation and feedback

### 2. End Users
Graduate students, researchers, and academic professionals who:
- Create and edit bibliographic metadata
- Search and browse scholarly collections
- Manage research resources and citations
- Track changes and provenance
- Collaborate on metadata curation

## Testing Framework Structure

- [Participant Recruitment](01_participant_recruitment.md)
- [Configuration Testing Protocol](02_technician_testing.md)
- [Usability Testing Protocol](03_end_user_testing.md)
- [Task-Based Scenarios](04_user_scenarios.md)
- [Data Collection Methods](05_data_collection.md)
- [Analysis Framework](06_analysis_framework.md)
- [Questionnaires and Forms](questionnaires/)
- [Test Data and Examples](test_data/)
- [Evaluation Metrics](evaluation_metrics/)

### How Testing Protocol and Scenarios Work Together

**Two-Layer Testing Approach**:

1. **Testing Protocol** (`03_end_user_testing.md`):
   - Provides the **methodological framework**
   - Defines session structure and timing
   - Establishes data collection methods
   - Sets success criteria and metrics

2. **User Scenarios** (`04_user_scenarios.md`):
   - Provides **realistic, contextual content**
   - Replaces generic tasks with professional scenarios
   - Matches participant's domain expertise
   - Includes authentic materials and constraints

**Integration Example**:
Instead of a generic task like "create a new bibliographic record," participants work with realistic scenarios like "Dr. Sarah Chen has provided 8 publications that need institutional repository records" (Scenario A1), providing authentic context, materials, and professional motivation.

## Test Objectives

### Primary Objectives
1. **Usability Assessment**: Evaluate the ease of use and learning curve for both user categories
2. **Functionality Validation**: Ensure all core features work as intended in real-world scenarios
3. **User Experience Evaluation**: Assess overall satisfaction and identify pain points
4. **Performance Analysis**: Measure task completion times and error rates
5. **Accessibility Compliance**: Verify the system meets accessibility standards

### Secondary Objectives
1. **Feature Prioritization**: Identify most and least valuable features
2. **Training Needs Assessment**: Determine documentation and training requirements
3. **Workflow Integration**: Evaluate how HERITRACE fits into existing workflows
4. **Scalability Concerns**: Identify potential issues with larger datasets or user bases

## Testing Methodology

### Mixed Methods Approach
- **Quantitative**: Task completion rates, time-to-completion, error frequencies
- **Qualitative**: Think-aloud protocols, interviews, observational notes
- **Comparative**: Before/after system implementation (where applicable)

### Testing Environment
- Controlled laboratory setting with screen recording
- Real-world pilot implementation (for selected participants)
- Remote testing capabilities for geographically distributed users

## Timeline

| Phase | Duration | Activities |
|-------|----------|------------|
| Preparation | 1-2 weeks | Recruitment, setup, materials preparation |
| Technician Testing | 2-3 weeks | Configuration and setup testing (flexible scheduling) |
| End User Testing | 2-3 weeks | Usability and functionality testing (flexible scheduling) |
| Analysis | 1-2 weeks | Data analysis and initial findings |
| Reporting | 1 week | Final report preparation and presentation |

**Total Duration**: 7-11 weeks (depending on participant availability)

## Expected Deliverables

1. **Comprehensive Test Report**: Detailed findings, recommendations, and metrics
2. **User Experience Documentation**: Guidelines for optimal user workflows
3. **Configuration Best Practices**: Technician setup recommendations
4. **Training Material Specifications**: Requirements for user documentation and training
5. **Priority Enhancement List**: Ranked list of recommended improvements

## Success Criteria

### Technician Success Metrics
- 80%+ successful completion of basic configuration tasks
- Average setup time appropriate for learning context (flexible timing)
- 75%+ confidence in system understanding and evaluation

### End User Success Metrics
- 75%+ task completion rate for core metadata operations
- Average System Usability Scale (SUS) score above 65
- 70%+ user satisfaction with interface design and workflow
- Positive feedback on research workflow integration potential