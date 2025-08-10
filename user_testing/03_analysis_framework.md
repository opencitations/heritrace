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
      "actual_duration_minutes": "[HH:MM:SS]",
      "status": "[complete|partial|failed]",
      "errors_encountered": "[DERIVED: COUNT(errors)]",
      "errors": [
        {
          "severity": "[low|medium|high]",
          "symptom": "[WHAT WAS OBSERVED]",
          "trigger": "[USER_ACTION_THAT_LED_TO_ERROR]",
          "outcome": "[blocked|recovered|workaround]"
        }
      ]
    },
    "merge_authors": {
      "task_name": "Merge duplicate author entities",
      "expected_duration_minutes": 10,
      "actual_duration_minutes": "[HH:MM:SS]",
      "status": "[complete|partial|failed]",
      "errors_encountered": "[DERIVED: COUNT(errors)]",
      "errors": []
    },
    "restore_version": {
      "task_name": "Restore previous version",
      "expected_duration_minutes": 7,
      "actual_duration_minutes": "[HH:MM:SS]",
      "status": "[complete|partial|failed]",
      "errors_encountered": "[DERIVED: COUNT(errors)]",
      "errors": []
    },
    "create_publication": {
      "task_name": "Create new publication record",
      "expected_duration_minutes": 20,
      "actual_duration_minutes": "[HH:MM:SS]",
      "status": "[complete|partial|failed]",
      "errors_encountered": "[DERIVED: COUNT(errors)]",
      "errors": []
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
      "actual_duration_minutes": "[HH:MM:SS]",
      "status": "[complete|partial|failed]",
      "errors_encountered": "[DERIVED: COUNT(errors)]",
      "errors": [
        {
          "severity": "[low|medium|high]",
          "symptom": "[WHAT WAS OBSERVED]",
          "trigger": "[USER_ACTION_THAT_LED_TO_ERROR]",
          "outcome": "[blocked|recovered|workaround]"
        }
      ]
    },
    "add_display_support": {
      "task_name": "Add abstract display support",
      "expected_duration_minutes": 23,
      "actual_duration_minutes": "[HH:MM:SS]",
      "status": "[complete|partial|failed]",
      "errors_encountered": "[DERIVED: COUNT(errors)]",
      "errors": []
    }
  }
}
```

**Task Completion Analysis Instructions:**
1. **Create individual files**: `[participant_ID]_task_completion.json` for each participant
2. **While watching videos**: Measure actual duration and count visible errors. Record `actual_duration_minutes` strictly as `HH:MM:SS` (hours:minutes:seconds)
3. **Status definitions**: 
   - `complete` = working deliverable produced
   - `partial` = incomplete attempt with some progress
   - `failed` = task abandoned or no progress
4. **Error counting**: Use the counting protocol below. Record each event in the `errors` list; `errors_encountered` is the count of that list.

**Important**: The `errors_encountered` field should match error-related codes in qualitative coding for consistency.

### Error definition and severity

An error is any observable event that prevents expected progress, forces a retry/workaround, or indicates user confusion tied to a specific interface or configuration cause. Classify each event by severity only (grounded categories will be derived later during coding).

- **Severity**
  - **high**: Blocks task completion or requires restart/support.
  - **medium**: Requires workaround/retry and causes noticeable delay.
  - **low**: Minor issue or confusion with little impact on time.

### Error counting protocol

- Count one event per distinct occurrence; repeated identical misclicks within 5 seconds count as a single event.
- The same error happening again later counts as a new event.
- Only count issues tied to an action or UI state; do not count passive reading or expected confirmation prompts.
- If multiple symptoms stem from one underlying cause (e.g., a single SHACL issue leading to two messages), record one event and note symptoms in `symptom`.

### Aggregation metrics (Phase 2)

From the templates above, compute:

- **Errors per task** and **per participant**
- **Severity-weighted error score** per task: low=1, medium=2, high=4 (sum over events)
- **Error rate per minute**: errors_encountered / actual_duration_minutes
- **Blocked tasks**: tasks with any high-severity event with outcome `blocked`
- **Task success rate** (per user type and per task): `((complete) + 0.5 * (partial)) / (complete + partial + failed) * 100`

## Step 3: Grounded Analysis

### User-Type Specific Analysis

**Base Template**: Use this structure for both user types, specifying `user_type` as `"end_user"` or `"technician"`

#### Open Coding Phase
**Template**: `[user_type]_[participant_ID]_codes.json`
```json
{
  "participant_id": "[PARTICIPANT_ID]",
  "user_type": "[end_user|technician]",
  "codes": [
    {
      "code": "[PARTICIPANT_EXACT_WORDS]",
      "verbatim_quote": "[EXACT_QUOTE_FROM_DATA]",
      "context": "[SITUATION_DESCRIPTION]",
      "sentiment": "[positive|neutral|negative]"
    }
  ]
}
```

#### Axial Coding Phase
**Template**: `[user_type]_axial_codes.json`
```json
{
  "user_type": "[end_user|technician]",
  "categories": [
    {
      "category_name": "[CATEGORY_NAME]",
      "related_codes": [
        {
          "participant_id": "[PARTICIPANT_ID]",
          "code": "[CODE_NAME]"
        }
      ],
      "category_description": "[HOW_CODES_RELATE]",
      "task_contexts": ["[TASK1]", "[TASK2]"],
      "overall_sentiment": "[positive|neutral|negative]",
      "frequency": "[NUMBER_OF_RELATED_CODES]"
    }
  ]
}
```

#### Selective Coding Phase
**Template**: `[user_type]_selective_codes.json`
```json
{
  "user_type": "[end_user|technician]",
  "core_category": "[CENTRAL_THEME_NAME]",
  "theory_statement": "[MAIN_EXPLANATION_OF_USER_EXPERIENCE]",
  "supporting_categories": [
    {
      "category": "[CATEGORY_NAME]",
      "relationship_to_core": "[HOW_IT_SUPPORTS_MAIN_THEORY]",
      "frequency": "[HOW_MANY_PARTICIPANTS_AFFECTED]"
    }
  ]
}
```

# Data visualization

**1. Task Success Rate by User Type**
- **Type**: Side-by-side bar charts (separate charts for each user type)
- **Input**: Calculate from individual `task_completion.json` files
- **End User Chart**: edit_publication, merge_authors, restore_version, create_publication
- **Technician Chart**: add_shacl_validation, add_display_support
- **Y-axis**: Success percentage (0-100%)
- **Success calculation**: `complete = 1`, `partial = 0.5`, `failed = 0`
- **Output**: Shows task difficulty within each user type separately

**2. Duration Analysis Scatter Plot**  
- **Type**: Scatter plot with reference line
- **Input**: Extract expected_duration and actual_duration from task completion files
- **X-axis**: Expected duration (minutes)
- **Y-axis**: Actual duration (minutes)
- **Colors**: User type distinction
- **Reference line**: y=x diagonal for perfect time estimation
- **Output**: Reveals time estimation accuracy patterns

**3. Error Metrics Heatmaps**
- **Type**: Two matrix heatmaps
- **Inputs**:
  - Heatmap A: `errors_encountered` per participant-task
  - Heatmap B: severity-weighted score per participant-task (low=1, medium=2, high=4)
- **Rows**: Participants  
- **Columns**: Task types
- **Output**: Highlights hotspots by count and by impact

**4. Error Category Distribution (derived from grounded analysis)**
- **Type**: Stacked bar chart by task (separate charts per user type)
- **Input**: Categories emerging from axial coding mapped to error events
- **Output**: Shows which grounded categories dominate per task


**5. Grounded Theory Category TreeMap**
- **Type**: Hierarchical TreeMap visualization (separate for each user type)
- **Input**: Extract categories, frequencies and sentiment from `axial_codes.json` files
- **Rectangle size**: Category frequency (from `frequency` field in JSON)
- **Color coding**: Category sentiment (from `overall_sentiment` field: red=negative, yellow=neutral, green=positive)
- **Hierarchical nesting**: Core categories contain related subcategories
- **Interactive**: Click to drill down into category details and supporting quotes
- **Output**: Visual representation of user experience themes with relative importance and emotional impact

# SUS Analysis

## SUS Score Calculation

The System Usability Scale (SUS) provides a standardized usability metric. Calculate SUS scores using the standard formula:

1. **Score Processing**:
   - Odd items (1,3,5,7,9): Score = rating - 1
   - Even items (2,4,6,8,10): Score = 5 - rating
   
2. **Total Calculation**: Sum all scores and multiply by 2.5
3. **Range**: Final scores range from 0-100

## SUS Subscales (Usability & Learnability)

### Calculation
- **Usability (8 item)**: items 1,2,3,5,6,7,8,9
- **Learnability (2 item)**: items 4,10

Conversion is identical to SUS total (each item to 0–4). For each subscale:
- Compute the mean of its items (0–4) and multiply by 25 → 0–100 scale.

## SUS Data Processing

**Input Files**: Extract ratings from `results/[endusers|technicians]/sus/[participant_id]_sus.md`

**Output Structure**: `results/aggregated_analysis/sus/`
```
sus_individual_scores.json
sus_aggregated_report.json
sus_visualizations.png
```

Notes:
- `sus_individual_scores.json` includes `usability_score` and `learnability_score` per participant.
- `sus_aggregated_report.json` includes `subscales_summary` per user type.

**Aggregated Metrics by User Type**:
- Mean SUS score
- Standard deviation
- Median score
- Score range (min-max)
- Individual participant scores

## SUS Benchmarking

Reference benchmarks for interpretation:
- Below 68: Below average usability
- 68-80.3: Above average usability  
- Above 80.3: Excellent usability

## SUS Visualization Templates

**1. SUS Score Distribution by User Type**
- **Type**: Box plot comparison
- **Input**: Individual SUS scores grouped by user type
- **Output**: Shows score distribution, median, and outliers with benchmark thresholds

**2. Statistics Summary Table**
- **Type**: Text-based summary table
- **Input**: Aggregated statistics by user type
- **Output**: Count, mean, standard deviation, median, and range for each user type

**3. Subscale Distributions by User Type**
- **Type**: Two box plots — one per subscale (Usability, Learnability)
- **Overlays**: horizontal guides at 60 (needs improvement) e 80 (excellent)
- **Output**: Distribuzione delle sottoscale per tipo utente con soglie di interpretazione

## SUS Software Usage

**Running the Analysis**:
```bash
cd user_testing/analysis_software
uv run python sus_calculator.py
```

**Prerequisites**:
- SUS questionnaire files in markdown format at `results/[endusers|technicians]/sus/`
- Dependencies installed via `uv sync`

**Output Files**:
- JSON files with detailed scores and statistics
- PNG visualization with box plots and summary table

## Task Analysis Software Usage

**Running the Analysis**:
```bash
cd user_testing/analysis_software
# Option A: esegui l'intera pipeline (metriche + grafici)
uv run python task_pipeline.py

# Option B: esegui singoli step
uv run python task_metrics.py
uv run python task_plots.py
```

**Prerequisites**:
- Task completion files at `results/[endusers|technicians]/task_completion/`
- Dependencies installed via `uv sync`

**Output Files** (in `results/aggregated_analysis/tasks/`):
- `task_metrics.json`
- `task_success_rates.png`
- `task_duration_expected_vs_actual.png`
- `task_error_heatmaps.png`
