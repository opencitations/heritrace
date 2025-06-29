# Analysis Framework

## Overview

This framework transforms user testing data into actionable insights for HERITRACE system improvement and user experience optimization. The analysis is designed for data collected from self-guided testing sessions with screen and voice recordings.

## Data Sources

### Technician Testing Data (4-6 participants)
- **Screen+voice recordings** of 60-minute sessions
- **Task completion data** for 3 specific configuration tasks
- **Modified SHACL schema files** and **display rules files**
- **SUS questionnaire responses**
- **Structured reflection responses** to 4 specific questions

### End User Testing Data (8-12 participants)
- **Screen+voice recordings** of 60-minute sessions
- **Task completion data** for 5 specific metadata management tasks
- **SUS questionnaire responses**
- **Structured reflection responses** to 4 specific questions

## Analysis Approach

**Mixed-Methods Integration**: Quantitative (statistical analysis of completion metrics), Qualitative (grounded theory analysis of recordings), Triangulation (cross-validation across data sources and participant types)

## Task Analysis

### Technician Task Completion Metrics
**Input**: Completion data for 3 specific configuration tasks

**Specific Tasks**:
1. **Add Abstract Support** (15 min): dcterms:abstract property with validation rules
2. **Add Keywords Support** (10 min): prism:keyword property configuration  
3. **Configure Display Rules** (10 min): Interface display configuration

**Calculations**:
```python
# Task-Specific Success Rates
task_abstract_completed = count(participants with abstract_task="complete")
task_abstract_attempted = count(technician_participants)
abstract_success_rate = (task_abstract_completed / task_abstract_attempted) * 100

task_keywords_completed = count(participants with keywords_task="complete")
keywords_success_rate = (task_keywords_completed / task_abstract_attempted) * 100

task_display_completed = count(participants with display_task="complete")
display_success_rate = (task_display_completed / task_abstract_attempted) * 100

# Overall Technician Completion
technician_overall = (abstract_success_rate + keywords_success_rate + display_success_rate) / 3
```

**Success Criteria**: Based on deliverable files (modified SHACL schemas and display rules)

### End User Task Completion Metrics
**Input**: Completion data for 5 specific metadata management tasks

**Specific Tasks**:
1. **Create New Publication Record** (15 min) - Target: 85% completion
2. **Add Missing Information** (10 min) - Target: 90% completion
3. **Correct Publication Error** (12 min) - Target: 75% completion
4. **Identify and Merge Duplicate Author** (15 min) - Target: 70% completion
5. **Restore Previous Version** (8 min) - Target: 80% completion

**Calculations**:
```python
# Individual Task Success Rates
task_rates = {}
target_rates = {"creation": 85, "addition": 90, "correction": 75, "merge": 70, "restore": 80}

for task in ["creation", "addition", "correction", "merge", "restore"]:
    completed = count(participants with task_status="complete")
    attempted = count(end_user_participants)
    task_rates[task] = (completed / attempted) * 100
    
    # Compare to target
    target_achievement = task_rates[task] / target_rates[task] * 100

# Overall End User Performance
end_user_overall = sum(task_rates.values()) / len(task_rates)
```

**Quality Classification**: Based on specific success/failure criteria defined for each task

**Output**: Task-specific completion rates, target achievement analysis, user type comparison

### Time and Efficiency Analysis
**Input**: Timestamp data from session recordings

**Calculations**:
```python
# Basic Time Statistics
task_times = [end_time - start_time for each task]
mean_time = sum(task_times) / len(task_times)
median_time = sorted(task_times)[len(task_times)//2]

# Learning Curve Analysis (within same session)
first_task_times = [time_for_task_1 for each participant]
last_task_times = [time_for_final_task for each participant]
within_session_improvement = (mean(first_task_times) - mean(last_task_times)) / mean(first_task_times) * 100

# Experience Level Comparison
novice_times = [task_times for participants with experience_level="novice"]
expert_times = [task_times for participants with experience_level="expert"]
experience_advantage = (mean(novice_times) - mean(expert_times)) / mean(novice_times) * 100

# Error Recovery Time
error_start = timestamp_when_error_occurred
error_resolved = timestamp_when_user_continued
recovery_time = error_resolved - error_start
```

**Output**: Time statistics by user type, learning curves, efficiency metrics

### Error Analysis Framework
**Input**: Error logs from session observations

**Error Classification System**:
```python
# Categorize each error
error_types = {
    "navigation": ["wrong_menu", "lost_orientation", "back_button"],
    "input": ["wrong_format", "typo", "invalid_data"],
    "conceptual": ["misunderstood_system", "wrong_approach"],
    "workflow": ["skipped_step", "wrong_sequence"]
}

# Calculate error rates
navigation_errors = count(errors where type="navigation")
total_errors = count(all_errors)
navigation_error_rate = (navigation_errors / total_errors) * 100

# Impact scoring (1=minor, 2=moderate, 3=critical)
impact_score = sum([error.impact_level for error in errors]) / len(errors)
```

**Output**: Error frequency by type, impact distribution, critical error identification

## Usability Analysis

### System Usability Scale (SUS) Analysis
**Input**: [SUS questionnaire responses](questionnaires/sus_questionnaire.md)

**Calculations**:
```
# Individual SUS Score
odd_questions = [Q1, Q3, Q5, Q7, Q9]  # responses 1-5
even_questions = [Q2, Q4, Q6, Q8, Q10]  # responses 1-5

odd_scores = sum([(response - 1) for response in odd_questions])
even_scores = sum([(5 - response) for response in even_questions])
sus_score = (odd_scores + even_scores) * 2.5

# Group Analysis
group_mean = sum(all_sus_scores) / count(participants)
group_median = median(all_sus_scores)
std_deviation = stdev(all_sus_scores)
```

**Output**: Individual scores (0-100), group statistics, benchmark comparison (target: >65, optimal: >70)

## Analytical Methods

### Quantitative Techniques
- **Descriptive Statistics**: Central tendency, variability, distribution analysis for task completion rates and SUS scores
- **Comparative Analysis**: Completion rate comparisons between user types and against target benchmarks

### Qualitative Techniques
**Grounded Theory Analysis** of screen+voice recordings:

**Structured Reflection Analysis**:
```python
# Analysis of 4 specific reflection questions for both user types

# Technician Reflection Questions:
tech_questions = [
    "How effectively did HERITRACE support you in these configuration tasks?",
    "What were the most useful features that helped you accomplish your work?", 
    "What were the main weaknesses or frustrations you encountered?",
    "What additional features would have made these tasks easier?"
]

# End User Reflection Questions:
user_questions = [
    "How effectively did HERITRACE support you in these metadata management tasks?",
    "What were the most useful features for your bibliographic workflow?",
    "What were the main weaknesses or frustrating aspects you encountered?", 
    "What additional features would have made this more useful for your academic work?"
]

# Coding Structure
reflection_codes = {
    "effectiveness": ["task_support", "workflow_integration", "feature_adequacy"],
    "useful_features": ["interface_elements", "functionality", "workflow_helpers"],
    "weaknesses": ["usability_barriers", "missing_features", "confusion_points"],
    "improvement_needs": ["feature_requests", "workflow_gaps", "enhancement_priorities"]
}
```

**Open Coding from Think-Aloud Protocols**:

**Examples of HERITRACE verbalizations and corresponding codes**:

**Technicians during configuration**:
- *"I don't see where to add dcterms:abstract..."* → Code: `interface_navigation_confusion`
- *"I expected a wizard for SHACL configuration..."* → Code: `configuration_expectation_mismatch` 
- *"The file won't save, let me try..."* → Code: `technical_error_recovery`
- *"Great, the display rules work immediately"* → Code: `configuration_success_moment`

**End users during metadata management**:
- *"Where do I click to create a new article?"* → Code: `workflow_entry_confusion`
- *"This ORCID links automatically!"* → Code: `feature_discovery_positive`
- *"I entered the wrong volume, how do I modify it?"* → Code: `correction_workflow_uncertainty`
- *"The merge process is too complicated..."* → Code: `task_complexity_frustration`

**Axial Coding: Grouping by themes**:
```python
heritrace_concepts = {
    "sistema_navigation": [
        "interface_navigation_confusion", "workflow_entry_confusion", 
        "menu_discovery_difficulty"
    ],
    "technical_configuration": [
        "configuration_expectation_mismatch", "technical_error_recovery",
        "shacl_comprehension_difficulty"
    ],
    "metadata_workflow": [
        "correction_workflow_uncertainty", "task_complexity_frustration",
        "workflow_adaptation_success"
    ],
    "feature_satisfaction": [
        "configuration_success_moment", "feature_discovery_positive",
        "automatic_linking_appreciation"
    ]
}
```

### Screen Recording and Interaction Analysis
**Input**: Self-recorded screen+voice recordings from participants

**Behavioral Coding Framework**:
```python
# Code categories for screen recording analysis
behavioral_codes = {
    "navigation_patterns": ["direct_path", "exploration", "backtracking", "confusion"],
    "error_recovery": ["immediate_recognition", "delayed_recognition", "help_seeking"],
    "task_strategies": ["systematic_approach", "trial_and_error", "feature_discovery"],
    "verbalization_quality": ["continuous_thinking", "sparse_comments", "rich_explanation"]
}

# Time-based analysis
interaction_timestamps = [
    {"action": "click_menu", "time": "00:05:23", "context": "looking_for_create_option"},
    {"action": "verbalize_confusion", "time": "00:05:45", "content": "I'm not sure where..."}
]
```

**Integration with Reflection Data**: Compare observed behavior with participant statements about experience

## Converting Qualitative Insights to Quantitative Metrics

### From Grounded Theory Codes to Metrics

**Step 1: Code Frequency Analysis**
```python
# Count occurrences of each code across all participants
code_frequencies = {
    "interface_navigation_confusion": 15,  # appeared 15 times across all recordings
    "configuration_expectation_mismatch": 8,
    "workflow_entry_confusion": 22,
    "feature_discovery_positive": 12,
    "task_complexity_frustration": 18,
    "configuration_success_moment": 6
}

# Calculate percentages
total_codes = sum(code_frequencies.values())
code_percentages = {code: (count/total_codes)*100 for code, count in code_frequencies.items()}
```

**Step 2: Theme-Level Metrics**
```python
# Aggregate codes into theme scores
theme_scores = {
    "system_navigation": code_frequencies["interface_navigation_confusion"] + 
                         code_frequencies["workflow_entry_confusion"],  # = 37
    "technical_configuration": code_frequencies["configuration_expectation_mismatch"] + 
                              code_frequencies["configuration_success_moment"],  # = 14
    "feature_satisfaction": code_frequencies["feature_discovery_positive"]  # = 12
}

# Calculate problem severity index (higher = more problematic)
problem_severity = {
    "navigation_issues": theme_scores["sistema_navigation"] / total_participants,  # per participant
    "configuration_barriers": theme_scores["technical_configuration"] / technician_participants
}
```

**Step 3: User Type Comparison Metrics**
```python
# Compare code frequencies between user types
technician_codes = {"configuration_expectation_mismatch": 8, "technical_error_recovery": 5}
end_user_codes = {"workflow_entry_confusion": 22, "task_complexity_frustration": 18}

# Calculate relative problem rates
tech_problem_rate = sum(technician_codes.values()) / technician_participants
user_problem_rate = sum(end_user_codes.values()) / end_user_participants

comparison_ratio = user_problem_rate / tech_problem_rate  # Who struggles more?
```

### Visualization Generation

**1. Problem Frequency Charts**
```python
# Bar chart: Most common issues
import matplotlib.pyplot as plt

issues = list(code_percentages.keys())
percentages = list(code_percentages.values())

plt.figure(figsize=(12, 6))
plt.bar(issues, percentages, color=['red' if 'confusion' in issue or 'frustration' in issue 
                                   else 'green' for issue in issues])
plt.title('HERITRACE Usability Issues - Frequency Analysis')
plt.xlabel('Issue Type')
plt.ylabel('Percentage of Total Verbalizations')
plt.xticks(rotation=45)
```

**2. User Type Comparison Dashboard**
```python
# Side-by-side comparison
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

# Technician issues
tech_issues = ['Configuration Problems', 'SHACL Difficulties', 'File Management']
tech_values = [8, 5, 3]
ax1.pie(tech_values, labels=tech_issues, autopct='%1.1f%%')
ax1.set_title('Technician Pain Points')

# End user issues  
user_issues = ['Navigation Confusion', 'Workflow Uncertainty', 'Task Complexity']
user_values = [22, 15, 18]
ax2.pie(user_values, labels=user_issues, autopct='%1.1f%%')
ax2.set_title('End User Pain Points')
```

**3. Task Performance vs. Verbalization Correlation**
```python
# Correlation between negative verbalizations and task completion
task_completion_rates = [85, 90, 75, 70, 80]  # From quantitative analysis
negative_verbalization_counts = [3, 1, 8, 12, 5]  # From qualitative analysis

plt.scatter(negative_verbalization_counts, task_completion_rates)
plt.xlabel('Negative Verbalizations Count')
plt.ylabel('Task Completion Rate (%)')
plt.title('Relationship: User Frustration vs. Task Success')

# Add correlation coefficient
correlation = numpy.corrcoef(negative_verbalization_counts, task_completion_rates)[0,1]
plt.text(0.05, 0.95, f'Correlation: {correlation:.2f}', transform=plt.gca().transAxes)
```

**4. Timeline Analysis Visualization**
```python
# Show when problems occur during tasks
time_segments = ['0-5min', '5-10min', '10-15min', '15-20min']
confusion_incidents = [12, 18, 8, 4]  # Peak confusion in middle of tasks

plt.plot(time_segments, confusion_incidents, marker='o', linewidth=2)
plt.title('User Confusion Over Time - Task Progression')
plt.xlabel('Time Segment')
plt.ylabel('Number of Confusion Incidents')
plt.grid(True, alpha=0.3)
```

### Quantitative Insight Metrics

**Problem Priority Index**
```python
# Combine frequency + severity + user impact
problem_priority = {
    "navigation_confusion": {
        "frequency": 37,  # how often it occurs
        "severity": 3,    # impact level (1-5)
        "affected_users": 8,  # how many users experienced it
        "priority_score": (37 * 3 * 8) / 100  # normalized score
    }
}

# Rank problems by priority score for development roadmap
sorted_priorities = sorted(problem_priority.items(), 
                          key=lambda x: x[1]['priority_score'], reverse=True)
```

**Feature Success Rate**
```python
# Convert positive verbalizations to success metrics
positive_mentions = {
    "orcid_integration": 12,
    "automatic_validation": 8,
    "version_control": 6
}

total_participants = 14
feature_satisfaction_rate = {
    feature: (mentions/total_participants)*100 
    for feature, mentions in positive_mentions.items()
}
```

**Workflow Efficiency Indicators**
```python
# Time between confusion and resolution
confusion_resolution_times = [30, 45, 120, 90, 60]  # seconds from recordings
average_confusion_time = sum(confusion_resolution_times) / len(confusion_resolution_times)

efficiency_score = 100 - (average_confusion_time / 10)  # lower confusion time = higher efficiency
```

## HERITRACE Development Priorities

**Input**: Quantified issues from grounded theory analysis + task completion data

**Process**: 
```python
# Rank HERITRACE issues by frequency and impact
heritrace_issues = {
    "navigation_confusion": {"frequency": 37, "blocks_task_completion": True},
    "configuration_complexity": {"frequency": 14, "blocks_task_completion": True}, 
    "merge_workflow_difficulty": {"frequency": 12, "blocks_task_completion": False}
}

# Priority = frequency × completion_impact
priorities = {}
for issue, data in heritrace_issues.items():
    impact_multiplier = 2 if data["blocks_task_completion"] else 1
    priorities[issue] = data["frequency"] * impact_multiplier
```

**Output**: Ranked development roadmap for HERITRACE interface improvements

## Success Criteria

### Technician Testing Success Criteria
- **Technical completion**: Successfully adds abstract and keyword support with working display rules
- **Deliverable quality**: Modified SHACL schema and display rules files validate and function correctly
- **Usability threshold**: Average SUS score ≥ 65 for acceptable usability
- **Verbalization richness**: Complete think-aloud data capturing configuration decision-making

### End User Testing Success Criteria  
- **Task completion targets**:
  - Create Publication Record: ≥85% completion rate
  - Add Missing Information: ≥90% completion rate
  - Correct Publication Error: ≥75% completion rate
  - Merge Duplicate Author: ≥70% completion rate
  - Restore Previous Version: ≥80% completion rate
- **Usability threshold**: Average SUS score ≥ 65 for acceptable usability
- **Workflow relevance**: Users can articulate system integration with academic work
- **Verbalization richness**: Complete think-aloud data capturing metadata workflow expectations

### Overall Study Success
- **Recording completeness**: All participants provide complete screen+voice recordings
- **Reflection completion**: All participants complete structured 4-question reflection
- **SUS response rate**: 100% SUS questionnaire completion
- **Data sufficiency**: Adequate data for grounded theory analysis (concept saturation)

This framework provides a systematic approach to transforming user testing data into actionable insights that drive meaningful improvements to HERITRACE's usability, functionality, and user experience. 