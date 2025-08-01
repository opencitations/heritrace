#!/usr/bin/env python3
"""
Grounded Theory Analysis script for HERITRACE user testing data
Follows proper grounded theory methodology: Open Coding -> Axial Coding -> Selective Coding
Uses local AI models for emergent coding discovery
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

import outlines
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


class GroundedAnalyzer:
    def __init__(self, model_name="mistralai/Ministral-8B-Instruct-2410"):
        """Initialize with local transformers model"""
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = None
        self.model = None
        
        self.open_codes = {}  # Initial codes discovered from data
        self.axial_codes = {}  # Grouped codes into categories  
        self.selective_codes = {}  # Core categories and relationships
        
        self.open_coding_complete = False
        self.axial_coding_complete = False
        self.selective_coding_complete = False
        
        # JSON schemas for structured output
        self.open_coding_schema = {
            "type": "object",
            "properties": {
                "codes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "pattern": "^[a-z_]+$"},
                            "explanation": {"type": "string"}
                        },
                        "required": ["code", "explanation"]
                    }
                }
            },
            "required": ["codes"]
        }
        
        self.axial_coding_schema = {
            "type": "object",
            "properties": {
                "categories": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string"},
                            "explanation": {"type": "string"},
                            "codes": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["category", "explanation", "codes"]
                    }
                }
            },
            "required": ["categories"]
        }
        
        self.selective_coding_schema = {
            "type": "object",
            "properties": {
                "core_category": {"type": "string"},
                "core_explanation": {"type": "string"},
                "relationships": {"type": "string"},
                "emerging_theory": {"type": "string"}
            },
            "required": ["core_category", "core_explanation", "relationships", "emerging_theory"]
        }
        
        self.outlines_model = None
        self.open_coding_generator = None
        self.axial_coding_generator = None
        self.selective_coding_generator = None
        
        self.grounded_theory_explanation = """
GROUNDED THEORY METHODOLOGY EXPLANATION:

Grounded Theory is a systematic research method that discovers theories and patterns from data rather than testing pre-existing theories. It has three phases:

1. OPEN CODING: Breaking down data into discrete concepts and labeling them with descriptive codes
2. AXIAL CODING: Grouping related codes into broader categories  
3. SELECTIVE CODING: Identifying core categories and relationships between them

IMPORTANT DEFINITIONS:

• EMERGING CONCEPTS: Ideas, themes, or patterns that naturally arise from reading the data, not predetermined categories
• DESCRIPTIVE CODES: Short labels (2-4 words with underscores) that capture the essence of what is happening in the data
• INDUCTIVE ANALYSIS: Letting the data speak rather than imposing external frameworks

CODING RULES:
- Use present tense verbs when possible (e.g., "user_struggling" not "user_struggled")
- Be specific but concise ("navigation_menu_confusion" not just "confusion")
- Focus on actions, emotions, and problems, not just topics
- Each code should represent ONE clear concept
- Use underscores to connect words (no spaces or hyphens)
"""
    
    def load_model(self):
        """Load the transformers model and tokenizer"""
        print(f"Loading {self.model_name} on {self.device}...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.bfloat16 if self.device == "cuda" else torch.float32,
            low_cpu_mem_usage=True
        ).to(self.device)
        self.outlines_model = outlines.models.transformers(
            self.model, self.tokenizer
        )
        self.open_coding_generator = outlines.generate.json(
            self.outlines_model, self.open_coding_schema
        )
        self.axial_coding_generator = outlines.generate.json(
            self.outlines_model, self.axial_coding_schema
        )
        self.selective_coding_generator = outlines.generate.json(
            self.outlines_model, self.selective_coding_schema
        )        
        print("Model loaded successfully!")
    
    def query_llm(self, prompt, context, generator):
        """Query local LLM via Outlines structured generation"""
        if not self.model or not self.tokenizer:
            self.load_model()
        
        full_prompt = f"{context}\n\n{prompt}"
        
        response = generator(full_prompt)
        return response
    
    def load_transcription(self, transcription_file):
        """Load transcription from JSON file"""
        with open(transcription_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data['transcription']
    
    def load_written_responses(self, responses_file):
        """Load written responses from markdown file"""
        with open(responses_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    
    def load_json_files_from_folder(self, folder_path):
        """Load all JSON files from a folder"""
        json_files = []
        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"Folder {folder_path} does not exist")
        
        for file_path in folder.glob('*.json'):
            json_files.append(file_path)
        
        if not json_files:
            raise ValueError(f"No JSON files found in {folder_path}")
        
        return json_files
    
    
    def open_coding_phase(self, data_text, data_type="transcription"):
        """Phase 1: Open Coding - discover initial codes from data"""
        print(f"Starting Open Coding phase for {data_type}...")
        
        if data_type == "transcription":
            data_specific_instructions = """
DATA TYPE: User testing transcription (think-aloud protocol)
FOCUS ON: Verbal expressions of confusion, success, frustration, discovery, and problem-solving attempts
LOOK FOR: What users say when they encounter problems, express emotions, or describe their thought process

SPECIFIC CODING TARGETS:
- Moments of confusion: When users express uncertainty or get lost
- Emotional reactions: Frustration, satisfaction, surprise, etc.
- Problem-solving strategies: How users try to overcome obstacles
- Feature interactions: How users discover and use interface elements
- Task progression: Steps in completing assigned tasks

EXAMPLE TRANSCRIPTION CODES:
- "navigation_menu_confusion" - User cannot find expected menu options
- "feature_discovery_positive" - User finds useful feature unexpectedly
- "error_recovery_attempting" - User trying to fix a mistake they made
- "task_completion_celebrating" - User expresses satisfaction at finishing task
- "interface_expectation_violated" - System behaves differently than user expected
"""
        else:
            data_specific_instructions = """
DATA TYPE: Written reflection responses (structured questionnaire answers)
FOCUS ON: Deliberate evaluations, feature assessments, and improvement suggestions
LOOK FOR: Explicit opinions about system effectiveness, specific feature mentions, and requested enhancements

SPECIFIC CODING TARGETS:
- Effectiveness assessments: How well the system supported their work
- Feature evaluations: Specific tools or interface elements mentioned
- Usability barriers: Explicitly stated problems or frustrations
- Workflow integration: How system fits into their normal work process
- Improvement suggestions: Specific features or changes requested

EXAMPLE WRITTEN RESPONSE CODES:
- "workflow_integration_seamless" - User reports system fits well into their process
- "feature_discovery_difficult" - User states features are hard to find
- "error_handling_inadequate" - User complains about poor error messages
- "automation_request_specific" - User asks for specific automated features
- "learning_curve_steep" - User mentions system is hard to learn
"""
        
        open_coding_prompt = f"""
You are an expert grounded theory researcher analyzing HERITRACE user testing data.

{self.grounded_theory_explanation}

{data_specific_instructions}

YOUR TASK:
Read through the data below and identify ALL emerging concepts. For each concept you identify, create a descriptive code following the rules above.

REQUIRED OUTPUT FORMAT:
CODE: explanation of what this code represents

EXAMPLE OUTPUT:
navigation_confusion: User cannot locate expected interface elements or menu options
feature_satisfaction: User expresses positive reaction to specific system functionality
task_abandonment: User gives up on completing assigned task due to obstacles

Now analyze this data:
"""
        
        open_coding_prompt += "\n\nIMPORTANT: Respond with a valid JSON object following this exact structure:\n{\"codes\": [{\"code\": \"example_code\", \"explanation\": \"what this represents\"}]}"
        
        response = self.query_llm(
            open_coding_prompt, 
            data_text, 
            generator=self.open_coding_generator
        )
        
        if not response:
            raise Exception("LLM analysis failed and no fallback available")
            
        codes = self._parse_json_open_coding(response)
        analysis = {
            'text': data_text,
            'data_type': data_type,
            'codes': codes,
            'raw_response': response
        }
        
        for code, explanation in codes.items():
            if code in self.open_codes:
                self.open_codes[code]['instances'].append(data_text[:200] + "...")
            else:
                self.open_codes[code] = {
                    'explanation': explanation,
                    'instances': [data_text[:200] + "..."],
                    'data_type': data_type
                }
        
        self.open_coding_complete = True
        print(f"Open Coding complete. Found {len(self.open_codes)} unique codes.")
        return analysis
    
    
    def _parse_json_open_coding(self, json_response):
        """Parse JSON response from structured generation"""
        codes = {}
        if 'codes' in json_response:
            for item in json_response['codes']:
                if 'code' in item and 'explanation' in item:
                    code = item['code'].lower().replace(' ', '_')
                    codes[code] = item['explanation']
        return codes
    
    
    def axial_coding_phase(self):
        """Phase 2: Axial Coding - group codes into categories"""
        print("Starting Axial Coding phase...")
        
        if not self.open_coding_complete:
            print("Error: Must complete Open Coding first")
            return
        
        axial_coding_prompt = f"""
You are an expert grounded theory researcher performing AXIAL CODING.

{self.grounded_theory_explanation}

AXIAL CODING PROCESS:
Axial coding groups related open codes into broader conceptual categories. This identifies the main themes and dimensions of the user experience.

CATEGORY CREATION RULES:
- Each category should represent a distinct aspect of user experience
- Categories should be mutually exclusive (codes shouldn't overlap between categories)
- Category names should be descriptive and capture the essence of grouped codes
- Each category needs 2-6 codes to be meaningful
- Focus on user experience dimensions like: interface usability, task completion, emotional responses, system functionality, workflow integration

EXAMPLE CATEGORIES:
- "interface_navigation_issues" - Problems finding and using interface elements
- "task_completion_barriers" - Obstacles preventing users from finishing tasks  
- "positive_feature_responses" - Successful interactions with system functionality
- "workflow_integration_challenges" - Difficulties fitting system into normal work processes

YOUR TASK:
Group the codes below into 4-8 meaningful categories that capture the main themes of HERITRACE user experience.

REQUIRED OUTPUT FORMAT:
CATEGORY: category_name
EXPLANATION: detailed explanation of what this category represents
CODES: code1, code2, code3, code4

Codes to group:
"""
        
        axial_coding_prompt += "\n\nIMPORTANT: Respond with a valid JSON object following this exact structure:\n{\"categories\": [{\"category\": \"name\", \"explanation\": \"description\", \"codes\": [\"code1\", \"code2\"]}]}"
        
        codes_list = "\n".join([f"- {code}: {data['explanation']}" 
                               for code, data in self.open_codes.items()])
        
        response = self.query_llm(
            axial_coding_prompt, 
            codes_list,
            generator=self.axial_coding_generator
        )
        
        if not response:
            raise Exception("LLM analysis failed and no fallback available")
            
        self.axial_codes = self._parse_json_axial_coding(response)
        
        self.axial_coding_complete = True
        print(f"Axial Coding complete. Found {len(self.axial_codes)} categories.")
    
    
    def _parse_json_axial_coding(self, json_response):
        """Parse JSON response from structured axial coding"""
        categories = {}
        if 'categories' in json_response:
            for item in json_response['categories']:
                if 'category' in item and 'explanation' in item and 'codes' in item:
                    category_name = item['category']
                    categories[category_name] = {
                        'explanation': item['explanation'],
                        'codes': item['codes']
                    }
        return categories
    
    
    def selective_coding_phase(self):
        """Phase 3: Selective Coding - identify core category and relationships"""
        print("Starting Selective Coding phase...")
        
        if not self.axial_coding_complete:
            print("Error: Must complete Axial Coding first")
            return
        
        selective_prompt = f"""
You are an expert grounded theory researcher performing SELECTIVE CODING.

{self.grounded_theory_explanation}

SELECTIVE CODING PROCESS:
Selective coding identifies the central phenomenon (core category) that ties all other categories together and explains the overall user experience pattern.

CORE CATEGORY CRITERIA:
- Appears frequently across all data
- Relates to and explains other categories
- Captures the main story of user experience with HERITRACE
- Can be used to explain user behavior patterns

RELATIONSHIP ANALYSIS:
Examine how categories influence each other:
- Causal relationships (A causes B)
- Conditional relationships (A happens when B is present)
- Sequential relationships (A leads to B over time)
- Contextual relationships (A affects how B is experienced)

THEORY DEVELOPMENT:
Create a cohesive explanation of:
- What is the central user experience with HERITRACE?
- Why do users behave the way they do?
- What factors determine success vs. failure?
- How do different aspects of the system interact?

YOUR TASK:
Analyze the categories below and develop a grounded theory of HERITRACE user experience.

REQUIRED OUTPUT FORMAT:
CORE_CATEGORY: [category name] - [detailed explanation of why this is central]
RELATIONSHIPS: [specific descriptions of how categories influence each other]
THEORY: [cohesive theory explaining the overall HERITRACE user experience phenomenon]

Categories to analyze:
"""
        
        selective_prompt += "\n\nIMPORTANT: Respond with a valid JSON object following this exact structure:\n{\"core_category\": \"name\", \"core_explanation\": \"why this is central\", \"relationships\": \"how categories relate\", \"emerging_theory\": \"cohesive explanation\"}"
        
        categories_text = "\n".join([f"{name}: {data['explanation']}\nCodes: {', '.join(data['codes'])}\n"
                                   for name, data in self.axial_codes.items()])
        
        response = self.query_llm(
            selective_prompt, 
            categories_text,
            generator=self.selective_coding_generator
        )
        
        if not response:
            raise Exception("LLM analysis failed and no fallback available")
            
        self.selective_codes = self._parse_json_selective_coding(response)
        
        self.selective_coding_complete = True
        print("Selective Coding complete.")
    
    
    def _parse_json_selective_coding(self, json_response):
        """Parse JSON response from structured selective coding"""
        result = {
            'core_category': json_response.get('core_category', ''),
            'core_explanation': json_response.get('core_explanation', ''),
            'relationships': json_response.get('relationships', ''),
            'emerging_theory': json_response.get('emerging_theory', '')
        }
        return result
    
    
    def analyze_data_files(self, input_path, participant_type="end_user", written_responses=None):
        """Complete grounded theory analysis pipeline for multiple files"""
        print(f"Starting Grounded Theory Analysis: {input_path}")
        
        analyses = []
        
        if os.path.isfile(input_path):
            json_files = [Path(input_path)]
        else:
            json_files = self.load_json_files_from_folder(input_path)
        
        for json_file in json_files:
            print(f"Analyzing transcription: {json_file.name}")
            transcription = self.load_transcription(json_file)
            open_coding_analysis = self.open_coding_phase(transcription, "transcription")
            analyses.append({
                'file': str(json_file),
                'type': 'transcription',
                'participant_type': participant_type,
                'data_length': len(transcription),
                'analysis': open_coding_analysis
            })
        
        if written_responses:
            for response_file in written_responses:
                if os.path.exists(response_file):
                    print(f"Analyzing written responses: {response_file}")
                    responses_content = self.load_written_responses(response_file)
                    open_coding_analysis = self.open_coding_phase(responses_content, "written_responses")
                    analyses.append({
                        'file': response_file,
                        'type': 'written_responses',
                        'participant_type': participant_type,
                        'data_length': len(responses_content),
                        'analysis': open_coding_analysis
                    })
        
        self.axial_coding_phase()
        self.selective_coding_phase()
        
        return {
            'input_path': input_path,
            'participant_type': participant_type,
            'total_files_analyzed': len(analyses),
            'file_analyses': analyses,
            'open_codes': self.open_codes,
            'axial_codes': self.axial_codes,
            'selective_codes': self.selective_codes
        }
    
    def generate_report(self, analysis_results, output_file):
        """Generate comprehensive grounded theory report"""
        report = {
            'analysis_timestamp': datetime.now().isoformat(),
            'methodology': 'Grounded Theory Analysis',
            'phases_completed': {
                'open_coding': self.open_coding_complete,
                'axial_coding': self.axial_coding_complete,
                'selective_coding': self.selective_coding_complete
            },
            'results': analysis_results,
            'summary': {
                'total_open_codes': len(self.open_codes),
                'total_categories': len(self.axial_codes),
                'core_theory': self.selective_codes.get('emerging_theory', 'Not identified')
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"Grounded Theory report saved to {output_file}")
        return report
    
    def print_summary(self):
        """Print analysis summary"""
        print("\n" + "="*60)
        print("HERITRACE GROUNDED THEORY ANALYSIS SUMMARY")
        print("="*60)
        
        print(f"\nOPEN CODING RESULTS ({len(self.open_codes)} codes):")
        for code, data in list(self.open_codes.items())[:10]:  # Top 10
            count = len(data['instances'])
            print(f"  • {code}: {data['explanation']} ({count} instances)")
        
        if len(self.open_codes) > 10:
            print(f"  ... and {len(self.open_codes) - 10} more codes")
        
        print(f"\nAXIAL CODING RESULTS ({len(self.axial_codes)} categories):")
        for category, data in self.axial_codes.items():
            print(f"  • {category}: {data['explanation']}")
            print(f"    Codes: {', '.join(data['codes'][:5])}")
            if len(data['codes']) > 5:
                print(f"    ... and {len(data['codes']) - 5} more")
        
        if self.selective_codes:
            print(f"\nSELECTIVE CODING RESULTS:")
            print(f"  Core Category: {self.selective_codes.get('core_category', 'Not identified')}")
            print(f"  Emerging Theory: {self.selective_codes.get('emerging_theory', 'Not identified')}")

def main():
    parser = argparse.ArgumentParser(description='Grounded Theory Analysis for HERITRACE user testing')
    parser.add_argument('input_path', help='Path to transcription JSON file or folder containing JSON files')
    parser.add_argument('--participant-type', choices=['technician', 'end_user'], 
                       default='end_user', help='Type of participant')
    parser.add_argument('--written-responses', nargs='*', 
                       help='Paths to written response files (markdown format)')
    parser.add_argument('--output-dir', default='grounded_analysis_results', 
                       help='Output directory for results')
    parser.add_argument('--model-name', default='mistralai/Mistral-7B-Instruct-v0.3',
                       help='HuggingFace model name to use (recommended: mistralai/Mistral-7B-Instruct-v0.3, microsoft/Phi-3.5-mini-instruct, Qwen/Qwen2.5-Coder-7B-Instruct)')
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    analyzer = GroundedAnalyzer(args.model_name)
    
    results = analyzer.analyze_data_files(
        args.input_path, 
        args.participant_type, 
        args.written_responses
    )
    
    report_file = output_dir / 'grounded_theory_report.json'
    analyzer.generate_report(results, report_file)
    
    analyzer.print_summary()

if __name__ == "__main__":
    main()