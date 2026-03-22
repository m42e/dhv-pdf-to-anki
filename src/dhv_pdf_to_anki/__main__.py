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
from dataclasses import dataclass
from typing import Callable

# Import main functions from each module (after path setup)
from dhv_pdf_to_anki.extract_images import extract_images_with_numbers as extract_images_main
from dhv_pdf_to_anki.extract_questions import extract_questions_from_pdf
from dhv_pdf_to_anki.extend_questions import generate_extended_questions
from dhv_pdf_to_anki.generate_anki import generate_anki_deck


@dataclass(slots=True)
class PipelineConfig:
    pdf_path: pathlib.Path
    anki_deck_name: str = "DHV Lernmaterial Fragen"
    output_dir: pathlib.Path = pathlib.Path("output/")
    image_pdf: str = "Bilder.pdf"
    questions_pdf: str = "Lernstoff.pdf"
    image_dir: pathlib.Path = pathlib.Path("images/")
    language: str = "de"
    save_question_images: bool = True
    mistral_api_key: str | None = None


@dataclass(slots=True)
class PipelineResult:
    questions_file: pathlib.Path
    extended_questions_file: pathlib.Path | None
    anki_file: pathlib.Path


def build_pipeline_config(args: argparse.Namespace) -> PipelineConfig:
    return PipelineConfig(
        pdf_path=pathlib.Path(args.pdf_path),
        anki_deck_name=args.anki_deck_name,
        output_dir=pathlib.Path(args.output_dir),
        image_pdf=args.image_pdf,
        questions_pdf=args.questions_pdf,
        image_dir=pathlib.Path(args.image_dir),
        language=args.language,
        save_question_images=args.no_question_images,
    )


def sanitize_deck_filename(deck_name: str) -> str:
    return deck_name.replace(" ", "_").replace("/", "_") + ".apkg"

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

def check_prerequisites(config: PipelineConfig) -> None:
    """Check if required directories and PDF files exist."""
    all_good = True
    required_dirs = [config.output_dir, config.image_dir, config.pdf_path]
    for dir_path in required_dirs:
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✓ Directory created: {dir_path}")
        else:
            print(f"✓ Directory exists: {dir_path}")
            
    # Check if the PDF files exist
    image_pdf_path = config.pdf_path / config.image_pdf
    questions_pdf_path = config.pdf_path / config.questions_pdf
    if not image_pdf_path.exists():
        print(f"❌ Image PDF file not found: {image_pdf_path}")
        all_good = False
    if not questions_pdf_path.exists():
        print(f"❌ Questions PDF file not found: {questions_pdf_path}")
        all_good = False
    
    # Check if the output directory is writable
    try:
        test_file = config.output_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
        print(f"✓ Output directory is writable: {config.output_dir}")
    except PermissionError:
        print(f"❌ Output directory is not writable: {config.output_dir}")
        all_good = False
    except Exception as e:
        print(f"❌ Error checking output directory permissions: {e}")
        all_good = False

    if not all_good:
        raise FileNotFoundError("Prerequisites check failed. Please fix the missing files or directories.")
    print(f"✓ Required PDF files found: {image_pdf_path}, {questions_pdf_path}")


def run_pipeline(
    config: PipelineConfig,
    progress_callback: Callable[[int, str], None] | None = None,
) -> PipelineResult:
    def report(progress: int, message: str) -> None:
        if progress_callback is not None:
            progress_callback(progress, message)

    report(5, "Checking input files")
    check_prerequisites(config)

    report(20, "Extracting images from image PDF")
    print("\n1. Extracting images from PDF...")
    print("-" * 40)
    extract_images_main(config.pdf_path / config.image_pdf, str(config.image_dir))

    report(45, "Extracting questions from questions PDF")
    print("\n2. Extracting questions from PDF...")
    print("-" * 40)
    questions = extract_questions_from_pdf(
        config.pdf_path / config.questions_pdf,
        save_images=config.save_question_images,
        images_dir=str(config.image_dir),
    )
    print(f"✓ Extracted {len(questions)} questions from PDF.")

    questions_file = config.output_dir / "questions.json"
    with open(questions_file, "w", encoding="utf-8") as file_handle:
        json.dump(questions, file_handle, ensure_ascii=False, indent=2)
    print(f"✓ Questions saved to: {questions_file}")

    question_files = [str(questions_file)]
    extended_questions_file: pathlib.Path | None = None

    report(65, "Checking optional AI extension step")
    print("\n3. Checking for Mistral AI API key...")
    print("-" * 40)
    mistral_api_key = config.mistral_api_key or os.getenv("MISTRAL_API_KEY")

    if mistral_api_key:
        report(75, "Generating extended questions with Mistral AI")
        print("✓ Mistral AI API key found. Generating extended questions...")
        extended_questions = generate_extended_questions(questions, str(config.output_dir), mistral_api_key)
        extended_questions_file = config.output_dir / "extended_questions.json"
        with open(extended_questions_file, "w", encoding="utf-8") as file_handle:
            json.dump(extended_questions, file_handle, ensure_ascii=False, indent=2)
        print(f"✓ Extended questions saved to: {extended_questions_file}")
        question_files.append(str(extended_questions_file))
    else:
        print("⚠ No Mistral AI API key found (MISTRAL_API_KEY environment variable).")
        print("Skipping extended question generation.")

    report(90, "Building Anki deck")
    print("\n4. Generating Anki deck...")
    print("-" * 40)

    anki_file = config.output_dir / sanitize_deck_filename(config.anki_deck_name)
    generate_anki_deck(
        question_files,
        anki_file,
        deckname=config.anki_deck_name,
        images_dir=str(config.image_dir),
        language=config.language,
    )

    report(100, "Deck generated successfully")

    return PipelineResult(
        questions_file=questions_file,
        extended_questions_file=extended_questions_file,
        anki_file=anki_file,
    )



def main() -> None:
    """
    Main function that executes the complete pipeline.
    """
    
    args = parse_args()
    config = build_pipeline_config(args)

    print("="*80)
    print("DHV PDF to Anki - Complete Pipeline")
    print("="*80)
    
    try:
        result = run_pipeline(config)

        print("\n" + "="*80)
        print("✓ Pipeline completed successfully!")
        print(f"Anki deck: {result.anki_file}")
        print("Your Anki deck should now be ready for import.")
        print("="*80)
        
    except Exception as e:
        
        print(f"\n❌ Error in pipeline: {e}")
        print("Pipeline execution failed.")
        raise


if __name__ == "__main__":
    main()