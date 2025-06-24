# User Scenarios for HERITRACE Testing

## Overview

This document provides realistic, task-based scenarios for testing HERITRACE with end users. Each scenario is designed to reflect authentic workflows and challenges that librarians, archivists, curators, and researchers encounter in their daily work.

## Integration with Testing Protocol

**Important**: These scenarios are designed to work **in conjunction with** the [End User Testing Protocol](03_end_user_testing.md). They provide realistic context and materials that replace the generic tasks described in the testing protocol.

### How Scenarios Replace Generic Tasks

**Testing Protocol Structure** (from 03_end_user_testing.md):
- Session 1: Initial exploration → Use simplified versions of scenarios for first impressions
- Session 2: Core functionality → Use complete scenarios matching participant's role
- Session 3: Advanced features → Use complex scenarios requiring advanced workflows

**Scenario Implementation**:
1. **Scenario Selection**: Choose scenarios based on participant's professional background
2. **Complexity Matching**: Adjust scenario complexity to participant's experience level
3. **Time Allocation**: Use scenario time estimates to plan testing sessions
4. **Success Criteria**: Apply scenario-specific success criteria alongside protocol metrics

### Scenario-to-Session Mapping

| Testing Session | Generic Task (Protocol) | Realistic Scenario Examples |
|-----------------|-------------------------|----------------------------|
| **Session 1: Exploration** | "Examine sample records" | Use scenario backgrounds for context |
| **Session 2: Core Tasks** | "Create new record" | A1 (Faculty Publications), M1 (Art Catalog) |
| **Session 2: Core Tasks** | "Edit existing record" | A2 (Journal Management), AR1 (Personal Papers) |
| **Session 2: Core Tasks** | "Manage relationships" | A3 (Retrospective Collection), R1 (DH Bibliography) |
| **Session 3: Advanced** | "Entity merging" | All scenarios include duplicate resolution |
| **Session 3: Advanced** | "Change tracking" | R2 (Collaborative Dataset) - multi-user context |

## Scenario Categories

### Academic Library Scenarios
### Archive Management Scenarios  
### Museum Curation Scenarios
### Research Project Scenarios

---

## Academic Library Scenarios

### Scenario A1: New Faculty Publication Processing

**Background Context:**
Dr. Sarah Chen, a new faculty member in Environmental Science, has just joined your university. She has provided you with a list of her recent publications that need to be added to the institutional repository and linked to her faculty profile.

**User Role**: Subject Librarian
**Complexity Level**: Intermediate
**Estimated Time**: 45-60 minutes

**Provided Materials:**
- CV with 8 recent publications (journal articles, conference papers, book chapter)
- ORCID ID: 0000-0002-1825-0097
- Complete citation information for each publication
- 3 publications have DOIs, 2 have missing publication dates

**Primary Tasks:**
1. Create bibliographic records for all 8 publications
2. Establish Dr. Chen as an author entity with ORCID linkage
3. Link publications to existing journal/conference entities where possible
4. Create new venue entities for publications not yet in the system
5. Handle incomplete information appropriately

**Success Criteria:**
- All publications accurately represented in the system
- Author relationships correctly established
- Venue relationships properly linked
- Incomplete data flagged for future completion

**Complexity Factors:**
- Mix of publication types requiring different metadata schemas
- Need to distinguish between similar journal titles
- Handling of missing/incomplete publication information
- Integration with existing institutional data

### Scenario A2: Journal Collection Management

**Background Context:**
Your library subscribes to the "Journal of Climate Research" and needs to maintain comprehensive metadata for all issues and articles. The journal has just released volume 15, issue 3, containing 12 articles, and you need to update your records.

**User Role**: Cataloging Librarian
**Complexity Level**: Advanced
**Estimated Time**: 60-75 minutes

**Provided Materials:**
- Complete table of contents for Volume 15, Issue 3
- Author information including institutional affiliations
- Abstract text for each article
- Special issue theme: "Coastal Climate Adaptation"

**Primary Tasks:**
1. Create or update the journal issue record
2. Create individual article records for all 12 articles
3. Establish proper hierarchical relationships (Journal → Volume → Issue → Articles)
4. Link articles to existing or new author entities
5. Apply consistent subject headings related to the special theme
6. Ensure proper pagination and sequencing

**Success Criteria:**
- Complete hierarchical structure properly established
- All articles accurately cataloged with full metadata
- Consistent application of subject headings
- Proper navigation between related items

**Complexity Factors:**
- Managing hierarchical relationships across multiple levels
- Handling collaborative authorship and institutional affiliations
- Maintaining consistency in subject classification
- Ensuring proper sequence and pagination relationships

### Scenario A3: Retrospective Collection Digitization

**Background Context:**
Your library is digitizing a collection of 1970s environmental science reports that were never properly cataloged. These reports have minimal existing metadata and require comprehensive description based on physical examination and content analysis.

**User Role**: Digital Collections Librarian
**Complexity Level**: Advanced
**Estimated Time**: 75-90 minutes

**Provided Materials:**
- Scanned cover pages and title pages for 6 reports
- Basic provenance information (donation records)
- Institutional guidelines for retrospective cataloging
- Authority files for environmental science subjects

**Primary Tasks:**
1. Create comprehensive bibliographic records from minimal source information
2. Establish corporate authorship for government agencies and research institutions
3. Apply appropriate subject headings and classification
4. Create collection-level relationships between related reports
5. Document provenance and digitization information
6. Handle uncertain or incomplete information appropriately

**Success Criteria:**
- Rich, discoverable metadata created from limited sources
- Appropriate authority work for corporate authors
- Consistent subject analysis and classification
- Clear documentation of information sources and certainty levels

**Complexity Factors:**
- Limited source information requiring interpretation
- Authority work for historical corporate entities
- Balancing completeness with available information
- Maintaining consistency across a collection

---

## Archive Management Scenarios

### Scenario AR1: Personal Papers Processing

**Background Context:**
The university archives has received the papers of Dr. Margaret Williams, a prominent 20th-century historian. The collection includes correspondence, manuscripts, photographs, and research materials spanning 1945-1995. You need to create a hierarchical description following archival standards.

**User Role**: Processing Archivist
**Complexity Level**: Advanced
**Estimated Time**: 90-120 minutes

**Provided Materials:**
- Preliminary inventory with series organization
- Sample correspondence and manuscript materials
- Biographical information about Dr. Williams
- Related collections already in the archives

**Primary Tasks:**
1. Create collection-level description with appropriate archival metadata
2. Establish series and subseries hierarchy
3. Create detailed descriptions for selected significant items
4. Link to related collections and external resources
5. Establish access points for researchers (subjects, correspondents, organizations)
6. Document processing decisions and arrangement choices

**Success Criteria:**
- Multi-level archival description properly structured
- Rich access points for discovery
- Clear relationships to related materials
- Professional archival standards maintained

**Complexity Factors:**
- Multi-level hierarchical description
- Archival vs. bibliographic description standards
- Handling of mixed materials and formats
- Establishing intellectual relationships between materials

### Scenario AR2: Institutional Records Management

**Background Context:**
The university is transferring records from the Office of Student Affairs covering academic years 2015-2020. These records include policy documents, meeting minutes, correspondence, and student organization files. You need to establish proper archival control and access.

**User Role**: University Archivist
**Complexity Level**: Intermediate
**Estimated Time**: 60-75 minutes

**Provided Materials:**
- Records transfer documentation
- Office organizational charts
- Records retention schedules
- Sample documents from each record series

**Primary Tasks:**
1. Establish record group and series organization
2. Create appropriate administrative metadata
3. Apply retention and access restrictions
4. Link to related institutional records
5. Create researcher access points
6. Document chain of custody and transfer process

**Success Criteria:**
- Proper archival control established
- Access restrictions appropriately applied
- Clear documentation of provenance
- Integration with broader institutional records program

**Complexity Factors:**
- Institutional context and administrative relationships
- Privacy and access restriction considerations
- Integration with records management systems
- Long-term preservation planning

---

## Museum Curation Scenarios

### Scenario M1: Art Exhibition Catalog

**Background Context:**
Your museum is preparing a catalog for an upcoming exhibition "Environmental Art: 1960-2020". The exhibition includes 45 artworks from various collections, and you need to create comprehensive catalog records that will support both the physical catalog and online exhibition materials.

**User Role**: Museum Cataloger
**Complexity Level**: Advanced
**Estimated Time**: 90-120 minutes

**Provided Materials:**
- Artwork information sheets with basic details
- High-resolution images for selected pieces
- Artist biographical information
- Thematic organization for exhibition sections

**Primary Tasks:**
1. Create detailed catalog records for selected artworks
2. Establish artist entities with biographical information
3. Link artworks to broader movements and themes
4. Create exhibition context and curatorial relationships
5. Establish provenance and ownership information
6. Apply museum standards for object description

**Success Criteria:**
- Museum-quality catalog records with appropriate detail
- Rich contextual information for researchers
- Proper attribution and provenance documentation
- Integration with exhibition narrative

**Complexity Factors:**
- Museum vs. library cataloging standards
- Complex provenance and ownership tracking
- Artistic and cultural context description
- Rights and permissions management

### Scenario M2: Natural History Specimen Collection

**Background Context:**
The natural history museum has acquired a collection of geological specimens from a private collector. The collection includes 200 specimens with varying levels of documentation, and you need to create systematic catalog records that support both research and public access.

**User Role**: Collections Manager
**Complexity Level**: Intermediate
**Estimated Time**: 75-90 minutes

**Provided Materials:**
- Collector's original catalog with specimen numbers
- Scientific identification information
- Geographic and temporal collection data
- Museum accessioning documentation

**Primary Tasks:**
1. Create systematic catalog records for specimen groups
2. Establish proper scientific classification and nomenclature
3. Document collection context and provenance
4. Link to related specimens and collections
5. Apply appropriate subject headings for scientific research
6. Ensure compliance with museum standards

**Success Criteria:**
- Scientific accuracy in classification and description
- Proper documentation of collection context
- Research-accessible organization and metadata
- Integration with broader museum collections

**Complexity Factors:**
- Scientific accuracy and nomenclature standards
- Geographic and temporal context documentation
- Integration with museum collection management systems
- Supporting both research and public access needs

---

## Research Project Scenarios

### Scenario R1: Digital Humanities Project Bibliography

**Background Context:**
You are managing a digital humanities project investigating "Women Scientists in 20th Century America". The project team has compiled bibliographic sources from multiple disciplines and needs a comprehensive, searchable bibliography.

**User Role**: Digital Humanities Librarian
**Complexity Level**: Advanced
**Estimated Time**: 90-120 minutes

**Provided Materials:**
- Mixed bibliography with 25 sources (books, articles, archival materials)
- Project-specific subject categories and tags
- Contributor information for collaborative project
- Links to digital versions where available

**Primary Tasks:**
1. Create comprehensive records for diverse source types
2. Apply project-specific subject classification and tagging
3. Establish relationships between related sources
4. Link to digital versions and external resources
5. Create contributor and project context information
6. Ensure compatibility with project research tools

**Success Criteria:**
- Rich, searchable bibliography supporting research goals
- Consistent application of project-specific organization
- Effective linking to digital resources
- Support for collaborative research workflows

**Complexity Factors:**
- Interdisciplinary source materials
- Project-specific vs. standard classification schemes
- Integration with digital humanities tools and workflows
- Collaborative metadata creation and maintenance

### Scenario R2: Collaborative Research Dataset Documentation

**Background Context:**
A multi-institutional research team studying climate change impacts needs to document and describe their shared research datasets. The datasets include observational data, model outputs, and literature reviews, all requiring comprehensive metadata for discovery and reuse.

**User Role**: Research Data Librarian
**Complexity Level**: Expert
**Estimated Time**: 120-150 minutes

**Provided Materials:**
- Technical documentation for 5 major datasets
- Research team contact information and institutional affiliations
- Data management plan requirements
- Funder metadata requirements

**Primary Tasks:**
1. Create detailed dataset descriptions following research data standards
2. Establish proper attribution for collaborative research
3. Document methodology and technical specifications
4. Link datasets to related publications and projects
5. Apply appropriate subject classification for discovery
6. Ensure compliance with funder and institutional requirements

**Success Criteria:**
- Research-quality dataset documentation
- Proper attribution and intellectual property documentation
- Compliance with metadata standards and requirements
- Support for data discovery and reuse

**Complexity Factors:**
- Technical complexity of research data description
- Multi-institutional collaboration and attribution
- Compliance with multiple metadata standards
- Long-term preservation and access planning

---

## Scenario Execution Guidelines

### Pre-Scenario Setup

**For Each Scenario:**
1. Prepare all materials in advance
2. Brief participant on role and context
3. Establish realistic time constraints
4. Provide access to help documentation
5. Set up screen recording and observation tools

### During Scenario Execution

**Facilitator Guidelines:**
- Encourage think-aloud verbalization
- Note points of confusion or difficulty
- Allow natural problem-solving without excessive intervention
- Document both successful strategies and failures
- Track time spent on different aspects of tasks

### Post-Scenario Debriefing

**Key Questions:**
1. How realistic was this scenario for your typical work?
2. What aspects of the task were most/least intuitive?
3. How would you approach this work in your current system?
4. What information or tools were missing?
5. How confident are you in the results you achieved?

### Scenario Variations

**Difficulty Adjustments:**
- **Novice**: Provide more complete source information and clearer instructions
- **Expert**: Include more ambiguous information and complex relationships
- **Time-Constrained**: Focus on essential tasks only
- **Comprehensive**: Include all optional tasks and quality control steps

**Role Adaptations:**
- Adjust scenarios based on participant's actual professional role
- Modify institutional context to match participant's workplace
- Adapt complexity to participant's experience level
- Include tools and standards familiar to participant

## Success Metrics for Scenarios

### Task Completion Metrics
- **Full Completion**: All required tasks completed successfully
- **Partial Completion**: Core tasks completed with minor omissions
- **Functional Completion**: Basic objectives met despite process issues
- **Incomplete**: Unable to complete primary scenario objectives

### Quality Assessment
- **Metadata Quality**: Accuracy, completeness, and consistency of created records
- **Relationship Management**: Appropriate establishment of entity relationships
- **Standard Compliance**: Adherence to relevant professional standards
- **Workflow Efficiency**: Effective use of system features and capabilities

### Learning and Adaptation
- **System Understanding**: Evidence of growing familiarity with interface
- **Problem-Solving**: Effective strategies for overcoming obstacles
- **Feature Discovery**: Independent identification and use of relevant features
- **Professional Integration**: Alignment with established professional practices 