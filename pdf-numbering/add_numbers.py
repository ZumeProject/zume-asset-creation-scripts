#!/usr/bin/env python3

import os
import sys
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO

def add_page_numbers(input_path, output_path):
    """
    Add page numbers to a PDF file, centered at the bottom of each page (except the first page).
    """
    # Read the original PDF
    pdf_reader = PdfReader(input_path)
    pdf_writer = PdfWriter()
    
    # Process each page
    for page_num, page in enumerate(pdf_reader.pages):
        # The first page (page_num = 0) should not have a page number
        if page_num == 0:
            pdf_writer.add_page(page)
            continue
        
        # Create a new PDF with just the page number
        packet = BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        
        # Get the width and height of the current page
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        
        # Draw the page number centered at the bottom
        can.setFont("Helvetica", 10)
        can.drawCentredString(width / 2, 20, str(page_num + 1))
        can.save()
        
        # Move to the beginning of the BytesIO buffer
        packet.seek(0)
        number_pdf = PdfReader(packet)
        
        # Merge the original page with the page number
        page.merge_page(number_pdf.pages[0])
        pdf_writer.add_page(page)
    
    # Write the result to the output file
    with open(output_path, 'wb') as output_file:
        pdf_writer.write(output_file)

def process_pdfs():
    """
    Process all PDFs in the unnumbered folder, add page numbers, and save to the numbered folder.
    """
    # Create the numbered directory if it doesn't exist
    if not os.path.exists('numbered'):
        os.makedirs('numbered')
    
    # Get all PDF files in the unnumbered directory
    unnumbered_dir = 'unnumbered'
    if not os.path.exists(unnumbered_dir):
        print(f"Error: '{unnumbered_dir}' directory does not exist.")
        return
    
    pdf_files = [f for f in os.listdir(unnumbered_dir) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"No PDF files found in the '{unnumbered_dir}' directory.")
        return
    
    # Process each PDF file
    for pdf_file in pdf_files:
        input_path = os.path.join(unnumbered_dir, pdf_file)
        output_path = os.path.join('numbered', pdf_file)
        
        print(f"Processing: {pdf_file}")
        try:
            add_page_numbers(input_path, output_path)
            # Delete the original file after successful processing
            os.remove(input_path)
            print(f"Success: Processed '{pdf_file}' and removed original")
        except Exception as e:
            print(f"Error processing '{pdf_file}': {str(e)}")

if __name__ == "__main__":
    print("Starting PDF page numbering process...")
    process_pdfs()
    print("PDF processing complete!")
