# HERITRACE user testing analysis framework

## Overview

This framework provides a systematic approach to transform user testing data into actionable insights for HERITRACE system improvement. The analysis follows a structured 3-phase workflow designed for data collected from self-guided testing sessions with screen recordings, voice recordings, SUS questionnaires, and written reflections.

## Analysis workflow overview

The framework is organized into three sequential phases:
1. **Manual analysis** - Transcription correction, coding, and task completion tracking
2. **Data aggregation** - Automated processing of individual analysis files  
3. **Insight generation** - Synthesis into development priorities and recommendations

# Manual analysis

## Step 1: Transcription processing

**Automatic transcription**
- Use transcription tool: `./analysis_software/transcriber.py`
- Generate initial transcripts: `participant_ID_transcript_raw.txt`

**Manual correction**
- Review automated transcripts while watching videos
- Correct transcription errors and unclear sections

## Step 2: Task completion analysis

### Task completion templates

Create individual completion analysis files for each participant using standardized templates.

**Template structure**:

**End user tasks:**
```json
{
  "participant_id": "[REPLACE_WITH_PARTICIPANT_ID]",
  "user_type": "end_user",
  "tasks": {
    "edit_publication": {
      "task_name": "Edit existing publication record",
      "expected_duration_minutes": 8,
      "actual_duration_minutes": "[HH:MM:SS]",
      "status": "[complete|partial|success_timeout|failed_misunderstanding|failed_bug]",
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
      "status": "[complete|partial|success_timeout|failed_misunderstanding|failed_bug]",
      "errors_encountered": "[DERIVED: COUNT(errors)]",
      "errors": []
    },
    "restore_version": {
      "task_name": "Restore previous version",
      "expected_duration_minutes": 7,
      "actual_duration_minutes": "[HH:MM:SS]",
      "status": "[complete|partial|success_timeout|failed_misunderstanding|failed_bug]",
      "errors_encountered": "[DERIVED: COUNT(errors)]",
      "errors": []
    },
    "create_publication": {
      "task_name": "Create new publication record",
      "expected_duration_minutes": 20,
      "actual_duration_minutes": "[HH:MM:SS]",
      "status": "[complete|partial|success_timeout|failed_misunderstanding|failed_bug]",
      "errors_encountered": "[DERIVED: COUNT(errors)]",
      "errors": []
    }
  }
}
```

**Technician tasks:**
```json
{
  "participant_id": "[REPLACE_WITH_PARTICIPANT_ID]",
  "user_type": "technician",
  "tasks": {
    "add_shacl_validation": {
      "task_name": "Add SHACL validation for abstract",
      "expected_duration_minutes": 22,
      "actual_duration_minutes": "[HH:MM:SS]",
      "status": "[complete|partial|success_timeout|failed_misunderstanding|failed_bug]",
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
      "status": "[complete|partial|success_timeout|failed_misunderstanding|failed_bug]",
      "errors_encountered": "[DERIVED: COUNT(errors)]",
      "errors": []
    }
  }
}
```

**Task completion analysis instructions:**
1. **Create individual files**: `[participant_ID]_task_completion.json` for each participant
2. **While watching videos**: Measure actual duration and count visible errors. Record `actual_duration_minutes` strictly as `HH:MM:SS` (hours:minutes:seconds)
3. **Status definitions**:
   - `complete` = working deliverable produced
   - `partial` = incomplete attempt with some progress
   - `success_timeout` = time limit expired while user was actively working
   - `failed_misunderstanding` = user misunderstood task or feature preventing completion
   - `failed_bug` = system bug prevented task completion
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

### Aggregation metrics (phase 2)

From the templates above, compute:

- **Errors per task** and **per participant**
- **Severity-weighted error score** per task: low=1, medium=2, high=4 (sum over events)
- **Error rate per minute**: errors_encountered / actual_duration_minutes
- **Blocked tasks**: tasks with any high-severity event with outcome `blocked`
- **Task success rate** (per user type and per task): `((complete) + 0.5 * (partial)) / (complete + partial + success_timeout + failed_misunderstanding + failed_bug) * 100`
- **Failure analysis**: Breakdown of failure types (`success_timeout`, `failed_misunderstanding`, `failed_bug`) per task and user type

## Step 3: Grounded analysis

### User-type specific analysis

**Base Template**: Use this structure for both user types, specifying `user_type` as `"end_user"` or `"technician"`

#### Open coding phase

**Constant comparison method**: During open coding, systematically compare each new code with all existing codes from previous participants and contexts. For every new code ask: "What other incidents are similar/different?", "How does this phenomenon vary across participants or tasks?", "What makes this incident unique or typical?". This continuous comparison helps refine code definitions, identify emerging patterns, and avoid redundant or overly narrow codes.

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

#### Axial coding phase
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

##### Axial code verification

**Purpose**: Verify that all open codes have been properly considered in axial coding analysis.

**Running the verification**:
```bash
cd user_testing/analysis_software

poetry run python3 axial_code_verification.py
```

**Output**: Console report showing:
- Missing codes (open codes not included in axial analysis)
- Extra codes (codes in axial analysis but not in open coding)
- Coverage percentage

#### Selective coding phase

**Purpose**: Identify the core category and develop a substantive theory that explains the user experience phenomenon, integrating all axial categories into a coherent theoretical framework.

**Template location**: `results/templates/TEMPLATE_selective_codes.json`

**Output files**:
- End users: `results/endusers/end_user_selective_codes.json`
- Technicians: `results/technicians/technician_selective_codes.json`

**Template structure**: `[user_type]_selective_codes.json`
```json
{
  "user_type": "[end_user|technician]",
  "core_category": "[CENTRAL_THEME_NAME]",
  "theory_statement": "[MAIN_EXPLANATION_OF_USER_EXPERIENCE]",
  "theoretical_propositions": [
    {
      "proposition": "[THEORETICAL_STATEMENT]",
      "explanation": "[HOW_THIS_EXPLAINS_THE_PHENOMENON]"
    }
  ],
  "supporting_categories": [
    {
      "category": "[CATEGORY_NAME_FROM_AXIAL_CODES]",
      "relationship_to_core": "[HOW_IT_SUPPORTS_MAIN_THEORY]",
      "frequency": 0,
      "axial_codes_included": [
        "[AXIAL_CATEGORY_NAME_1]",
        "[AXIAL_CATEGORY_NAME_2]"
      ]
    }
  ]
}
```

**Key fields**:
- `core_category`: The central phenomenon that has the greatest explanatory power and relates to all other categories
- `theory_statement`: A comprehensive explanation of the user experience pattern that emerged from the data
- `theoretical_propositions`: Testable statements that explain relationships and processes discovered in the analysis
- `supporting_categories`: Groups of related axial categories that support the core theory, with explicit relationships explained
- `axial_codes_included`: List of axial category names (from `category_name` field in axial codes) that are grouped under each supporting category

**Analysis guidelines**:
1. Review all axial categories to identify the core category with highest frequency and explanatory power
2. Develop a theory statement that connects all categories into a coherent narrative
3. Create theoretical propositions that explain the main patterns and relationships
4. Group related axial categories into supporting categories that explain different aspects of the core theory
5. Ensure every axial category is integrated into at least one supporting category

**Verification**: After completing selective coding, run the verification script to ensure 100% coverage of axial categories:
```bash
cd user_testing/analysis_software
poetry run python3 selective_code_verification.py
```

# Data visualization

**1. Task completion distribution by user type**
- **Type**: 100% stacked bar charts (separate charts for each user type)
- **Input**: Calculate from individual `task_completion.json` files
- **End User Chart**: edit_publication, merge_authors, restore_version, create_publication
- **Technician Chart**: add_shacl_validation, add_display_support
- **Y-axis**: Completion status percentage (0-100%)
- **Status segments** (bottom to top):
  - Complete: dark green (#1b7837) - working deliverable produced
  - Partial: yellow-orange (#fdae61) - incomplete with progress
  - Success: Timeout: blue (#4575b4) - time expired while working
  - Failed: Misunderstanding: dark red (#d73027) - user misunderstood task or feature
  - Failed: Bug: purple (#7b3294) - system bug prevented completion
- **Colors**: ColorBrewer safe palette (accessible for colorblind users and grayscale printing)
- **Labels**: Percentage labels shown on segments ≥5%
- **Output**: Shows complete task outcome distribution for each task within user type

**2. Duration analysis scatter plot**  
- **Type**: Scatter plot with reference line
- **Input**: Extract expected_duration and actual_duration from task completion files
- **X-axis**: Expected duration (minutes)
- **Y-axis**: Actual duration (minutes)
- **Colors**: User type distinction
- **Reference line**: y=x diagonal for perfect time estimation
- **Output**: Reveals time estimation accuracy patterns

**3. Error metrics heatmaps**
- **Type**: Two matrix heatmaps
- **Inputs**:
  - Heatmap A: `errors_encountered` per participant-task
  - Heatmap B: severity-weighted score per participant-task (low=1, medium=2, high=4)
- **Rows**: Participants  
- **Columns**: Task types
- **Output**: Highlights hotspots by count and by impact

**4. Error category distribution (derived from grounded analysis)**
- **Type**: Stacked bar chart by task (separate charts per user type)
- **Input**: Categories emerging from axial coding mapped to error events
- **Output**: Shows which grounded categories dominate per task


**5. Grounded theory category TreeMap**
- **Type**: Hierarchical TreeMap visualization (separate for each user type)
- **Input**: Extract categories, frequencies and sentiment from `axial_codes.json` files
- **Rectangle size**: Category frequency (from `frequency` field in JSON)
- **Color coding**: Category sentiment (from `overall_sentiment` field: red=negative, yellow=neutral, green=positive)
- **Hierarchical nesting**: Core categories contain related subcategories
- **Interactive**: Click to drill down into category details and supporting quotes
- **Output**: Visual representation of user experience themes with relative importance and emotional impact

# SUS analysis

## SUS score calculation

The System Usability Scale (SUS) provides a standardized usability metric. Calculate SUS scores using the standard formula:

1. **Score processing**:
   - Odd items (1,3,5,7,9): Score = rating - 1
   - Even items (2,4,6,8,10): Score = 5 - rating
   
2. **Total calculation**: Sum all scores and multiply by 2.5
3. **Range**: Final scores range from 0-100

## SUS data processing

**Input files**: Extract ratings from `results/[endusers|technicians]/sus/[participant_id]_sus.md`

**Output structure**: `results/aggregated_analysis/sus/`
```
sus_individual_scores.json
sus_aggregated_report.json
sus_visualizations.png
```

Notes:
- `sus_individual_scores.json` includes individual participant SUS scores.
- `sus_aggregated_report.json` includes aggregated statistics per user type.

**Aggregated metrics by user type**:
- Mean SUS score
- Standard deviation
- Median score
- Score range (min-max)
- Individual participant scores

## SUS benchmarking

Reference benchmarks for interpretation:
- Below 68: Below average usability
- 68-80.3: Above average usability  
- Above 80.3: Excellent usability

## SUS visualization templates

**1. SUS Score Distribution by User Type**
- **Type**: Box plot comparison
- **Input**: Individual SUS scores grouped by user type
- **Output**: Shows score distribution, median, and outliers with benchmark thresholds

**2. Statistics Summary Table**
- **Type**: Text-based summary table
- **Input**: Aggregated statistics by user type
- **Output**: Count, mean, median, percentiles, and range for each user type

## SUS software usage

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

## Task analysis software usage

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

## Recruitment distribution software usage

**Purpose**: Analyze participant familiarity with HERITRACE and SHACL (for technicians) from written answer files, generating distribution statistics and visualizations.

**Running the Analysis**:
```bash
cd user_testing/analysis_software
uv run python recruitment_distribution.py
```

**Prerequisites**:
- Written answer files at `results/[endusers|technicians]/written_answers/`
- Dependencies installed via `uv sync`

**Input Data**:
- End users: HERITRACE familiarity question responses
- Technicians: HERITRACE and SHACL familiarity question responses

**Output Files** (in `results/aggregated_analysis/recruitment/`):
- `recruitment_distribution.json` - Detailed participant data and summary statistics
- `recruitment_distribution_combined.png` - Combined visualization with three distribution charts:
  - End users HERITRACE familiarity (top panel)
  - Technicians HERITRACE familiarity (bottom left)
  - Technicians SHACL familiarity (bottom right)

**Familiarity Levels**:
- HERITRACE: No experience, Usage knowledge, Mastered
- SHACL: No experience, Working knowledge, Mastered
