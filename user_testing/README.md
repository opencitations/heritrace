# HERITRACE User Testing Protocol

This directory contains user testing protocols for HERITRACE (Heritage Enhanced Repository Interface for Tracing, Research, Archival Curation, and Engagement).

## Overview

HERITRACE is a semantic editor for GLAM professionals to facilitate metadata enrichment and editing. This protocol evaluates system usability, effectiveness, and user experience across two user categories.

## User Categories

| Category | Role | Focus |
|----------|------|-------|
| **Technicians** (4-6 participants) | Staff responsible for semantic system configuration | SHACL schema customization, display rules configuration |
| **End Users** (8-12 participants) | Academic professionals working with bibliographic metadata | Metadata creation/editing, search, workflows |

## Testing Framework

| Document | Purpose |
|----------|---------|
| [01_end_user_testing.md](01_end_user_testing.md) | Usability and functionality testing |
| [02_analysis_framework.md](02_analysis_framework.md) | Analysis and reporting framework |
| [questionnaires/](questionnaires/) | Pre-test and SUS questionnaires |

## Methodology

**Self-Guided Approach**:
- Participants conduct autonomous testing with screen and voice recording
- Specific task scenarios with structured reflection questions

**Mixed Methods**:
- Quantitative: Task completion rates, SUS scores, error frequencies
- Qualitative: Self-recorded think-aloud protocols, structured reflection responses

## Prerequisites

**Technicians**: SHACL validation knowledge (min level 4/7), RDF/SPARQL concepts, configuration file experience

**End Users**: Bibliographic metadata experience, web application comfort

## Success Criteria

| Category | Targets |
|----------|---------|
| **Technicians** | Technical completion of 3 configuration tasks, SUS score ≥65, complete recordings |
| **End Users** | 85% creation, 90% addition, 75% correction, 70% merge, 80% restore, SUS score ≥65 |

## Deliverables

1. Grounded theory analysis report from screen+voice recordings
2. Task completion analysis with specific HERITRACE improvement recommendations
3. SUS usability benchmarks and user experience insights
4. Prioritized HERITRACE development roadmap based on quantified user issues