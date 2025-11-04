#!/usr/bin/env python3
"""
Document Translator - Translate DOCX and PDF documents while preserving structure

This application translates Word documents and PDFs while maintaining:
- Document structure and layout
- Text formatting (bold, italic, colors, fonts) [DOCX]
- Images and logos [DOCX]
- Tables and lists [DOCX]
- Headers and footers [DOCX]
- Basic paragraph structure [PDF]
- Page breaks [PDF]
"""

import sys
import os
import shutil
import subprocess
from googletrans import Translator
from defusedxml import minidom as defused_minidom
from xml.dom import minidom
import time
import re

# Add ooxml to path
sys.path.insert(0, os.path.dirname(__file__))

# Try to import DOCX support
try:
    from ooxml.document import Document
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False
    print("Warning: DOCX support not available. Install python-docx or ooxml module.")

# Try to import PDF libraries
try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("Warning: PDF support not available. Install PyMuPDF: pip install pymupdf")


def get_python_executable():
    """Get the correct Python executable for the current platform"""
    # Try to use the same executable that's running this script
    return sys.executable


class DocumentTranslator:
    """Translates DOCX and PDF documents while preserving structure"""
    
    def __init__(self, source_lang='auto', target_lang='es'):
        """
        Initialize the translator
        
        Args:
            source_lang: Source language code (default: 'auto' for auto-detect)
            target_lang: Target language code (default: 'es' for Spanish)
        """
        self.translator = Translator()
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.translation_cache = {}
        
    def translate_text(self, text):
        """
        Translate text with caching to avoid duplicate translations
        
        Args:
            text: Text to translate
            
        Returns:
            Translated text
        """
        if not text or not text.strip():
            return text
            
        # Check cache first
        if text in self.translation_cache:
            return self.translation_cache[text]
        
        try:
            # Add small delay to avoid rate limiting
            time.sleep(0.1)
            
            result = self.translator.translate(
                text,
                src=self.source_lang,
                dest=self.target_lang
            )
            
            translated = result.text
            self.translation_cache[text] = translated
            
            return translated
            
        except Exception as e:
            print(f"Warning: Translation failed for '{text[:50]}...': {e}")
            return text
    
    def should_translate_text(self, text):
        """
        Determine if text should be translated
        
        Some elements like email addresses, URLs, or pure numbers
        should not be translated
        
        Args:
            text: Text to check
            
        Returns:
            Boolean indicating if text should be translated
        """
        text = text.strip()
        
        if not text:
            return False
        
        # Don't translate email addresses
        if '@' in text and '.' in text and len(text.split()) == 1:
            return False
        
        # Don't translate URLs
        if text.startswith('http://') or text.startswith('https://') or text.startswith('www.'):
            return False
        
        # Don't translate pure numbers or dates in simple format
        if re.match(r'^[\d\s\-/.,]+$', text):
            return False
            
        return True
    
    def should_translate_node(self, node):
        """
        Determine if a node's text should be translated (for XML nodes)
        
        Args:
            node: XML node to check
            
        Returns:
            Boolean indicating if node should be translated
        """
        if node.nodeType != minidom.Node.TEXT_NODE:
            return False
            
        return self.should_translate_text(node.nodeValue)
    
    def translate_xml_text_nodes(self, node):
        """
        Recursively translate all text nodes in an XML structure
        
        Args:
            node: XML node to process
        """
        # Process text nodes
        if node.nodeType == minidom.Node.TEXT_NODE:
            if self.should_translate_node(node):
                original = node.nodeValue
                translated = self.translate_text(original)
                node.nodeValue = translated
                print(f"  Translated: '{original[:50]}...' -> '{translated[:50]}...'")
        
        # Recursively process child nodes
        if node.hasChildNodes():
            for child in list(node.childNodes):
                self.translate_xml_text_nodes(child)
    
    def translate_pdf(self, input_pdf, output_pdf):
        """
        Translate a PDF document while preserving format and structure
        
        Args:
            input_pdf: Path to input PDF file
            output_pdf: Path to output PDF file
        """
        if not PDF_SUPPORT:
            raise Exception("PDF support not available. Install PyMuPDF: pip install pymupdf")
        
        print(f"\n{'='*60}")
        print(f"PDF Document Translator (Format-Preserving)")
        print(f"{'='*60}")
        print(f"Input:  {input_pdf}")
        print(f"Output: {output_pdf}")
        print(f"Source Language: {self.source_lang}")
        print(f"Target Language: {self.target_lang}")
        print(f"{'='*60}\n")
        
        try:
            # Open the PDF
            print("Step 1: Opening PDF and analyzing structure...")
            doc = fitz.open(input_pdf)
            num_pages = len(doc)
            print(f"  Found {num_pages} pages")
            
            # Create output document
            output_doc = fitz.open()
            
            # Process each page
            total_blocks = 0
            translated_blocks = 0
            
            for page_num in range(num_pages):
                print(f"\nStep 2: Processing page {page_num + 1}/{num_pages}...")
                page = doc[page_num]
                
                # Create a new page with same dimensions
                new_page = output_doc.new_page(width=page.rect.width, height=page.rect.height)
                
                # Copy all non-text elements (images, drawings, etc.)
                print(f"  Copying images and graphics...")
                # Get page as pixmap and insert as background
                pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
                # Convert pixmap to image bytes
                img_bytes = pix.tobytes("png")
                # Insert image as background
                new_page.insert_image(new_page.rect, stream=img_bytes, overlay=False)
                
                # Extract text blocks with positions and formatting
                print(f"  Extracting text blocks with formatting...")
                blocks = page.get_text("dict")["blocks"]
                text_blocks = [b for b in blocks if b["type"] == 0]  # Type 0 = text
                print(f"  Found {len(text_blocks)} text blocks")
                
                total_blocks += len(text_blocks)
                
                # Translate and overlay text blocks
                print(f"  Translating text blocks...")
                for block_num, block in enumerate(text_blocks):
                    try:
                        # Extract text from block
                        block_text = ""
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                block_text += span.get("text", "") + " "
                        
                        block_text = block_text.strip()
                        
                        if not block_text or not self.should_translate_text(block_text):
                            continue
                        
                        # Translate the text
                        translated_text = self.translate_text(block_text)
                        translated_blocks += 1
                        
                        # Get block rectangle and first span for formatting
                        bbox = fitz.Rect(block["bbox"])
                        
                        # Get font information from first span
                        font_size = 11  # default
                        font_name = "helv"  # default
                        font_color = (0, 0, 0)  # default black
                        
                        if block.get("lines") and block["lines"][0].get("spans"):
                            first_span = block["lines"][0]["spans"][0]
                            font_size = first_span.get("size", 11)
                            font_color = first_span.get("color", 0)
                            
                            # Convert color from int to RGB tuple
                            if isinstance(font_color, int):
                                # Extract RGB from integer
                                r = (font_color >> 16) & 0xFF
                                g = (font_color >> 8) & 0xFF
                                b = font_color & 0xFF
                                font_color = (r/255, g/255, b/255)
                        
                        # Draw white rectangle to cover original text
                        new_page.draw_rect(bbox, color=(1, 1, 1), fill=(1, 1, 1))
                        
                        # Insert translated text at the same position
                        # Use text box to handle multiline text
                        rc = new_page.insert_textbox(
                            bbox,
                            translated_text,
                            fontsize=font_size,
                            fontname=font_name,
                            color=font_color,
                            align=fitz.TEXT_ALIGN_LEFT
                        )
                        
                        if rc < 0:
                            # Text didn't fit, try with smaller font
                            new_page.draw_rect(bbox, color=(1, 1, 1), fill=(1, 1, 1))
                            rc = new_page.insert_textbox(
                                bbox,
                                translated_text,
                                fontsize=font_size * 0.8,
                                fontname=font_name,
                                color=font_color,
                                align=fitz.TEXT_ALIGN_LEFT
                            )
                        
                        if block_num % 5 == 0 and block_num > 0:
                            print(f"    Progress: {block_num}/{len(text_blocks)} blocks")
                    
                    except Exception as e:
                        print(f"    Warning: Failed to translate block {block_num}: {e}")
                        continue
                
                print(f"  ✓ Page {page_num + 1} completed")
            
            # Save the output PDF
            print(f"\nStep 3: Saving translated PDF...")
            output_doc.save(output_pdf, garbage=4, deflate=True, clean=True)
            output_doc.close()
            doc.close()
            
            print(f"\n{'='*60}")
            print(f"Translation Complete!")
            print(f"{'='*60}")
            print(f"Processed {num_pages} pages")
            print(f"Total text blocks: {total_blocks}")
            print(f"Translated blocks: {translated_blocks}")
            print(f"Unique translations: {len(self.translation_cache)}")
            print(f"Output saved to: {output_pdf}")
            print(f"✓ Format and structure preserved")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"\nError during PDF translation: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def translate_docx(self, input_docx, output_docx):
        """
        Translate a DOCX document
        
        Args:
            input_docx: Path to input DOCX file
            output_docx: Path to output DOCX file
        """
        if not DOCX_SUPPORT:
            raise Exception("DOCX support not available. Install required packages.")
        
        print(f"\n{'='*60}")
        print(f"DOCX Document Translator")
        print(f"{'='*60}")
        print(f"Input:  {input_docx}")
        print(f"Output: {output_docx}")
        print(f"Source Language: {self.source_lang}")
        print(f"Target Language: {self.target_lang}")
        print(f"{'='*60}\n")
        
        # Create temporary directory for unpacking
        temp_dir = os.path.join(os.path.dirname(__file__), 'temp_translate')
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        try:
            # Get the correct Python executable
            python_exe = get_python_executable()
            
            # Unpack the document
            print("Step 1: Unpacking document...")
            unpack_script = os.path.join(os.path.dirname(__file__), 'scripts', 'unpack.py')
            
            result = subprocess.run(
                [python_exe, unpack_script, input_docx, temp_dir],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"Error unpacking document: {result.stderr}")
                raise Exception("Failed to unpack document")
            
            print(result.stdout)
            
            # Initialize Document object
            print("\nStep 2: Loading document structure...")
            doc = Document(temp_dir)
            
            # Translate main document content
            print("\nStep 3: Translating main document content...")
            doc_xml = doc['word/document.xml']
            self.translate_xml_text_nodes(doc_xml.dom.documentElement)
            
            # Translate headers if they exist
            word_dir = os.path.join(doc.unpacked_path, 'word')
            if os.path.exists(word_dir):
                header_files = [f for f in os.listdir(word_dir)
                              if f.startswith('header') and f.endswith('.xml')]
                
                if header_files:
                    print("\nStep 4: Translating headers...")
                    for header_file in header_files:
                        header_path = f'word/{header_file}'
                        if header_path in doc.files:
                            header_xml = doc[header_path]
                            self.translate_xml_text_nodes(header_xml.dom.documentElement)
                
                # Translate footers if they exist
                footer_files = [f for f in os.listdir(word_dir)
                              if f.startswith('footer') and f.endswith('.xml')]
                
                if footer_files:
                    print("\nStep 5: Translating footers...")
                    for footer_file in footer_files:
                        footer_path = f'word/{footer_file}'
                        if footer_path in doc.files:
                            footer_xml = doc[footer_path]
                            self.translate_xml_text_nodes(footer_xml.dom.documentElement)
            
            # Save the modified document
            print("\nStep 6: Saving translated document...")
            doc.save()
            
            # Pack the document
            print("\nStep 7: Packing translated document...")
            pack_script = os.path.join(os.path.dirname(__file__), 'scripts', 'pack.py')
            
            result = subprocess.run(
                [python_exe, pack_script, temp_dir, output_docx],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"Error packing document: {result.stderr}")
                raise Exception("Failed to pack document")
            
            print(result.stdout)
            
            print(f"\n{'='*60}")
            print(f"Translation Complete!")
            print(f"{'='*60}")
            print(f"Translated {len(self.translation_cache)} unique text segments")
            print(f"Output saved to: {output_docx}")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"\nError during translation: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        finally:
            # Cleanup temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    def translate_document(self, input_file, output_file):
        """
        Translate a document (auto-detect DOCX or PDF)
        
        Args:
            input_file: Path to input file
            output_file: Path to output file
        """
        # Detect file type
        if input_file.lower().endswith('.docx'):
            self.translate_docx(input_file, output_file)
        elif input_file.lower().endswith('.pdf'):
            self.translate_pdf(input_file, output_file)
        else:
            raise ValueError("Unsupported file type. Only .docx and .pdf files are supported.")


def main():
    """Main entry point for the application"""
    
    if len(sys.argv) < 3:
        print("Document Translator - Translate DOCX and PDF while preserving structure")
        print("\nUsage:")
        print("  python document_translator.py <input_file> <output_file> [target_lang] [source_lang]")
        print("\nExamples:")
        print("  python document_translator.py document.docx translated.docx es")
        print("  python document_translator.py document.pdf translated.pdf fr en")
        print("  python document_translator.py report.docx report_es.docx es auto")
        print("\nSupported formats:")
        print(f"  DOCX: {'✓ Available' if DOCX_SUPPORT else '✗ Not available (install ooxml module)'}")
        print(f"  PDF:  {'✓ Available' if PDF_SUPPORT else '✗ Not available (pip install pypdf reportlab)'}")
        print("\nCommon language codes:")
        print("  en - English")
        print("  es - Spanish")
        print("  fr - French")
        print("  de - German")
        print("  it - Italian")
        print("  pt - Portuguese")
        print("  ru - Russian")
        print("  zh-cn - Chinese (Simplified)")
        print("  ja - Japanese")
        print("  ko - Korean")
        print("  ar - Arabic")
        print("\nFeatures:")
        print("  ✓ Auto-detects file format (DOCX or PDF)")
        print("  ✓ Preserves document structure")
        print("  ✓ DOCX: Keeps formatting, images, tables, headers, footers")
        print("  ✓ PDF: Maintains paragraph structure and page breaks")
        print("  ✓ Skips emails, URLs, and pure numbers")
        print("  ✓ Translation caching for efficiency")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    target_lang = sys.argv[3] if len(sys.argv) > 3 else 'es'
    source_lang = sys.argv[4] if len(sys.argv) > 4 else 'auto'
    
    # Validate input file
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found")
        sys.exit(1)
    
    if not (input_file.lower().endswith('.docx') or input_file.lower().endswith('.pdf')):
        print("Error: Input file must be a .docx or .pdf file")
        sys.exit(1)
    
    # Check if format is supported
    if input_file.lower().endswith('.docx') and not DOCX_SUPPORT:
        print("Error: DOCX support not available. Please install required modules.")
        sys.exit(1)
    
    if input_file.lower().endswith('.pdf') and not PDF_SUPPORT:
        print("Error: PDF support not available. Please install: pip install pypdf reportlab")
        sys.exit(1)
    
    # Create translator and translate document
    translator = DocumentTranslator(source_lang=source_lang, target_lang=target_lang)
    translator.translate_document(input_file, output_file)


if __name__ == '__main__':
    main()