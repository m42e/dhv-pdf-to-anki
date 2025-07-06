#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "mistralai",
# ]
# ///
"""
Script to find questions with "abbildung" and multiple numbers.
This script searches through questions.json to find:
1. Questions that contain "abbildung" in the question text
2. Questions that have multiple numbers in the question text
3. Questions that reference multiple figure numbers in the abbildung field
4. Generate individual questions for each numbered point using Mistral AI
"""

import json
import re
import os
import tempfile
from typing import List, Dict, Any, Optional
from mistralai import Mistral # type: ignore


def load_questions(file_path: str) -> List[Dict[str, Any]]:
    """Load questions from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def has_abbildung_in_text(question_text: str) -> bool:
    """Check if question text contains 'abbildung' (case insensitive)."""
    return 'abbildung' in question_text.lower()


def extract_numbers_from_text(text: str) -> List[str]:
    """Extract all numbers from text."""
    # Find all sequences of digits
    numbers = re.findall(r'(?<=[ ,.])[0-9A-F](?=[ ,.])', text)
    return numbers


def has_multiple_numbers(text: str) -> bool:
    """Check if text contains multiple numbers."""
    numbers = extract_numbers_from_text(text)
    return len(numbers) > 1


def has_multiple_figures(abbildung_field: str) -> bool:
    """Check if abbildung field references multiple figures."""
    if not abbildung_field:
        return False
    
    # Check for patterns like "12,13", "12-13", "12 13", "12/13", etc.
    # Also check for multiple separate numbers
    numbers = extract_numbers_from_text(abbildung_field)
    return len(numbers) > 1


def analyze_questions(questions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Analyze questions and categorize them based on criteria."""
    results = {
        'abbildung_in_text': [],
        'multiple_numbers_in_question': [],
        'multiple_figures_referenced': [],
        'all_criteria': []  # Questions that meet all criteria
    }
    
    for question in questions:
        question_text = question.get('question', '')
        abbildung_field = question.get('abbildung', '')
        
        # Check if question contains "abbildung"
        has_abbildung = has_abbildung_in_text(question_text)
        
        # Check if question has multiple numbers
        has_mult_numbers = has_multiple_numbers(question_text)
        
        # Check if references multiple figures
        has_mult_figures = has_multiple_figures(abbildung_field)
        
        if has_abbildung:
            results['abbildung_in_text'].append(question)
        
        if has_mult_numbers:
            results['multiple_numbers_in_question'].append(question)
        
        if has_mult_figures:
            results['multiple_figures_referenced'].append(question)
        
        # Questions that meet all criteria
        if has_abbildung and has_mult_numbers:
            results['all_criteria'].append(question)
    
    return results


def print_question_summary(question: Dict[str, Any]) -> None:
    """Print a summary of a question."""
    print(f"ID: {question.get('id', 'N/A')}")
    print(f"Section: {question.get('section', 'N/A')}")
    print(f"Subsection: {question.get('subsection', 'N/A')}")
    print(f"Question: {question.get('question', 'N/A')}")
    print(f"Abbildung: {question.get('abbildung', 'N/A')}")
    
    # Highlight numbers in question
    question_text = question.get('question', '')
    numbers = extract_numbers_from_text(question_text)
    if numbers:
        print(f"Numbers found in question: {', '.join(numbers)}")
    
    print("-" * 80)


def extract_answer_for_number(answers_dict: Dict[str, str], correct_answer: str, target_number: str) -> str:
    """Extract the specific answer for a given number from the correct answer choice."""
    if not answers_dict or not correct_answer:
        return ""
    
    correct_text = answers_dict.get(correct_answer, "")
    if not correct_text:
        return ""
    
    # Parse the answer text for number = answer patterns
    # Example: "1 = Obersegel 2 = Untersegel" or "3 = Stabilisator 4 = Bremsspinne 5 = Hauptbremsleine"
    pattern = rf'{target_number}\s*=\s*([^0-9]+?)(?=\s*[0-9]\s*=|$)'
    match = re.search(pattern, correct_text, re.IGNORECASE)
    
    if match:
        return match.group(1).strip()
    
    return ""


def call_mistral_api(prompt: str, api_key: Optional[str] = None) -> str:
    """Call Mistral AI API to generate content."""
    if not api_key:
        api_key = os.getenv('MISTRAL_API_KEY')
    
    if not api_key:
        print("Warning: No Mistral API key found. Set MISTRAL_API_KEY environment variable or provide api_key parameter.")
        return ""
    
    try:
        client = Mistral(api_key=api_key)
        
        chat_response = client.chat.complete(
            model="mistral-small-2503",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        response_string = chat_response.choices[0].message.content
        if response_string is None:
            print("Warning: Mistral API returned None for response content.")
            return ""
        if isinstance(response_string, str):
            return response_string.strip()
        else:
            # Handle ContentChunk - extract text from different chunk types
            text_content = ""
            for chunk in response_string:
                match chunk.type:
                    case "text":
                        text_content += chunk.text
                    case "document_url":
                        if hasattr(chunk, 'document_name'):
                            text_content += f"[Document: {chunk.document_name}]"
                        else:
                            text_content += "[Document URL: {chunk.document_url}]"
            return text_content.strip()
        
        return chat_response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"Error calling Mistral API: {e}")
        return ""


def generate_single_question(original_question: Dict[str, Any], target_number: str, correct_answer: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """Generate a single question for a specific numbered point using Mistral AI."""
    
    # Create prompt for Mistral
    prompt = f"""
Based on the following paragliding exam question, generate a new question that asks specifically about point {target_number}.

Original question: {original_question.get('question', '')}
Section: {original_question.get('section', '')}
Subsection: {original_question.get('subsection', '')}
Figure number: {original_question.get('abbildung', '')}
Correct answer for point {target_number}: {correct_answer}

Generate:
1. A new question asking specifically "Was bezeichnet Punkt {target_number} in der Abbildung?" 
2. Four answer choices (A, B, C, D) where one is correct ({correct_answer}) and three are plausible but incorrect alternatives related to paragliding equipment/terminology
3. Return ONLY a JSON object with this structure:
{{
  "question": "Was bezeichnet Punkt {target_number} in der Abbildung?",
  "answers": {{
    "A": "option 1",
    "B": "option 2", 
    "C": "option 3",
    "D": "option 4"
  }},
  "correct": ["X"]
}}

Make sure the correct answer ({correct_answer}) is randomly placed among the options A-D.
Use German language and paragliding terminology. Answer in the exact JSON format without any additional text or markdown.
"""

    mistral_response = call_mistral_api(prompt, api_key)
    
    if not mistral_response:
        # Fallback: create a simple question manually
        return {
            "section": original_question.get('section', ''),
            "subsection": original_question.get('subsection', ''),
            "question": f"Was bezeichnet Punkt {target_number} in der Abbildung?",
            "answers": {
                "A": correct_answer,
                "B": "Andere Komponente",
                "C": "Unbekanntes Teil",
                "D": "Sonstiges Element"
            },
            "correct": ["A"],
            "abbildung": original_question.get('abbildung', ''),
            "section_id": original_question.get('section_id', ''),
            "subsection_id": original_question.get('subsection_id', ''),
            "page": original_question.get('page', ''),
            "pdf_page_number": original_question.get('pdf_page_number', ''),
        }
    
    try:
        # Parse the JSON response from Mistral
        # First, try to extract JSON from the response if it's wrapped in markdown or extra text
        response_text = mistral_response.strip()
        
        # Look for JSON content between ```json and ``` or just plain JSON
        import re
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(1)
        elif response_text.startswith('```') and response_text.endswith('```'):
            # Remove markdown code blocks
            response_text = response_text.strip('`').strip()
            if response_text.startswith('json'):
                response_text = response_text[4:].strip()
        
        generated_data = json.loads(response_text)
        
        # Add the original question metadata
        generated_data.update({
            "section": original_question.get('section', ''),
            "subsection": original_question.get('subsection', ''),
            "abbildung": original_question.get('abbildung', ''),
            "section_id": original_question.get('section_id', ''),
            "subsection_id": original_question.get('subsection_id', '')
        })
        
        return generated_data
        
    except json.JSONDecodeError as e:
        print(f"Failed to parse Mistral response for question {original_question.get('id', 'unknown')}, number {target_number}")
        print(f"Response was: {mistral_response[:200]}...")
        print(f"JSON error: {e}")
        # Fallback to manual generation
        return {
            "section": original_question.get('section', ''),
            "subsection": original_question.get('subsection', ''),
            "question": f"Was bezeichnet Punkt {target_number} in der Abbildung?",
            "answers": {
                "A": correct_answer,
                "B": "Andere Komponente",
                "C": "Unbekanntes Teil", 
                "D": "Sonstiges Element"
            },
            "correct": ["A"],
            "abbildung": original_question.get('abbildung', ''),
            "section_id": original_question.get('section_id', ''),
            "subsection_id": original_question.get('subsection_id', ''),
            "page": original_question.get('page', ''),
            "pdf_page_number": original_question.get('pdf_page_number', ''),
        }


def load_existing_extended_questions(file_path: str) -> Dict[str, Dict[str, Any]]:
    """Load existing extended questions from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
            # Return as dict with ID as key for quick lookup
            return {q.get('id', ''): q for q in questions}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_extended_question(question: Dict[str, Any], file_path: str):
    """Save a single extended question to file, appending to existing questions."""
    try:
        # Load existing questions
        existing_questions = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_questions = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            existing_questions = []
        
        # Add new question
        existing_questions.append(question)
        
        # Save back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_questions, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"Error saving question to {file_path}: {e}")


def generate_extended_questions(target_questions: List[Dict[str, Any]], output_folder: Optional[str] = None, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """Generate individual questions for each numbered point in the target questions."""
    # Set up output file path
    if output_folder:
        os.makedirs(output_folder, exist_ok=True)
        extended_file = os.path.join(output_folder, 'extended_questions.json')
    else:
        # Use temporary directory
        temp_dir = tempfile.gettempdir()
        extended_file = os.path.join(temp_dir, 'extended_questions.json')
    
    # Load existing extended questions to avoid duplicates
    existing_questions = load_existing_extended_questions(extended_file)
    extended_questions = list(existing_questions.values())
    
    print(f"Found {len(existing_questions)} existing extended questions")
    
    for question in target_questions:
        original_id = f'{question.get('id', '')}{question.get('section_id', '')}{question.get('subsection_id', '')}'
        question_text = question.get('question', '')
        answers = question.get('answers', {})
        correct_choices = question.get('correct', [])
        
        if not correct_choices:
            continue
            
        correct_choice = correct_choices[0]
        
        # Extract numbers from question text
        numbers = extract_numbers_from_text(question_text)
        
        print(f"Processing question ID {original_id} with {len(numbers)} numbers: {numbers}")
        
        for i, number in enumerate(numbers, 1):
            # Generate new ID: 99<referencedid>000+questionid
            new_id = f"99{original_id}000{i}"
            
            # Check if this question already exists
            if new_id in existing_questions:
                print(f"  Skipping question for number {number} (ID: {new_id}) - already exists")
                continue
            
            # Extract the correct answer for this specific number
            correct_answer = extract_answer_for_number(answers, correct_choice, number)
            
            if correct_answer:
                print(f"  Generating question for number {number}: {correct_answer}")
                
                # Generate new question using Mistral AI
                new_question = generate_single_question(question, number, correct_answer, api_key)
                
                new_question['id'] = new_id
                new_question['original_id'] = original_id
                new_question['target_number'] = number
                
                # Save immediately to file
                save_extended_question(new_question, extended_file)
                
                # Add to our list for return
                extended_questions.append(new_question)
                existing_questions[new_id] = new_question
                
                print(f"  ✓ Saved question ID: {new_id}")
            else:
                print(f"  Could not extract answer for number {number}")
    
    return extended_questions


def process_questions(questions_file: str, output_folder: Optional[str] = None, mistral_api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Process questions and generate extended questions.
    
    Args:
        questions_file: Path to the JSON file containing questions
        output_folder: Directory to save extended questions (None for temp directory)
        mistral_api_key: Mistral AI API key (None to use environment variable)
    
    Returns:
        List of generated extended questions
    """
    try:
        # Load questions
        print(f"Loading questions from {questions_file}...")
        questions = load_questions(questions_file)
        print(f"Loaded {len(questions)} questions.")
        
        # Analyze questions
        print("\nAnalyzing questions...")
        results = analyze_questions(questions)
        
        # Print analysis results
        print("\n" + "="*80)
        print("ANALYSIS RESULTS")
        print("="*80)
        
        print(f"\n1. Questions containing 'abbildung' in text: {len(results['abbildung_in_text'])}")
        print(f"2. Questions with multiple numbers: {len(results['multiple_numbers_in_question'])}")
        print(f"3. Questions referencing multiple figures: {len(results['multiple_figures_referenced'])}")
        print(f"4. Questions with 'abbildung' AND multiple numbers: {len(results['all_criteria'])}")
        
        # Generate extended questions if criteria are met
        extended_questions = []
        if results['all_criteria']:
            print("\n" + "="*80)
            print("GENERATING EXTENDED QUESTIONS")
            print("="*80)
            
            # Check API key availability
            api_key = mistral_api_key or os.getenv('MISTRAL_API_KEY')
            if not api_key:
                print("Warning: No Mistral API key provided or found in environment.")
                print("Extended questions will use fallback generation without AI assistance.")
            else:
                print("Using Mistral AI to generate enhanced questions...")
            
            extended_questions = generate_extended_questions(
                results['all_criteria'], 
                output_folder=output_folder, 
                api_key=mistral_api_key
            )
            
            print(f"\nGenerated {len(extended_questions)} extended questions.")
            
        return extended_questions
        
    except FileNotFoundError:
        print(f"Error: Could not find {questions_file}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {questions_file}: {e}")
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extend paragliding exam questions with individual numbered questions')
    parser.add_argument('--questions', '-q', default='questions.json', 
                       help='Path to questions JSON file (default: questions.json)')
    parser.add_argument('--output', '-o', default=None,
                       help='Output folder for extended questions (default: temp directory)')
    parser.add_argument('--api-key', '-k', default=None,
                       help='Mistral AI API key (default: use MISTRAL_API_KEY env var)')
    
    args = parser.parse_args()
    
    # Process questions
    extended_questions = process_questions(
        questions_file=args.questions,
        output_folder=args.output,
        mistral_api_key=args.api_key
    )
    
    if extended_questions:
        print(f"\n✓ Successfully generated {len(extended_questions)} extended questions.")
        
        # Show a few examples
        print("\nExample generated questions:")
        for i, question in enumerate(extended_questions[:3]):
            print(f"\nExtended Question {i+1}:")
            print(f"ID: {question.get('id', 'N/A')}")
            print(f"Question: {question.get('question', 'N/A')}")
            print(f"Target Number: {question.get('target_number', 'N/A')}")
    else:
        print("\nNo extended questions were generated.")


def main_legacy():
    """Legacy main function - kept for backward compatibility."""
    questions_file = 'questions.json'
    
    try:
        # Load questions
        print(f"Loading questions from {questions_file}...")
        questions = load_questions(questions_file)
        print(f"Loaded {len(questions)} questions.")
        
        # Analyze questions
        print("\nAnalyzing questions...")
        results = analyze_questions(questions)
        
        # Print results
        print("\n" + "="*80)
        print("ANALYSIS RESULTS")
        print("="*80)
        
        print(f"\n1. Questions containing 'abbildung' in text: {len(results['abbildung_in_text'])}")
        print(f"2. Questions with multiple numbers: {len(results['multiple_numbers_in_question'])}")
        print(f"3. Questions referencing multiple figures: {len(results['multiple_figures_referenced'])}")
        print(f"4. Questions with 'abbildung' AND multiple numbers: {len(results['all_criteria'])}")
        
        # Show detailed results for questions with abbildung and multiple numbers
        if results['all_criteria']:
            print("\n" + "="*80)
            print("QUESTIONS WITH 'ABBILDUNG' AND MULTIPLE NUMBERS:")
            print("="*80)
            for question in results['all_criteria']:
                print_question_summary(question)
        
        # Show questions referencing multiple figures
        if results['multiple_figures_referenced']:
            print("\n" + "="*80)
            print("QUESTIONS REFERENCING MULTIPLE FIGURES:")
            print("="*80)
            for question in results['multiple_figures_referenced'][:10]:  # Show first 10
                print_question_summary(question)
            
            if len(results['multiple_figures_referenced']) > 10:
                print(f"... and {len(results['multiple_figures_referenced']) - 10} more questions")
        
        # Save results to file
        output_file = 'analysis_results.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nDetailed results saved to {output_file}")
        
        # Generate extended questions for each numbered point
        if results['all_criteria']:
            print("\n" + "="*80)
            print("GENERATING EXTENDED QUESTIONS")
            print("="*80)
            
            # Check if MISTRAL_API_KEY is available
            api_key = os.getenv('MISTRAL_API_KEY')
            if not api_key:
                print("Warning: MISTRAL_API_KEY environment variable not set.")
                print("Extended questions will use fallback generation without AI assistance.")
            else:
                print("Using Mistral AI to generate enhanced questions...")
            
            # Use default parameters for legacy compatibility
            extended_questions = generate_extended_questions(results['all_criteria'])
            
            if extended_questions:
                print(f"\nGenerated {len(extended_questions)} new extended questions.")
                
                # Load all extended questions from file for display
                extended_file = 'extended_questions.json'
                all_extended_questions = []
                try:
                    with open(extended_file, 'r', encoding='utf-8') as f:
                        all_extended_questions = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    all_extended_questions = extended_questions
                
                print(f"Total extended questions in file: {len(all_extended_questions)}")
                
                # Show a few examples of newly generated questions
                if extended_questions:
                    print("\nExample newly generated questions:")
                    for i, question in enumerate(extended_questions[:3]):
                        print(f"\nNew Extended Question {i+1}:")
                        print(f"ID: {question.get('id', 'N/A')}")
                        print(f"Original ID: {question.get('original_id', 'N/A')}")
                        print(f"Target Number: {question.get('target_number', 'N/A')}")
                        print(f"Question: {question.get('question', 'N/A')}")
                        print(f"Answers: {question.get('answers', {})}")
                        print(f"Correct: {question.get('correct', [])}")
            else:
                print("No new extended questions were generated (all may already exist).")
        
    except FileNotFoundError:
        print(f"Error: Could not find {questions_file}")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {questions_file}: {e}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()