#!/usr/bin/env python3
"""
Main entry point for dhv-pdf-to-anki package.

This script executes the pipeline in the following order:
1. extract_images.py - Extract images from PDF
2. extract_questions.py - Extract questions from PDF
3. extend_questions.py - Generate extended questions (if Mistral AI API key is present)
4. generate_anki.py - Generate Anki deck from questions
"""

import os
import pathlib
import sys
import json
import argparse

# Import main functions from each module (after path setup)
from dhv_pdf_to_anki.extract_images import extract_images_with_numbers as extract_images_main
from dhv_pdf_to_anki.extract_questions import extract_questions_from_pdf
from dhv_pdf_to_anki.extend_questions import generate_extended_questions
from dhv_pdf_to_anki.generate_anki import generate_anki_deck

def parse_args():
    """
    Parse command line arguments.
    Currently, no arguments are required, but this function can be extended in the future.
    """

    parser = argparse.ArgumentParser(description="Run the complete DHV PDF to Anki pipeline.")
    parser.add_argument("--pdf-path", type=str, default="pdf/", help="Path to the PDF file to process.")
    parser.add_argument("--anki-deck-name", type=str, default="DHV Lernmaterial Fragen", help="Name of the generated Anki deck.")
    parser.add_argument("--output-dir", type=str, default="output/", help="Directory to save the output files.")
    parser.add_argument("--image-pdf", type=str, default="Bilder.pdf", help="Name of the PDF file containing images.")
    parser.add_argument("--questions-pdf", type=str, default="Lernstoff.pdf", help="Name of the PDF file containing questions.")
    parser.add_argument("--image-dir", type=str, default="images/", help="Directory to save extracted images.")
    parser.add_argument("--language", type=str, choices=["en", "de"], default="de", help="Language for Anki card interface text (en=English, de=German)")
    parser.add_argument("--no-question-images", action="store_false", help="Disable extraction of question images. Only text questions will be processed.")
    # Add any future arguments here if needed
    return parser.parse_args()

def check_prerequisites(args):
    # Check if the required directories exist and create them if not
    """
    Check if the required directories exist and create them if not.
    """
    all_good = True
    required_dirs = [args.output_dir, args.image_dir, args.pdf_path]
    for dir_path in required_dirs:
        dir_path = pathlib.Path(dir_path)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✓ Directory created: {dir_path}")
        else:
            print(f"✓ Directory exists: {dir_path}")
            
    # Check if the PDF files exist
    pdf_path = pathlib.Path(args.pdf_path)
    image_pdf_path = pdf_path / args.image_pdf
    questions_pdf_path = pdf_path / args.questions_pdf
    if not image_pdf_path.exists():
        print(f"❌ Image PDF file not found: {image_pdf_path}")
        all_good = False
    if not questions_pdf_path.exists():
        print(f"❌ Questions PDF file not found: {questions_pdf_path}")
        all_good = False
    
    # Check if the output directory is writable
    try:
        test_file = pathlib.Path(args.output_dir) / ".write_test"
        test_file.touch()
        test_file.unlink()
        print(f"✓ Output directory is writable: {args.output_dir}")
    except PermissionError:
        print(f"❌ Output directory is not writable: {args.output_dir}")
        all_good = False
    except Exception as e:
        print(f"❌ Error checking output directory permissions: {e}")
        all_good = False

    if not all_good:
        print("\n❌ Prerequisites check failed. Please fix the issues above.")
        sys.exit(1)
    print(f"✓ Required PDF files found: {image_pdf_path}, {questions_pdf_path}")



def main() -> None:
    """
    Main function that executes the complete pipeline.
    """
    
    args = parse_args()

    print("="*80)
    print("DHV PDF to Anki - Complete Pipeline")
    print("="*80)
    
    check_prerequisites(args)
    
    try:
        # Step 1: Extract images from PDF
        print("\n1. Extracting images from PDF...")
        print("-" * 40)
        extract_images_main(pathlib.Path(args.pdf_path) / args.image_pdf, args.image_dir)
        
        # Step 2: Extract questions from PDF
        print("\n2. Extracting questions from PDF...")
        print("-" * 40)
        questions = extract_questions_from_pdf(pathlib.Path(args.pdf_path) / args.questions_pdf, save_images=args.no_question_images, images_dir=args.image_dir)
        print(f"✓ Extracted {len(questions)} questions from PDF.", questions)
        
        # Save questions to JSON file
        questions_file = pathlib.Path(args.output_dir) / "questions.json"
        with open(questions_file, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        print(f"✓ Questions saved to: {questions_file}")
        
        question_files = [str(questions_file)]
        
        # Step 3: Extend questions (only if Mistral AI API key is present)
        print("\n3. Checking for Mistral AI API key...")
        print("-" * 40)
        mistral_api_key = os.getenv('MISTRAL_API_KEY')
        
        if mistral_api_key:
            print("✓ Mistral AI API key found. Generating extended questions...")
            extended_questions = generate_extended_questions(questions, args.output_dir, mistral_api_key)
            extended_questions_file = pathlib.Path(args.output_dir) / "extended_questions.json"
            with open(extended_questions_file, 'w', encoding='utf-8') as f:
                json.dump(extended_questions, f, ensure_ascii=False, indent=2)
            print(f"✓ Extended questions saved to: {extended_questions_file}")
            question_files.append(str(extended_questions_file))
        else:
            print("⚠ No Mistral AI API key found (MISTRAL_API_KEY environment variable).")
            print("Skipping extended question generation.")
            print("Set MISTRAL_API_KEY environment variable to enable this feature.")
        
        # Step 4: Generate Anki deck
        print("\n4. Generating Anki deck...")
        print("-" * 40)
        
        filename = args.anki_deck_name.replace(" ", "_").replace("/", "_") + ".apkg"
        
        print('question_files:', question_files)

        generate_anki_deck(question_files, pathlib.Path(args.output_dir) / filename, deckname=args.anki_deck_name, images_dir=args.image_dir, language=args.language)
        
        print("\n" + "="*80)
        print("✓ Pipeline completed successfully!")
        print("Your Anki deck should now be ready for import.")
        print("="*80)
        
    except Exception as e:
        
        print(f"\n❌ Error in pipeline: {e}")
        print("Pipeline execution failed.")
        raise
        sys.exit(1)


if __name__ == "__main__":
    main()