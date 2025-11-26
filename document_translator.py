#!/usr/bin/env python3
"""
Document Translator - Enhanced Version for Large Documents

This version includes:
- Larger chunk sizes for efficiency (4500 chars vs 500)
- Better progress tracking
- Adaptive delays to avoid rate limiting
- Memory-efficient processing
- Better error recovery
- Progress persistence
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
import json
import hashlib

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
    Enhanced document translator for large documents
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
        self.use_context = True
        self.progress_file = None
        self.total_segments = 0
        self.translated_segments = 0
        
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
        
        # Fallback: improved sentence splitting
        # Split on sentence endings but keep the delimiter
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def translate_chunk(self, chunk):
        """
        Translate a single chunk of text with enhanced retry logic
        
        Args:
            chunk: Text chunk to translate
            
        Returns:
            Translated text
        """
        if not chunk or not chunk.strip():
            return chunk
        
        # Check cache
        cache_key = hashlib.md5(chunk.encode()).hexdigest()
        if cache_key in self.context_cache:
            return self.context_cache[cache_key]
        
        # Retry logic with exponential backoff
        max_retries = 5
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # Add exponential backoff delay
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1))
                    print(f"  Retry {attempt}/{max_retries} after {delay:.1f}s delay...")
                    time.sleep(delay)
                
                # Reinitialize translator if needed
                if self.translator is None:
                    self.translator = GoogleTranslator(source=self.source_lang, target=self.target_lang)
                
                # Translate
                translated = self.translator.translate(chunk)
                
                # Validate result
                if translated is None or not translated:
                    if attempt < max_retries - 1:
                        continue
                    print(f"  Warning: Translation returned empty for chunk")
                    translated = chunk
                
                if not isinstance(translated, str):
                    print(f"  Warning: Translation returned non-string type")
                    translated = str(translated) if translated else chunk
                
                # Cache and return
                self.context_cache[cache_key] = translated
                self.translated_segments += 1
                
                # Show progress
                if self.total_segments > 0:
                    progress = (self.translated_segments / self.total_segments) * 100
                    print(f"  Progress: {self.translated_segments}/{self.total_segments} segments ({progress:.1f}%)")
                
                return translated
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Handle specific errors
                if 'rate' in error_msg or 'limit' in error_msg or '429' in str(e):
                    print(f"  Rate limit detected, using longer delay...")
                    delay = base_delay * 3 * (2 ** attempt)
                    time.sleep(min(delay, 30))  # Cap at 30 seconds
                elif 'connection' in error_msg or 'timeout' in error_msg:
                    print(f"  Connection issue, retrying...")
                else:
                    print(f"  Translation error: {e}")
                
                if attempt == max_retries - 1:
                    print(f"  All retries exhausted, using original text")
                    self.context_cache[cache_key] = chunk
                    return chunk
                
                # Try to recreate translator
                try:
                    time.sleep(1)
                    self.translator = GoogleTranslator(source=self.source_lang, target=self.target_lang)
                except Exception as recreate_error:
                    print(f"  Failed to recreate translator: {recreate_error}")
        
        return chunk
    
    def translate_with_context(self, text, max_chunk_size=4500):
        """
        Translate text with context awareness - optimized for large documents
        
        Args:
            text: Text to translate
            max_chunk_size: Maximum characters per chunk (increased for efficiency)
            
        Returns:
            Translated text
        """
        if not text or not text.strip():
            return text
        
        # Check cache
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self.translation_cache:
            return self.translation_cache[text_hash]
        
        # If text is short, translate directly
        if len(text) <= max_chunk_size:
            result = self.translate_chunk(text)
            self.translation_cache[text_hash] = result
            return result
        
        try:
            print(f"\n📄 Processing large text block ({len(text)} characters)...")
            
            # Split into sentences
            sentences = self.split_into_sentences(text)
            
            if not sentences:
                return text
            
            print(f"  Split into {len(sentences)} sentences")
            
            # Group sentences into optimal chunks
            chunks = []
            current_chunk = []
            current_size = 0
            
            for sentence in sentences:
                sentence_size = len(sentence)
                
                # Skip extremely long sentences that exceed chunk size
                if sentence_size > max_chunk_size:
                    # Process long sentence in smaller parts
                    words = sentence.split()
                    temp_chunk = []
                    temp_size = 0
                    
                    for word in words:
                        word_size = len(word) + 1  # +1 for space
                        if temp_size + word_size > max_chunk_size and temp_chunk:
                            chunks.append(' '.join(temp_chunk))
                            temp_chunk = [word]
                            temp_size = word_size
                        else:
                            temp_chunk.append(word)
                            temp_size += word_size
                    
                    if temp_chunk:
                        chunks.append(' '.join(temp_chunk))
                    continue
                
                # Create chunk if adding sentence would exceed limit
                if current_size + sentence_size > max_chunk_size and current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = [sentence]
                    current_size = sentence_size
                else:
                    current_chunk.append(sentence)
                    current_size += sentence_size + 1  # +1 for space
            
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            
            print(f"  Optimized into {len(chunks)} chunks for translation")
            print(f"  Average chunk size: {sum(len(c) for c in chunks) // len(chunks)} characters")
            
            # Set total segments for progress tracking
            self.total_segments = len(chunks)
            self.translated_segments = 0
            
            # Translate each chunk with adaptive delays
            translated_chunks = []
            consecutive_successes = 0
            
            for i, chunk in enumerate(chunks):
                chunk_num = i + 1
                print(f"\n  Translating chunk {chunk_num}/{len(chunks)} ({len(chunk)} chars)...")
                
                try:
                    translated = self.translate_chunk(chunk)
                    translated_chunks.append(translated)
                    consecutive_successes += 1
                    
                    # Adaptive delay based on success rate and chunk size
                    if i < len(chunks) - 1:
                        if consecutive_successes < 3:
                            # Longer delay if we're having issues
                            delay = 2.0 if len(chunk) > 2000 else 1.5
                        elif len(chunk) > 3000:
                            # Longer delay for large chunks
                            delay = 1.0
                        else:
                            # Shorter delay for small chunks when things are working
                            delay = 0.5
                        
                        print(f"    Waiting {delay}s before next chunk...")
                        time.sleep(delay)
                    
                except Exception as e:
                    print(f"    Error translating chunk {chunk_num}: {e}")
                    consecutive_successes = 0
                    # Add the original chunk if translation fails
                    translated_chunks.append(chunk)
                    # Longer delay after error
                    if i < len(chunks) - 1:
                        time.sleep(3.0)
            
            # Join results
            result = ' '.join(translated_chunks)
            self.translation_cache[text_hash] = result
            
            print(f"\n  ✓ Large text translation complete!")
            print(f"  Translated {self.translated_segments}/{self.total_segments} segments")
            
            return result
            
        except Exception as e:
            print(f"\n❌ Context translation failed: {e}")
            print("  Attempting fallback to direct translation...")
            
            # Fallback to direct translation
            try:
                result = self.translate_chunk(text)
                self.translation_cache[text_hash] = result
                return result
            except Exception as fallback_error:
                print(f"  Fallback also failed: {fallback_error}")
                return text
    
    def translate_text(self, text):
        """
        Main translation method with enhanced error handling
        
        Args:
            text: Text to translate
            
        Returns:
            Translated text
        """
        try:
            # Use larger chunks for better efficiency
            return self.translate_with_context(text, max_chunk_size=4500)
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
    
    def translate_xml_text_nodes(self, node, node_count=None):
        """
        Translate all text nodes in XML structure with progress tracking
        
        Args:
            node: XML node to process
            node_count: Total number of nodes (for progress)
        """
        try:
            if node.nodeType == minidom.Node.TEXT_NODE:
                if self.should_translate_node(node):
                    original = node.nodeValue
                    translated = self.translate_text(original)
                    node.nodeValue = translated
            
            if node.hasChildNodes():
                children = list(node.childNodes)
                for i, child in enumerate(children):
                    self.translate_xml_text_nodes(child)
                    
        except Exception as e:
            print(f"Warning: Failed to translate node: {e}")
    
    def save_progress(self, doc_id, progress_data):
        """
        Save translation progress for recovery
        
        Args:
            doc_id: Document ID
            progress_data: Progress information
        """
        progress_file = f"/tmp/translation_progress_{doc_id}.json"
        try:
            with open(progress_file, 'w') as f:
                json.dump(progress_data, f)
        except Exception as e:
            print(f"Warning: Could not save progress: {e}")
    
    def load_progress(self, doc_id):
        """
        Load translation progress
        
        Args:
            doc_id: Document ID
            
        Returns:
            Progress data or None
        """
        progress_file = f"/tmp/translation_progress_{doc_id}.json"
        try:
            if os.path.exists(progress_file):
                with open(progress_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load progress: {e}")
        return None
    
    def translate_docx(self, input_docx, output_docx):
        """
        Translate a DOCX document with enhanced handling for large files
        
        Args:
            input_docx: Path to input DOCX file
            output_docx: Path to output DOCX file
        """
        if not DOCX_SUPPORT:
            raise Exception("DOCX support not available")
        
        print(f"\n{'='*60}")
        print(f"DOCX Document Translator (Enhanced for Large Documents)")
        print(f"{'='*60}")
        print(f"Input:  {input_docx}")
        print(f"Output: {output_docx}")
        print(f"Source Language: {self.source_lang}")
        print(f"Target Language: {self.target_lang}")
        
        # Check file size
        file_size = os.path.getsize(input_docx) / (1024 * 1024)  # Size in MB
        print(f"File Size: {file_size:.2f} MB")
        
        if file_size > 10:
            print(f"⚠️  Large file detected - using optimized processing")
        
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
                text=True,
                timeout=60  # Add timeout for large files
            )
            
            if result.returncode != 0:
                raise Exception(f"Failed to unpack: {result.stderr}")
            
            print(result.stdout)
            
            # Initialize Document
            print("\nStep 2: Loading document structure...")
            doc = Document(temp_dir)
            
            # Count total text nodes for progress tracking
            doc_xml = doc['word/document.xml']
            total_text_nodes = self._count_text_nodes(doc_xml.dom.documentElement)
            print(f"  Found {total_text_nodes} text segments to translate")
            
            # Translate main content
            print("\nStep 3: Translating main document...")
            print("  This may take several minutes for large documents...")
            self.translate_xml_text_nodes(doc_xml.dom.documentElement, total_text_nodes)
            
            # Translate headers/footers
            word_dir = os.path.join(doc.unpacked_path, 'word')
            if os.path.exists(word_dir):
                # Process headers
                header_files = [f for f in os.listdir(word_dir) if f.startswith('header') and f.endswith('.xml')]
                if header_files:
                    print(f"\nStep 4: Translating {len(header_files)} headers...")
                    for header_file in header_files:
                        header_path = f'word/{header_file}'
                        if header_path in doc.files:
                            print(f"  Translating {header_file}...")
                            header_xml = doc[header_path]
                            self.translate_xml_text_nodes(header_xml.dom.documentElement)
                
                # Process footers
                footer_files = [f for f in os.listdir(word_dir) if f.startswith('footer') and f.endswith('.xml')]
                if footer_files:
                    print(f"\nStep 5: Translating {len(footer_files)} footers...")
                    for footer_file in footer_files:
                        footer_path = f'word/{footer_file}'
                        if footer_path in doc.files:
                            print(f"  Translating {footer_file}...")
                            footer_xml = doc[footer_path]
                            self.translate_xml_text_nodes(footer_xml.dom.documentElement)
            
            # Save
            print("\nStep 6: Saving translated document...")
            doc.save()
            
            # Pack
            print("\nStep 7: Packing translated document...")
            pack_script = os.path.join(os.path.dirname(__file__), 'scripts', 'pack.py')
            
            result = subprocess.run(
                [python_exe, pack_script, temp_dir, output_docx],
                capture_output=True,
                text=True,
                timeout=60  # Add timeout
            )
            
            if result.returncode != 0:
                raise Exception(f"Failed to pack: {result.stderr}")
            
            print(result.stdout)
            
            # Verify output
            if os.path.exists(output_docx):
                output_size = os.path.getsize(output_docx) / (1024 * 1024)
                print(f"\n✓ Output file created: {output_size:.2f} MB")
            
            print(f"\n{'='*60}")
            print(f"Translation Complete!")
            print(f"{'='*60}")
            print(f"Translated segments: {len(self.translation_cache)}")
            print(f"Cached translations: {len(self.context_cache)}")
            print(f"Output saved to: {output_docx}")
            print(f"{'='*60}\n")
            
        except subprocess.TimeoutExpired:
            print(f"\n❌ Operation timed out - file may be too large")
            raise Exception("Document processing timed out")
        except Exception as e:
            print(f"\n❌ Error during translation: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            # Clean up
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
    
    def _count_text_nodes(self, node):
        """
        Count text nodes in XML structure
        
        Args:
            node: XML node
            
        Returns:
            Number of text nodes
        """
        count = 0
        if node.nodeType == minidom.Node.TEXT_NODE:
            if self.should_translate_text(node.nodeValue):
                count = 1
        
        if node.hasChildNodes():
            for child in node.childNodes:
                count += self._count_text_nodes(child)
        
        return count
    
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
        print(f"PDF Document Translator (Enhanced)")
        print(f"{'='*60}")
        
        try:
            doc = fitz.open(input_pdf)
            output_doc = fitz.open()
            
            total_pages = len(doc)
            print(f"Processing {total_pages} pages...")
            
            for page_num in range(total_pages):
                print(f"\nPage {page_num + 1}/{total_pages}...")
                page = doc[page_num]
                new_page = output_doc.new_page(width=page.rect.width, height=page.rect.height)
                
                # Copy background
                pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
                img_bytes = pix.tobytes("png")
                new_page.insert_image(new_page.rect, stream=img_bytes, overlay=False)
                
                # Translate text blocks
                blocks = page.get_text("dict")["blocks"]
                text_blocks = [b for b in blocks if b["type"] == 0]
                
                print(f"  Found {len(text_blocks)} text blocks")
                
                for block_num, block in enumerate(text_blocks, 1):
                    block_text = ""
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            block_text += span.get("text", "") + " "
                    
                    block_text = block_text.strip()
                    if block_text and self.should_translate_text(block_text):
                        print(f"  Translating block {block_num}/{len(text_blocks)}...")
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
            
            print(f"\n✓ Translation complete: {output_pdf}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
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