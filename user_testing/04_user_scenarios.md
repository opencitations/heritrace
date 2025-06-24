# User Scenarios for HERITRACE Testing

## Overview

This document provides realistic scenarios for testing HERITRACE with end users, focusing on bibliographic metadata management tasks that academic professionals encounter in their work.

## Integration with Testing Protocol

These scenarios work with the [End User Testing Protocol](03_end_user_testing.md) by providing realistic context and materials:

- **Session 1**: Use simplified scenario versions for first impressions
- **Session 2**: Use complete scenarios matching participant experience level  
- **Session 3**: Use complex scenarios requiring advanced workflows

### Scenario Selection Guidelines
- **Novice Users**: Simpler scenarios (B1, B3) with complete information
- **Intermediate Users**: Standard scenarios (B2, B4, B5) with typical complexity
- **Advanced Users**: Complex scenarios (B6) with collaborative features

## Bibliographic Scenarios

### Scenario B1: New Faculty Publication Processing
**Role**: Subject Librarian or Research Support Staff  
**Complexity**: Intermediate (45-60 minutes)

**Context**: Dr. Sarah Chen, new Environmental Science faculty, provided a list of recent publications for the institutional repository.

**Materials Provided**:
- CV with 8 recent publications (articles, papers, book chapter)
- ORCID ID: 0000-0002-1825-0097
- Complete citation information
- 3 publications have DOIs, 2 missing publication dates

**Tasks**:
1. Create bibliographic records for all 8 publications
2. Establish Dr. Chen as author entity with ORCID linkage
3. Link publications to existing journal/conference entities
4. Create new venue entities for missing publications
5. Handle incomplete information appropriately

**Success Criteria**: All publications accurately represented, author relationships correctly established, venue relationships properly linked, incomplete data flagged

### Scenario B2: Journal Collection Management
**Role**: Cataloging Librarian  
**Complexity**: Advanced (60-75 minutes)

**Context**: Institution subscribes to "Journal of Climate Research." Volume 15, Issue 3 released with 12 articles requiring comprehensive metadata.

**Materials Provided**:
- Complete table of contents for Volume 15, Issue 3
- Author information
- Abstract text for each article

**Tasks**:
1. Create or update journal issue record
2. Create individual article records for all 12 articles
3. Establish hierarchical relationships (Journal → Volume → Issue → Articles)
4. Link articles to existing or new author entities
5. Apply consistent subject headings
6. Ensure proper pagination and sequencing

**Success Criteria**: Complete hierarchical structure established, all articles accurately cataloged, consistent subject heading application, proper navigation between related items

### Scenario B3: Citation Error Correction
**Role**: Metadata Specialist  
**Complexity**: Intermediate (30-45 minutes)

**Context**: Researcher reported errors in bibliographic records affecting citation accuracy. Corrections needed with proper change tracking.

**Materials Provided**:
- List of problematic citations with reported errors
- Correct information from authoritative sources
- Original bibliographic records with errors

**Tasks**:
1. Locate records with reported errors
2. Verify errors against authoritative sources
3. Correct title, author, and publication information
4. Update relationships if needed
5. Document sources of corrections

**Success Criteria**: All reported errors identified and corrected, changes properly documented, no information loss during corrections, updated records validate correctly

### Scenario B4: Author Disambiguation
**Role**: Cataloging Librarian or Data Curator  
**Complexity**: Advanced (45-60 minutes)

**Context**: Multiple author entities exist for the same person due to name variations. Merge duplicates while preserving publication relationships.

**Materials Provided**:
- List of suspected duplicate authors
- Publication lists for verification
- ORCID information where available
- Institutional affiliation data

**Tasks**:
1. Identify duplicate author entities
2. Verify they represent the same person
3. Merge duplicate entities using merge functionality
4. Resolve conflicting information (name variants, affiliations)
5. Ensure all publication relationships preserved

**Success Criteria**: Duplicates correctly identified and merged, all publication relationships maintained, conflicting information appropriately resolved, single comprehensive author entity created

### Scenario B5: Conference Proceedings Processing
**Role**: Academic Librarian  
**Complexity**: Advanced (60-90 minutes)

**Context**: Complete conference proceedings volume received requiring processing of conference record, proceedings volume, and individual papers.

**Materials Provided**:
- Conference information (title, dates, location, organizers)
- Proceedings volume metadata
- Table of contents with 15 individual papers
- Author information for all papers

**Tasks**:
1. Create conference entity record
2. Create proceedings volume record
3. Create individual paper records
4. Establish hierarchical relationships (Conference → Proceedings → Papers)
5. Link authors to papers and verify author entities
6. Apply appropriate subject headings

**Success Criteria**: Complete conference hierarchy established, all papers properly linked to proceedings and conference, author relationships correctly established, consistent metadata across all levels

### Scenario B6: Version History and Record Recovery
**Role**: Metadata Specialist or Cataloging Librarian  
**Complexity**: Expert (45-60 minutes)

**Context**: Several bibliographic records incorrectly modified over time. Restore to previous correct versions using change history.

**Materials Provided**:
- List of 5 problematic records with known good historical states
- Information about when correct versions existed
- Documentation of problematic changes
- Guidelines for version restoration decisions

**Tasks**:
1. Access version history for each problematic record
2. Identify correct previous versions to restore
3. Compare different versions to understand changes
4. Restore appropriate previous versions
5. Verify restored records are correct
6. Document restoration decisions and rationale

**Success Criteria**: Version history successfully accessed and interpreted, correct previous versions identified accurately, records restored to appropriate historical states, no loss of valid recent changes, restoration decisions properly documented

## Execution Guidelines

### Pre-Scenario Setup
1. Prepare all materials in advance
2. Brief participant on role and context
3. Establish realistic time constraints
4. Provide access to help documentation
5. Set up recording and observation tools

### During Execution
- Encourage think-aloud verbalization
- Note confusion or difficulty points
- Allow natural problem-solving without excessive intervention
- Document successful strategies and failures
- Track time spent on different task aspects

### Post-Scenario Debriefing
1. How realistic was this scenario for your typical work?
2. What aspects were most/least intuitive?
3. How would you approach this in your current system?
4. What information or tools were missing?
5. How confident are you in the results achieved?

### Scenario Variations
**Difficulty Adjustments**: Novice (more complete information) → Expert (more ambiguous information and complex relationships)

**Experience Adaptations**: Adjust scenarios to participant's actual professional role, modify institutional context, adapt complexity to experience level

## Success Metrics

### Task Completion
- **Full**: All required tasks completed successfully
- **Partial**: Core tasks completed with minor omissions
- **Functional**: Basic objectives met despite process issues
- **Incomplete**: Unable to complete primary objectives

### Quality Assessment
- **Metadata Quality**: Accuracy, completeness, and consistency
- **Relationship Management**: Appropriate entity relationships
- **Standard Compliance**: Adherence to bibliographic standards
- **Workflow Efficiency**: Effective system feature use

### Learning and Adaptation
- **System Understanding**: Growing familiarity with interface
- **Problem-Solving**: Effective obstacle-overcoming strategies
- **Feature Discovery**: Independent identification and use of features
- **Professional Integration**: Alignment with established practices 