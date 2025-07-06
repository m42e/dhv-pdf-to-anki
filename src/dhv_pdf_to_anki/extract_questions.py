# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pymupdf",
#     "tqdm",
# ]
# ///
import fitz  # type: ignore
import re
import json
import os
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname) 8s - %(message)s')

_logger = logging.getLogger(__name__)

vertical_margin = 4  # Vertical margin to consider for rectangle alignment
debug_page = 88

def extract_questions_from_pdf(pdf_path, save_images=True, images_dir='question_images'):
    """
    Extracts questions from a PDF file.

    Args:
        pdf_path (str): The path to the PDF file.
        save_images (bool): Whether to save images of question-answer regions.
        images_dir (str): Directory to save question images.

    Returns:
        list: A list of extracted questions.
    """
    questions = []
    
    # Create images directory if needed
    if save_images:
        os.makedirs(images_dir, exist_ok=True)

    section_id = 0
    subsection_id = 0

    # Open the PDF file
    with fitz.open(pdf_path) as doc:
        current_section = None
        current_subsection = None
        question_bbox = None
        current_question_data = None  # Track current question for image saving
        answer_bboxes = []  # Track all answer bboxes for current question
        page_num = 0  # Track page number for image saving
        for page in tqdm(doc, desc="Processing pages"):
            page_num += 1
            text = page.get_text()
            results = re.findall(r'Seite (\d+) von \d+', text)
            if int(results[0]) == debug_page:
                _logger.setLevel(logging.DEBUG)
            else:
                _logger.setLevel(logging.INFO)
            drawings = page.get_drawings()
            # Split the text into lines
            lines = list(filter(lambda x: len(x) != 1, re.split(
                r'\n(?=(\d\d\d|\d\d|\d|[ABCD])\) +)', text)))
            for line in lines:
                _logger.debug("Processing line: %s", line.strip())
                full_line = line.strip()
                if re.match(r"^[0-9]+\) ", line.strip()):
                    # Save image for previous question if exists (we'll define this function below)
                    if save_images and current_question_data and answer_bboxes and question_bbox:
                        save_question_image(doc, current_question_data, question_bbox, answer_bboxes, images_dir, current_question_data['page'])
                    
                    # Reset for new question
                    answer_bboxes = []
                    
                    questionid, line = line.split(') ', 1)
                    _logger.debug("------------------------------------------------------------")
                    _logger.debug("Found a question line %s", questionid)
                    line = re.sub(r'Seite \d+ von \d+', '', line)
                    line = line.replace('\n', ' ')
                    line = re.sub(r'\s\s+', ' ', line)
                    abbildung_number = None
                    if line.startswith('Abbildung '):
                        _logger.debug("Found an abbildung number in line: %s", line)
                        abbildung_number, line = line.split(': ', 1)
                        abbildung_number = abbildung_number.replace(
                            'Abbildung ', '').strip()
                    questions.append({"section": current_section, "subsection": current_subsection, "question": line.strip(), "answers": {}, "correct": [
                    ], "abbildung": abbildung_number, "id": questionid.strip(), "section_id": section_id, "subsection_id": subsection_id, "page": page_num - 1})
                    current_question_data = questions[-1]  # Store reference to current question
                    question_bbox = page.search_for(full_line.strip())
                # Check if the line ends with a question mark
                elif re.match(r"[ABCD]\) ", line.strip()):
                    _logger.debug("Found an answer line: %s", line.strip())
                    if questions:
                        _logger.debug("Current question: %s", questions[-1])
                        answercode, line = line.split(') ', 1)
                        line = re.sub(r'Seite \d+ von \d+', '', line)
                        line = line.replace('\n', ' ')
                        line = re.sub(r'\s\s+', ' ', line)
                        _logger.debug("Answer code: %s, line: %s", answercode, line.strip())
                        questions[-1]["answers"][answercode] = line.strip()
                    # Find the rectangle left of the answer in drawings
                    answer_bbox = page.search_for(full_line.strip())
                    # Store answer bbox for image generation
                    if answer_bbox:
                        answer_bboxes.extend(answer_bbox)
                    # Filter answer bboxes that are above the question
                    if question_bbox:
                        _logger.debug("Filtering answer bboxes above question bbox: %s", question_bbox)
                        answer_bbox = [
                            bbox for bbox in answer_bbox if bbox.y0 > question_bbox[0].y0]
                        # Limit to the answer closest to the top of the page (smallest y0)
                        if answer_bbox:
                            answer_bbox = [
                                min(answer_bbox, key=lambda bbox: bbox.y0)]
                    for drawing in drawings:
                        if drawing['type'] == 'fs':
                            rect = drawing['rect']
                            # Check if the rectangle is left of the answer text
                            for bbox in answer_bbox:
                                if (
                                    rect.y0 - vertical_margin <= bbox.y0 <= rect.y1 + vertical_margin and
                                    rect.y0 - vertical_margin <= bbox.y1 <= rect.y1 + vertical_margin
                                ):
                                    if rect.x1 <= bbox.x0 and abs(rect.y0 - bbox.y0) < vertical_margin:
                                        _logger.debug("Found a rectangle left of the answer: %s in bbox: %d, %d, %d, %d", rect, bbox.x0, bbox.y0, bbox.x1, bbox.y1)
                                        if drawing.get('fill') is not None:
                                            if questions[-1]["correct"]:
                                                raise ValueError(
                                                    f"Multiple correct answers found for question {questions[-1]['id']}")
                                            questions[-1]["correct"].append(
                                                answercode)
                else:
                    # Check if the line is on a filled rectangle with the specified gray color
                    _logger.debug("Checking line for section/subsection: %s", line.strip())
                    line_bbox = page.search_for(line.strip())
                    for drawing in drawings:
                        if drawing['type'] == 'f':
                            rect = drawing['rect']
                            fill = drawing.get('fill')
                            _logger.debug("Found rectangle: %s with fill: %s", rect, fill)
                            # Check if the rectangle has the specified gray fill
                            if fill == (0.8429999947547913, 0.8429999947547913, 0.8429999947547913):
                                # Check if the text is within this rectangle
                                for bbox in line_bbox:
                                    if (
                                        rect.x0 <= bbox.x0 <= rect.x1 and
                                        rect.y0 <= bbox.y0 <= rect.y1
                                    ):
                                        _logger.debug("Found section/subsection rectangle: %s", rect)
                                        current_section = line.strip().split(
                                            '\n')[-2].strip()
                                        section_id += 1
                                        break
                            if fill == (0.921999990940094, 0.921999990940094, 0.921999990940094):
                                # Check if the text is within this rectangle
                                for bbox in line_bbox:
                                    if (
                                        rect.x0 <= bbox.x0 <= rect.x1 and
                                        rect.y0 <= bbox.y0 <= rect.y1
                                    ):
                                        _logger.debug("Found subsection rectangle: %s", rect)
                                        current_subsection = line.strip().split(
                                            '\n')[-1].strip()
                                        subsection_id += 1
                                        break

        # Save image for the last question if exists (within the document context)
        if save_images and current_question_data and answer_bboxes and question_bbox:
            save_question_image(doc, current_question_data, question_bbox, answer_bboxes, images_dir, current_question_data['page'])

    return questions


def save_question_image(doc, question_data, question_bbox, answer_bboxes, images_dir, page_num):
    """
    Save an image of the question and its answers.
    
    Args:
        doc: The PDF document
        question_data: Dictionary containing question information
        question_bbox: Bounding box of the question text
        answer_bboxes: List of bounding boxes for all answers
        images_dir: Directory to save images
        page_num: Page number (0-indexed)
    """
    if not question_bbox or not answer_bboxes:
        return
    
    try:
        page = doc[page_num]
        
        # Combine all bounding boxes
        all_bboxes = list(question_bbox) + answer_bboxes
        
        # Calculate the overall bounding box
        min_x0 = min(bbox.x0 for bbox in all_bboxes)
        min_y0 = min(bbox.y0 for bbox in all_bboxes)
        max_x1 = max(bbox.x1 for bbox in all_bboxes)
        max_y1 = max(bbox.y1 for bbox in all_bboxes)
        
        # Add some padding
        padding = 10
        rect = fitz.Rect(
            max(0, min_x0 - padding),
            max(0, min_y0 - padding),
            min(page.rect.width, max_x1 + padding),
            min(page.rect.height, max_y1 + padding)
        )
        
        # Get the pixmap for this region
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
        pix = page.get_pixmap(matrix=mat, clip=rect)
        
        # Save the image
        question_id = question_data.get('id', 'unknown')
        section_id = question_data.get('section_id', 0)
        subsection_id = question_data.get('subsection_id', 0)
        page_id = question_data.get('page', 0)
        
        # Create unique filename using section, subsection, and question ID
        image_filename = f"question_s{section_id}_ss{subsection_id}_q{question_id}_p{page_id}.png"
        image_path = os.path.join(images_dir, image_filename)
        pix.save(image_path)
        
        # Add image path to question data
        question_data['image_path'] = image_path
        
        _logger.info(f"Saved image for question {question_id}: {image_path}")
        
    except Exception as e:
        _logger.error(f"Error saving image for question {question_data.get('id', 'unknown')}: {e}")


def main():
    pdf_path = 'pdf/Lernstoff.pdf'  # Replace with your PDF file path
    questions = extract_questions_from_pdf(pdf_path, save_images=True, images_dir='question_images')

    with open('questions.json', 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
