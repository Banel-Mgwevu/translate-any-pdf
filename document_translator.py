#!/usr/bin/env python3
"""
Document Translator - Robust Version with Error Handling

This version includes:
- Better error handling
- Fallback to simple translation if context fails
- More logging
- Graceful degradation
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

# Try to import NLTK (optional - will fallback if not available)
try:
    import nltk
    from nltk.tokenize import sent_tokenize
    
    # Try to download required data
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        try:
            nltk.download('punkt', quiet=True)
        except:
            pass
    
    try:
        nltk.data.find('corpora/wordnet')
    except LookupError:
        try:
            nltk.download('wordnet', quiet=True)
        except:
            pass
    
    NLTK_AVAILABLE = True
except:
    NLTK_AVAILABLE = False
    print("Warning: NLTK not available - using simple sentence splitting")

# Add ooxml to path
sys.path.insert(0, os.path.dirname(__file__))

# Try to import DOCX support
try:
    from ooxml.document import Document
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False
    print("Warning: DOCX support not available")

# Try to import PDF libraries
try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("Warning: PDF support not available")


def get_python_executable():
    """Get the correct Python executable for the current platform"""
    return sys.executable


class DocumentTranslator:
    """
    Robust document translator with fallback modes
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
        self.context_cache = {}
        self.use_context = True  # Can be disabled if context mode fails
        
        # Initialize the deep-translator instance
        try:
            self.translator = GoogleTranslator(source=source_lang, target=target_lang)
            print(f"✓ Translator initialized: {source_lang} -> {target_lang}")
        except Exception as e:
            print(f"✗ Failed to initialize translator: {e}")
            self.translator = None
    
    def split_into_sentences(self, text):
        """
        Split text into sentences (uses NLTK if available, otherwise simple split)
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        if not text or not text.strip():
            return []
        
        if NLTK_AVAILABLE:
            try:
                sentences = sent_tokenize(text)
                return [s.strip() for s in sentences if s.strip()]
            except Exception as e:
                print(f"Warning: NLTK tokenization failed: {e}")
                # Fall through to simple split
        
        # Fallback: simple splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
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
        
        # Retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Add delay to avoid rate limiting
                if attempt > 0:
                    time.sleep(0.5 * attempt)
                
                # Reinitialize translator if needed
                if self.translator is None:
                    self.translator = GoogleTranslator(source=self.source_lang, target=self.target_lang)
                
                # Translate
                translated = self.translator.translate(chunk)
                
                # Validate result
                if translated is None or not translated:
                    print(f"Warning: Translation returned empty for: '{chunk[:50]}...'")
                    translated = chunk
                
                if not isinstance(translated, str):
                    print(f"Warning: Translation returned non-string type")
                    translated = chunk
                
                # Cache and return
                self.context_cache[chunk] = translated
                return translated
                
            except Exception as e:
                print(f"Warning: Translation attempt {attempt + 1}/{max_retries} failed: {e}")
                
                if attempt == max_retries - 1:
                    print(f"All retries exhausted, using original text")
                    self.context_cache[chunk] = chunk
                    return chunk
                
                # Try to recreate translator
                try:
                    time.sleep(0.5)
                    self.translator = GoogleTranslator(source=self.source_lang, target=self.target_lang)
                except Exception as recreate_error:
                    print(f"Failed to recreate translator: {recreate_error}")
        
        return chunk
    
    def translate_with_context(self, text, max_chunk_size=500):
        """
        Translate text with context awareness (with fallback to simple mode)
        
        Args:
            text: Text to translate
            max_chunk_size: Maximum characters per chunk
            
        Returns:
            Translated text
        """
        if not text or not text.strip():
            return text
        
        # Check cache
        if text in self.translation_cache:
            return self.translation_cache[text]
        
        # If context mode is disabled or text is short, translate directly
        if not self.use_context or len(text) <= max_chunk_size:
            result = self.translate_chunk(text)
            self.translation_cache[text] = result
            return result
        
        try:
            # Split into sentences
            sentences = self.split_into_sentences(text)
            
            if not sentences:
                return text
            
            # Group sentences into chunks
            chunks = []
            current_chunk = []
            current_size = 0
            
            for sentence in sentences:
                sentence_size = len(sentence)
                
                if current_size + sentence_size > max_chunk_size and current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = [sentence]
                    current_size = sentence_size
                else:
                    current_chunk.append(sentence)
                    current_size += sentence_size
            
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            
            # Translate each chunk
            translated_chunks = []
            for i, chunk in enumerate(chunks):
                translated = self.translate_chunk(chunk)
                translated_chunks.append(translated)
                
                if i < len(chunks) - 1:
                    time.sleep(0.1)
            
            # Join results
            result = ' '.join(translated_chunks)
            self.translation_cache[text] = result
            return result
            
        except Exception as e:
            print(f"Warning: Context translation failed: {e}")
            print("Falling back to simple translation...")
            
            # Fallback to simple translation
            result = self.translate_chunk(text)
            self.translation_cache[text] = result
            return result
    
    def translate_text(self, text):
        """
        Main translation method
        
        Args:
            text: Text to translate
            
        Returns:
            Translated text
        """
        try:
            return self.translate_with_context(text)
        except Exception as e:
            print(f"Error in translate_text: {e}")
            # Ultimate fallback - return original
            return text
    
    def should_translate_text(self, text):
        """
        Determine if text should be translated
        
        Args:
            text: Text to check
            
        Returns:
            Boolean
        """
        text = text.strip()
        
        if not text or len(text) < 2:
            return False
        
        # Don't translate email addresses
        if '@' in text and '.' in text and len(text.split()) == 1:
            return False
        
        # Don't translate URLs
        if text.startswith(('http://', 'https://', 'www.')):
            return False
        
        # Don't translate pure numbers
        if re.match(r'^[\d\s\-/.,]+$', text):
            return False
            
        return True
    
    def should_translate_node(self, node):
        """
        Determine if a node's text should be translated
        
        Args:
            node: XML node
            
        Returns:
            Boolean
        """
        if node.nodeType != minidom.Node.TEXT_NODE:
            return False
            
        return self.should_translate_text(node.nodeValue)
    
    def translate_xml_text_nodes(self, node):
        """
        Translate all text nodes in XML structure
        
        Args:
            node: XML node to process
        """
        try:
            if node.nodeType == minidom.Node.TEXT_NODE:
                if self.should_translate_node(node):
                    original = node.nodeValue
                    translated = self.translate_text(original)
                    node.nodeValue = translated
            
            if node.hasChildNodes():
                for child in list(node.childNodes):
                    self.translate_xml_text_nodes(child)
                    
        except Exception as e:
            print(f"Warning: Failed to translate node: {e}")
    
    def translate_docx(self, input_docx, output_docx):
        """
        Translate a DOCX document
        
        Args:
            input_docx: Path to input DOCX file
            output_docx: Path to output DOCX file
        """
        if not DOCX_SUPPORT:
            raise Exception("DOCX support not available")
        
        print(f"\n{'='*60}")
        print(f"DOCX Document Translator (Robust Mode)")
        print(f"{'='*60}")
        print(f"Input:  {input_docx}")
        print(f"Output: {output_docx}")
        print(f"Source Language: {self.source_lang}")
        print(f"Target Language: {self.target_lang}")
        print(f"{'='*60}\n")
        
        temp_dir = os.path.join(os.path.dirname(__file__), 'temp_translate')
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        try:
            python_exe = get_python_executable()
            
            # Unpack
            print("Step 1: Unpacking document...")
            unpack_script = os.path.join(os.path.dirname(__file__), 'scripts', 'unpack.py')
            
            result = subprocess.run(
                [python_exe, unpack_script, input_docx, temp_dir],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"Failed to unpack: {result.stderr}")
            
            print(result.stdout)
            
            # Initialize Document
            print("\nStep 2: Loading document structure...")
            doc = Document(temp_dir)
            
            # Translate main content
            print("\nStep 3: Translating main document...")
            doc_xml = doc['word/document.xml']
            self.translate_xml_text_nodes(doc_xml.dom.documentElement)
            
            # Translate headers/footers
            word_dir = os.path.join(doc.unpacked_path, 'word')
            if os.path.exists(word_dir):
                for header_file in [f for f in os.listdir(word_dir) if f.startswith('header') and f.endswith('.xml')]:
                    header_path = f'word/{header_file}'
                    if header_path in doc.files:
                        print(f"Translating {header_file}...")
                        header_xml = doc[header_path]
                        self.translate_xml_text_nodes(header_xml.dom.documentElement)
                
                for footer_file in [f for f in os.listdir(word_dir) if f.startswith('footer') and f.endswith('.xml')]:
                    footer_path = f'word/{footer_file}'
                    if footer_path in doc.files:
                        print(f"Translating {footer_file}...")
                        footer_xml = doc[footer_path]
                        self.translate_xml_text_nodes(footer_xml.dom.documentElement)
            
            # Save
            print("\nStep 4: Saving translated document...")
            doc.save()
            
            # Pack
            print("\nStep 5: Packing translated document...")
            pack_script = os.path.join(os.path.dirname(__file__), 'scripts', 'pack.py')
            
            result = subprocess.run(
                [python_exe, pack_script, temp_dir, output_docx],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"Failed to pack: {result.stderr}")
            
            print(result.stdout)
            
            print(f"\n{'='*60}")
            print(f"Translation Complete!")
            print(f"{'='*60}")
            print(f"Translated segments: {len(self.translation_cache)}")
            print(f"Output saved to: {output_docx}")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"\nError during translation: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    def translate_pdf(self, input_pdf, output_pdf):
        """
        Translate a PDF document
        
        Args:
            input_pdf: Path to input PDF file
            output_pdf: Path to output PDF file
        """
        if not PDF_SUPPORT:
            raise Exception("PDF support not available")
        
        print(f"\n{'='*60}")
        print(f"PDF Document Translator (Robust Mode)")
        print(f"{'='*60}")
        
        try:
            doc = fitz.open(input_pdf)
            output_doc = fitz.open()
            
            for page_num in range(len(doc)):
                print(f"Processing page {page_num + 1}...")
                page = doc[page_num]
                new_page = output_doc.new_page(width=page.rect.width, height=page.rect.height)
                
                # Copy background
                pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
                img_bytes = pix.tobytes("png")
                new_page.insert_image(new_page.rect, stream=img_bytes, overlay=False)
                
                # Translate text blocks
                blocks = page.get_text("dict")["blocks"]
                for block in blocks:
                    if block["type"] == 0:  # text block
                        block_text = ""
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                block_text += span.get("text", "") + " "
                        
                        block_text = block_text.strip()
                        if block_text and self.should_translate_text(block_text):
                            translated = self.translate_text(block_text)
                            
                            bbox = fitz.Rect(block["bbox"])
                            font_size = 11
                            if block.get("lines") and block["lines"][0].get("spans"):
                                font_size = block["lines"][0]["spans"][0].get("size", 11)
                            
                            new_page.draw_rect(bbox, color=(1, 1, 1), fill=(1, 1, 1))
                            new_page.insert_textbox(bbox, translated, fontsize=font_size)
            
            output_doc.save(output_pdf)
            output_doc.close()
            doc.close()
            
            print(f"Translation complete: {output_pdf}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def translate_document(self, input_file, output_file):
        """
        Translate a document (auto-detect format)
        
        Args:
            input_file: Path to input file
            output_file: Path to output file
        """
        if input_file.lower().endswith('.docx'):
            self.translate_docx(input_file, output_file)
        elif input_file.lower().endswith('.pdf'):
            self.translate_pdf(input_file, output_file)
        else:
            raise ValueError("Unsupported file type")


def main():
    """Main entry point"""
    if len(sys.argv) < 3:
        print("Usage: python document_translator.py <input> <output> [target_lang] [source_lang]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    target_lang = sys.argv[3] if len(sys.argv) > 3 else 'es'
    source_lang = sys.argv[4] if len(sys.argv) > 4 else 'auto'
    
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found")
        sys.exit(1)
    
    translator = DocumentTranslator(source_lang=source_lang, target_lang=target_lang)
    translator.translate_document(input_file, output_file)


if __name__ == '__main__':
    main()