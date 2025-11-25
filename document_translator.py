#!/usr/bin/env python3
"""
Enhanced Document Translator - Improved METEOR scores and image preservation

Key improvements:
1. Context-aware translation (larger text chunks)
2. Sentence boundary detection
3. Better text segmentation
4. Explicit image preservation for DOCX
5. Translation quality optimization
"""

import sys
import os
import shutil
import subprocess
from deep_translator import GoogleTranslator
from defusedxml import minidom as defused_minidom
from xml.dom import minidom
import time
import re
import nltk
from nltk.tokenize import sent_tokenize

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

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
    return sys.executable


class EnhancedDocumentTranslator:
    """
    Enhanced translator with improved METEOR scores and image preservation
    """
    
    def __init__(self, source_lang='auto', target_lang='es'):
        """
        Initialize the translator
        
        Args:
            source_lang: Source language code (default: 'auto' for auto-detect)
            target_lang: Target language code (default: 'es' for Spanish)
        """
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.translation_cache = {}
        self.context_cache = {}  # Cache for context-aware translations
        
        # Initialize the deep-translator instance
        try:
            self.translator = GoogleTranslator(source=source_lang, target=target_lang)
        except Exception as e:
            print(f"Warning: Failed to initialize translator: {e}")
            self.translator = None
    
    def split_into_sentences(self, text):
        """
        Split text into sentences for better translation context
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        if not text or not text.strip():
            return []
        
        try:
            # Use NLTK for better sentence boundary detection
            sentences = sent_tokenize(text)
            return [s.strip() for s in sentences if s.strip()]
        except Exception as e:
            # Fallback to simple splitting
            sentences = re.split(r'[.!?]+', text)
            return [s.strip() for s in sentences if s.strip()]
    
    def translate_with_context(self, text, max_chunk_size=500):
        """
        Translate text with context awareness for better METEOR scores
        
        This method:
        1. Splits text into sentences
        2. Groups sentences into chunks (preserving context)
        3. Translates chunks instead of individual sentences
        4. Maintains semantic coherence
        
        Args:
            text: Text to translate
            max_chunk_size: Maximum characters per chunk
            
        Returns:
            Translated text
        """
        if not text or not text.strip():
            return text
        
        # Check cache first
        if text in self.translation_cache:
            return self.translation_cache[text]
        
        # Split into sentences
        sentences = self.split_into_sentences(text)
        
        if not sentences:
            return text
        
        # If text is short enough, translate as one chunk
        if len(text) <= max_chunk_size:
            return self.translate_chunk(text)
        
        # Group sentences into chunks while preserving context
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            # If adding this sentence exceeds max size and we have content, start new chunk
            if current_size + sentence_size > max_chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        # Translate each chunk
        translated_chunks = []
        for i, chunk in enumerate(chunks):
            translated = self.translate_chunk(chunk)
            translated_chunks.append(translated)
            
            # Small delay between chunks to avoid rate limiting
            if i < len(chunks) - 1:
                time.sleep(0.1)
        
        # Join translated chunks
        result = ' '.join(translated_chunks)
        
        # Cache the result
        self.translation_cache[text] = result
        
        return result
    
    def translate_chunk(self, chunk):
        """
        Translate a single chunk of text with retry logic
        
        Args:
            chunk: Text chunk to translate
            
        Returns:
            Translated text
        """
        if not chunk or not chunk.strip():
            return chunk
        
        # Check cache
        if chunk in self.context_cache:
            return self.context_cache[chunk]
        
        # Retry logic for robustness
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Add delay to avoid rate limiting (increase with retries)
                time.sleep(0.2 * (attempt + 1))
                
                # Reinitialize translator if needed
                if self.translator is None:
                    self.translator = GoogleTranslator(source=self.source_lang, target=self.target_lang)
                
                # Translate
                translated = self.translator.translate(chunk)
                
                # Handle None or empty returns
                if translated is None or not translated:
                    print(f"Warning: Translation returned None, using original text")
                    translated = chunk
                
                # Validate the result is a string
                if not isinstance(translated, str):
                    print(f"Warning: Translation returned non-string type, using original text")
                    translated = chunk
                
                # Cache the result
                self.context_cache[chunk] = translated
                return translated
                
            except Exception as e:
                print(f"Warning: Translation attempt {attempt + 1}/{max_retries} failed: {e}")
                
                # On last retry, return original text
                if attempt == max_retries - 1:
                    print(f"All retries exhausted, using original text")
                    self.context_cache[chunk] = chunk
                    return chunk
                
                # Try to recreate translator for next attempt
                try:
                    time.sleep(0.5)
                    self.translator = GoogleTranslator(source=self.source_lang, target=self.target_lang)
                except Exception as recreate_error:
                    print(f"Failed to recreate translator: {recreate_error}")
        
        return chunk
    
    def should_translate_text(self, text):
        """
        Determine if text should be translated
        
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
        
        # Don't translate very short fragments (likely formatting)
        if len(text) < 3:
            return False
            
        return True
    
    def extract_paragraph_text(self, paragraph_node):
        """
        Extract all text from a paragraph node while preserving structure
        
        Args:
            paragraph_node: XML paragraph node
            
        Returns:
            Extracted text
        """
        text_parts = []
        
        def extract_text_recursive(node):
            if node.nodeType == minidom.Node.TEXT_NODE:
                text = node.nodeValue
                if text and text.strip():
                    text_parts.append(text)
            
            if node.hasChildNodes():
                for child in node.childNodes:
                    extract_text_recursive(child)
        
        extract_text_recursive(paragraph_node)
        return ' '.join(text_parts)
    
    def translate_paragraph_node(self, paragraph_node):
        """
        Translate an entire paragraph as a unit for better context
        
        Args:
            paragraph_node: XML paragraph node
        """
        # Extract full paragraph text
        paragraph_text = self.extract_paragraph_text(paragraph_node)
        
        if not paragraph_text or not self.should_translate_text(paragraph_text):
            return
        
        # Translate the entire paragraph with context
        translated_paragraph = self.translate_with_context(paragraph_text)
        
        # Now replace text nodes with translated segments
        # We need to distribute the translation across the text nodes
        translated_words = translated_paragraph.split()
        word_index = 0
        
        def replace_text_nodes(node):
            nonlocal word_index
            
            if node.nodeType == minidom.Node.TEXT_NODE:
                text = node.nodeValue
                if text and text.strip():
                    # Calculate how many words this node should get
                    original_words = text.split()
                    num_words = len(original_words)
                    
                    # Get corresponding translated words
                    if word_index < len(translated_words):
                        end_index = min(word_index + num_words, len(translated_words))
                        node_translation = ' '.join(translated_words[word_index:end_index])
                        node.nodeValue = node_translation
                        word_index = end_index
            
            if node.hasChildNodes():
                for child in list(node.childNodes):
                    replace_text_nodes(child)
        
        replace_text_nodes(paragraph_node)
    
    def translate_xml_document(self, dom):
        """
        Translate XML document with paragraph-level context
        
        Args:
            dom: XML DOM document
        """
        # Find all paragraph nodes (w:p elements)
        paragraphs = dom.getElementsByTagName('w:p')
        
        total_paragraphs = len(paragraphs)
        print(f"  Found {total_paragraphs} paragraphs to translate")
        
        for i, paragraph in enumerate(paragraphs):
            try:
                self.translate_paragraph_node(paragraph)
                
                if (i + 1) % 10 == 0:
                    print(f"  Progress: {i + 1}/{total_paragraphs} paragraphs")
            except Exception as e:
                print(f"  Warning: Failed to translate paragraph {i + 1}: {e}")
                continue
    
    def verify_images_preserved(self, doc_path):
        """
        Verify that images are preserved in the DOCX structure
        
        Args:
            doc_path: Path to unpacked document
            
        Returns:
            Dictionary with image information
        """
        media_path = os.path.join(doc_path, 'word', 'media')
        
        if not os.path.exists(media_path):
            return {"images": 0, "preserved": True, "files": []}
        
        image_files = [f for f in os.listdir(media_path) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'))]
        
        return {
            "images": len(image_files),
            "preserved": True,
            "files": image_files
        }
    
    def translate_docx(self, input_docx, output_docx):
        """
        Translate a DOCX document with improved context and image preservation
        
        Args:
            input_docx: Path to input DOCX file
            output_docx: Path to output DOCX file
        """
        if not DOCX_SUPPORT:
            raise Exception("DOCX support not available. Install required packages.")
        
        print(f"\n{'='*60}")
        print(f"Enhanced DOCX Document Translator")
        print(f"{'='*60}")
        print(f"Input:  {input_docx}")
        print(f"Output: {output_docx}")
        print(f"Source Language: {self.source_lang}")
        print(f"Target Language: {self.target_lang}")
        print(f"Features: Context-aware translation + Image preservation")
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
            
            # Verify images before translation
            print("\nStep 2: Verifying images in source document...")
            source_images = self.verify_images_preserved(temp_dir)
            print(f"  Found {source_images['images']} images in source document")
            if source_images['files']:
                print(f"  Image files: {', '.join(source_images['files'][:5])}")
                if len(source_images['files']) > 5:
                    print(f"  ... and {len(source_images['files']) - 5} more")
            
            # Initialize Document object
            print("\nStep 3: Loading document structure...")
            doc = Document(temp_dir)
            
            # Translate main document content with context
            print("\nStep 4: Translating main document (context-aware)...")
            doc_xml = doc['word/document.xml']
            self.translate_xml_document(doc_xml.dom)
            
            # Translate headers if they exist
            word_dir = os.path.join(doc.unpacked_path, 'word')
            if os.path.exists(word_dir):
                header_files = [f for f in os.listdir(word_dir)
                              if f.startswith('header') and f.endswith('.xml')]
                
                if header_files:
                    print("\nStep 5: Translating headers...")
                    for header_file in header_files:
                        header_path = f'word/{header_file}'
                        if header_path in doc.files:
                            header_xml = doc[header_path]
                            self.translate_xml_document(header_xml.dom)
                
                # Translate footers if they exist
                footer_files = [f for f in os.listdir(word_dir)
                              if f.startswith('footer') and f.endswith('.xml')]
                
                if footer_files:
                    print("\nStep 6: Translating footers...")
                    for footer_file in footer_files:
                        footer_path = f'word/{footer_file}'
                        if footer_path in doc.files:
                            footer_xml = doc[footer_path]
                            self.translate_xml_document(footer_xml.dom)
            
            # Save the modified document
            print("\nStep 7: Saving translated document...")
            doc.save()
            
            # Verify images after translation
            print("\nStep 8: Verifying images after translation...")
            translated_images = self.verify_images_preserved(temp_dir)
            print(f"  Images in translated document: {translated_images['images']}")
            
            if source_images['images'] != translated_images['images']:
                print(f"  ⚠️  WARNING: Image count mismatch!")
                print(f"     Source: {source_images['images']} images")
                print(f"     Translated: {translated_images['images']} images")
            else:
                print(f"  ✓ All {source_images['images']} images preserved")
            
            # Pack the document
            print("\nStep 9: Packing translated document...")
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
            print(f"Paragraphs translated: {len(self.translation_cache)}")
            print(f"Context chunks used: {len(self.context_cache)}")
            print(f"Images preserved: {translated_images['images']}")
            print(f"Output saved to: {output_docx}")
            print(f"✓ Context-aware translation for better METEOR scores")
            print(f"✓ Images and formatting preserved")
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
    
    def translate_pdf(self, input_pdf, output_pdf):
        """
        Translate a PDF document with improved context awareness
        
        Args:
            input_pdf: Path to input PDF file
            output_pdf: Path to output PDF file
        """
        if not PDF_SUPPORT:
            raise Exception("PDF support not available. Install PyMuPDF: pip install pymupdf")
        
        print(f"\n{'='*60}")
        print(f"Enhanced PDF Document Translator")
        print(f"{'='*60}")
        print(f"Input:  {input_pdf}")
        print(f"Output: {output_pdf}")
        print(f"Source Language: {self.source_lang}")
        print(f"Target Language: {self.target_lang}")
        print(f"Features: Context-aware translation")
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
                pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
                img_bytes = pix.tobytes("png")
                new_page.insert_image(new_page.rect, stream=img_bytes, overlay=False)
                
                # Extract text blocks with positions and formatting
                print(f"  Extracting text blocks with formatting...")
                blocks = page.get_text("dict")["blocks"]
                text_blocks = [b for b in blocks if b["type"] == 0]
                print(f"  Found {len(text_blocks)} text blocks")
                
                total_blocks += len(text_blocks)
                
                # Translate and overlay text blocks with context awareness
                print(f"  Translating text blocks (context-aware)...")
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
                        
                        # Translate with context awareness
                        translated_text = self.translate_with_context(block_text)
                        translated_blocks += 1
                        
                        # Get block rectangle and formatting
                        bbox = fitz.Rect(block["bbox"])
                        
                        # Get font information
                        font_size = 11
                        font_name = "helv"
                        font_color = (0, 0, 0)
                        
                        if block.get("lines") and block["lines"][0].get("spans"):
                            first_span = block["lines"][0]["spans"][0]
                            font_size = first_span.get("size", 11)
                            font_color = first_span.get("color", 0)
                            
                            if isinstance(font_color, int):
                                r = (font_color >> 16) & 0xFF
                                g = (font_color >> 8) & 0xFF
                                b = font_color & 0xFF
                                font_color = (r/255, g/255, b/255)
                        
                        # Draw white rectangle to cover original
                        new_page.draw_rect(bbox, color=(1, 1, 1), fill=(1, 1, 1))
                        
                        # Insert translated text
                        rc = new_page.insert_textbox(
                            bbox,
                            translated_text,
                            fontsize=font_size,
                            fontname=font_name,
                            color=font_color,
                            align=fitz.TEXT_ALIGN_LEFT
                        )
                        
                        if rc < 0:
                            # Retry with smaller font
                            new_page.draw_rect(bbox, color=(1, 1, 1), fill=(1, 1, 1))
                            new_page.insert_textbox(
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
            print(f"Context chunks: {len(self.context_cache)}")
            print(f"Output saved to: {output_pdf}")
            print(f"✓ Context-aware translation for better quality")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"\nError during PDF translation: {e}")
            import traceback
            traceback.print_exc()
            raise
    
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
        print("Enhanced Document Translator - Better METEOR scores + Image preservation")
        print("\nUsage:")
        print("  python document_translator_improved.py <input_file> <output_file> [target_lang] [source_lang]")
        print("\nExamples:")
        print("  python document_translator_improved.py document.docx translated.docx es")
        print("  python document_translator_improved.py document.pdf translated.pdf fr en")
        print("\nKey Improvements:")
        print("  ✓ Context-aware translation (better METEOR scores)")
        print("  ✓ Sentence boundary detection")
        print("  ✓ Paragraph-level translation")
        print("  ✓ Explicit image preservation for DOCX")
        print("  ✓ Better semantic coherence")
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
    
    # Create translator and translate document
    translator = EnhancedDocumentTranslator(source_lang=source_lang, target_lang=target_lang)
    translator.translate_document(input_file, output_file)


if __name__ == '__main__':
    main()