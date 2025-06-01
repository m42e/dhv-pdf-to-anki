# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pymupdf",
# ]
# ///
import fitz # type: ignore
import re
import os
import tqdm

def extract_images_with_numbers(pdf_path, output_dir):
    """
    Extract images from PDF that are preceded by "Abbildung <number>" text.
    Images are saved with names based on the figure number.
    """
    # Open the PDF document
    doc = fitz.open(pdf_path)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    extracted_count = 0
    
    with tqdm.tqdm(total=len(doc), desc="Processing PDF pages", unit="page") as pbar:
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pbar.set_postfix({"Extracted": extracted_count, "Current page": page_num + 1})
            
            # Get all text blocks with their positions
            text_blocks = page.get_text("dict")
            
            # Get all images on the page
            image_list = page.get_images()
            
            if not image_list:
                pbar.update(1)
                continue
                
            # Extract text and find "Abbildung" patterns
            abbildung_positions = []
            for block in text_blocks["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"]
                            # Look for "Abbildung" followed by a number
                            match = re.search(r'Abbildung\s+(\d+(?:\.\d+)?)', text, re.IGNORECASE)
                            if match:
                                number = match.group(1)
                                # Get the position of this text
                                bbox = span["bbox"]
                                abbildung_positions.append({
                                    'number': number,
                                    'y_pos': bbox[1],  # y-coordinate (top of text)
                                    'bbox': bbox
                                })
            
            # Filter out already extracted "Abbildung" numbers to avoid unnecessary processing
            existing_numbers = set()
            for abbildung in abbildung_positions:
                number = abbildung['number']
                output_path = os.path.join(output_dir, f"Abbildung_{number}.png")
                if os.path.exists(output_path):
                    existing_numbers.add(number)
            
            # Remove already extracted "Abbildung" positions
            abbildung_positions = [ab for ab in abbildung_positions if ab['number'] not in existing_numbers]
            
            # Skip image processing if no remaining "Abbildung" positions
            if not abbildung_positions:
                pbar.update(1)
                continue
            
            # Process each image on the page
            for img_index, img in enumerate(image_list):
                try:
                    # Get image information
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    
                    # Skip CMYK images (convert them first)
                    if pix.n - pix.alpha < 4:
                        # Get image position on page
                        img_rects = page.get_image_rects(img)
                        
                        if img_rects:
                            img_rect = img_rects[0]
                            img_y_pos = img_rect.y0  # Top of image
                            
                            # Find the closest "Abbildung" text above this image
                            best_match = None
                            min_distance = float('inf')
                            
                            for abbildung in abbildung_positions:
                                # Check if the "Abbildung" text is above the image
                                if abbildung['y_pos'] < img_y_pos:
                                    distance = img_y_pos - abbildung['y_pos']
                                    if distance < min_distance:
                                        min_distance = distance
                                        best_match = abbildung
                            
                            if best_match and min_distance < 200:  # Within reasonable distance
                                number = best_match['number']
                                output_path = os.path.join(output_dir, f"Abbildung_{number}.png")
                                
                                # Skip if image already exists
                                if os.path.exists(output_path):
                                    continue
                                
                                # Save the image
                                if pix.alpha:
                                    pix = fitz.Pixmap(fitz.csRGB, pix)
                                
                                pix.save(output_path)
                                extracted_count += 1
                                # Update the progress bar postfix with the new extracted count
                                pbar.set_postfix({"Extracted": extracted_count, "Current page": page_num + 1})
                    else:
                        # Convert CMYK to RGB
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                        
                        # Get image position and match with text (same logic as above)
                        img_rects = page.get_image_rects(img)
                        if img_rects:
                            img_rect = img_rects[0]
                            img_y_pos = img_rect.y0
                            
                            best_match = None
                            min_distance = float('inf')
                            
                            for abbildung in abbildung_positions:
                                if abbildung['y_pos'] < img_y_pos:
                                    distance = img_y_pos - abbildung['y_pos']
                                    if distance < min_distance:
                                        min_distance = distance
                                        best_match = abbildung
                            
                            if best_match and min_distance < 200:
                                number = best_match['number']
                                output_path = os.path.join(output_dir, f"Abbildung_{number}.png")
                                
                                # Skip if image already exists
                                if os.path.exists(output_path):
                                    continue
                                
                                pix.save(output_path)
                                extracted_count += 1
                                # Update the progress bar postfix with the new extracted count
                                pbar.set_postfix({"Extracted": extracted_count, "Current page": page_num + 1})
                    
                    pix = None  # Free memory
                    
                except Exception as e:
                    print(f"Error processing image {img_index} on page {page_num + 1}: {e}")
                    continue
        
            # Update progress bar at the end of each page
            pbar.update(1)
    
    doc.close()
    print(f"\nExtraction complete! Total images extracted: {extracted_count}")

if __name__ == "__main__":
    pdf_path = "Bilder.pdf"
    output_dir = "images"
    
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found!")
    else:
        extract_images_with_numbers(pdf_path, output_dir)