# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pymupdf",
#     "tqdm",
# ]
# ///
import fitz # type: ignore
import re
import json
from tqdm import tqdm

vertical_margin = 4  # Vertical margin to consider for rectangle alignment

def extract_questions_from_pdf(pdf_path):
    """
    Extracts questions from a PDF file.
    
    Args:
        pdf_path (str): The path to the PDF file.
        
    Returns:
        list: A list of extracted questions.
    """
    questions = []
    
    section_id = 0
    subsection_id = 0
    
    # Open the PDF file
    with fitz.open(pdf_path) as doc:
        current_section = None
        current_subsection = None
        question_bbox = None
        for page in tqdm(doc, desc="Processing pages"):
            text = page.get_text()
            drawings = page.get_drawings()
            # Split the text into lines
            lines = list(filter(lambda x: len(x) != 1, re.split(r'\s+(?=(\d\d\d|\d\d|\d|[ABCD])\) +)', text)))
            for line in lines:
                full_line = line.strip()
                if re.match(r"^[0-9]+\) ", line.strip()):
                    questionid,line = line.split(') ', 1)
                    line = re.sub(r'Seite \d+ von \d+', '', line)
                    line = line.replace('\n', ' ')
                    line = re.sub(r'\s\s+', ' ', line)
                    abbildung_number = None
                    if line.startswith('Abbildung '):
                        abbildung_number, line = line.split(': ', 1)
                        abbildung_number = abbildung_number.replace('Abbildung ', '').strip()
                    questions.append({"section": current_section, "subsection": current_subsection, "question": line.strip(), "answers": {}, "correct" : [], "abbildung": abbildung_number, "id": questionid.strip(), "section_id": section_id, "subsection_id": subsection_id})
                    question_bbox = page.search_for(full_line.strip())
                # Check if the line ends with a question mark
                elif re.match(r"[ABCD]\) ", line.strip()):
                    if questions:
                        answercode, line = line.split(') ', 1)
                        line = re.sub(r'Seite \d+ von \d+', '', line)
                        line = line.replace('\n', ' ')
                        line = re.sub(r'\s\s+', ' ', line)
                        questions[-1]["answers"][answercode]= line.strip()
                    # Find the rectangle left of the answer in drawings
                    answer_bbox = page.search_for(full_line.strip())
                    # Filter answer bboxes that are above the question
                    if question_bbox:
                        answer_bbox = [bbox for bbox in answer_bbox if bbox.y0 > question_bbox[0].y0]
                        # Limit to the answer closest to the top of the page (smallest y0)
                        if answer_bbox:
                            answer_bbox = [min(answer_bbox, key=lambda bbox: bbox.y0)]
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
                                        if drawing.get('fill') is not None:
                                            if questions[-1]["correct"]:
                                                raise ValueError(f"Multiple correct answers found for question {questions[-1]['id']}")
                                            questions[-1]["correct"].append(answercode)
                else:
                    # Check if the line is on a filled rectangle with the specified gray color
                    line_bbox = page.search_for(line.strip())
                    for drawing in drawings:
                        if drawing['type'] == 'f':
                            rect = drawing['rect']
                            fill = drawing.get('fill')
                            # Check if the rectangle has the specified gray fill
                            if fill == (0.8429999947547913, 0.8429999947547913, 0.8429999947547913):
                                # Check if the text is within this rectangle
                                for bbox in line_bbox:
                                    if (
                                        rect.x0 <= bbox.x0 <= rect.x1 and
                                        rect.y0 <= bbox.y0 <= rect.y1
                                    ):
                                        current_section = line.strip().split('\n')[-2].strip()
                                        section_id += 1
                                        break
                            if fill == (0.921999990940094, 0.921999990940094, 0.921999990940094):
                                # Check if the text is within this rectangle
                                for bbox in line_bbox:
                                    if (
                                        rect.x0 <= bbox.x0 <= rect.x1 and
                                        rect.y0 <= bbox.y0 <= rect.y1
                                    ):
                                        current_subsection = line.strip().split('\n')[-1].strip()
                                        subsection_id += 1
                                        break
    
    return questions


def main():
    pdf_path = 'pdf/Lernstoff.pdf'  # Replace with your PDF file path
    questions = extract_questions_from_pdf(pdf_path)
    
    with open('questions.json', 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()