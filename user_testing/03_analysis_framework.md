# HERITRACE User Testing Analysis Framework

## Overview

This framework provides a systematic approach to transform user testing data into actionable insights for HERITRACE system improvement. The analysis follows a structured 3-phase workflow designed for data collected from self-guided testing sessions with screen recordings, voice recordings, SUS questionnaires, and written reflections.

## Analysis Workflow Overview

The framework is organized into three sequential phases:
1. **Manual Analysis** - Transcription correction, coding, and task completion tracking
2. **Data Aggregation** - Automated processing of individual analysis files  
3. **Insight Generation** - Synthesis into development priorities and recommendations

# Manual Analysis

## Step 1: Transcription Processing

**Automatic Transcription**
- Use transcription tool: `./analysis_software/transcriber.py`
- Generate initial transcripts: `participant_ID_transcript_raw.txt`

**Manual Correction**
- Review automated transcripts while watching videos
- Correct transcription errors and unclear sections

## Step 2: Task Completion Analysis

### Task Completion Templates

Create individual completion analysis files for each participant using standardized templates.

**Template Structure**:

**End User Tasks:**
```json
{
  "participant_id": "[REPLACE_WITH_PARTICIPANT_ID]",
  "user_type": "end_user",
  "tasks": {
    "edit_publication": {
      "task_name": "Edit existing publication record",
      "expected_duration_minutes": 8,
      "actual_duration_minutes": "[MEASURE_FROM_VIDEO]",
      "status": "[complete|partial|failed]",
      "errors_encountered": "[COUNT_FROM_VIDEO]",
      "help_sought": "[true|false]"
    },
    "merge_authors": {
      "task_name": "Merge duplicate author entities",
      "expected_duration_minutes": 10,
      "actual_duration_minutes": "[MEASURE_FROM_VIDEO]",
      "status": "[complete|partial|failed]",
      "errors_encountered": "[COUNT_FROM_VIDEO]",
      "help_sought": "[true|false]"
    },
    "restore_version": {
      "task_name": "Restore previous version",
      "expected_duration_minutes": 7,
      "actual_duration_minutes": "[MEASURE_FROM_VIDEO]",
      "status": "[complete|partial|failed]",
      "errors_encountered": "[COUNT_FROM_VIDEO]",
      "help_sought": "[true|false]"
    },
    "create_publication": {
      "task_name": "Create new publication record",
      "expected_duration_minutes": 20,
      "actual_duration_minutes": "[MEASURE_FROM_VIDEO]",
      "status": "[complete|partial|failed]",
      "errors_encountered": "[COUNT_FROM_VIDEO]",
      "help_sought": "[true|false]"
    }
  }
}
```

**Technician Tasks:**
```json
{
  "participant_id": "[REPLACE_WITH_PARTICIPANT_ID]",
  "user_type": "technician",
  "tasks": {
    "add_shacl_validation": {
      "task_name": "Add SHACL validation for abstract",
      "expected_duration_minutes": 22,
      "actual_duration_minutes": "[MEASURE_FROM_VIDEO]",
      "status": "[complete|partial|failed]",
      "errors_encountered": "[COUNT_FROM_VIDEO]",
      "help_sought": "[true|false]"
    },
    "add_display_support": {
      "task_name": "Add abstract display support",
      "expected_duration_minutes": 23,
      "actual_duration_minutes": "[MEASURE_FROM_VIDEO]",
      "status": "[complete|partial|failed]",
      "errors_encountered": "[COUNT_FROM_VIDEO]",
      "help_sought": "[true|false]"
    }
  }
}
```

**Task Completion Analysis Instructions:**
1. **Create individual files**: `[participant_ID]_task_completion.json` for each participant
2. **While watching videos**: Measure actual duration and count visible errors
3. **Status definitions**: 
   - `complete` = working deliverable produced
   - `partial` = incomplete attempt with some progress
   - `failed` = task abandoned or no progress
4. **Error counting**: Include wrong clicks, error messages, confusion incidents
5. **Help seeking**: Note when participant explicitly seeks help or guidance

**Important**: The `errors_encountered` field should match error-related codes in qualitative coding for consistency.

## Step 3: Grounded Analysis

### Unified Qualitative Coding Process

**Individual Coding Templates**

Create individual coding files for each participant: `[participant_ID]_codes.json`

**Template Structure:**
```json
{
  "participant_id": "[REPLACE_WITH_PARTICIPANT_ID]",
  "user_type": "[end_user|technician]",
  "codes": [
    {
      "code_name": "[DESCRIPTIVE_CODE_NAME]",
      "verbatim_quote": "[EXACT_PARTICIPANT_QUOTE]",
      "context": "[SITUATIONAL_CONTEXT]"
    }
  ]
}
```

**Coding Instructions:**
1. Create individual files: One `[participant_ID]_codes.json` per participant
2. Code from both thinking aloud (video recordings) and written reflections
3. Let codes emerge naturally from the data without predefined categories
4. Keep codes close to participant language and document situational context