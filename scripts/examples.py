#!/usr/bin/env python3
"""
Example usage of the Document Translator

This script demonstrates various ways to use the document translator
"""

from document_translator import DocumentTranslator
import os

# Example 1: Basic Translation
print("Example 1: Basic Translation (English to Spanish)")
print("-" * 60)
translator = DocumentTranslator(source_lang='en', target_lang='es')

# Uncomment the following lines when you have a document to translate:
# translator.translate_document('input.docx', 'output_spanish.docx')

print("Translator initialized with:")
print(f"  Source Language: {translator.source_lang}")
print(f"  Target Language: {translator.target_lang}")
print()

# Example 2: Auto-detect source language
print("Example 2: Auto-detect Source Language")
print("-" * 60)
translator_auto = DocumentTranslator(source_lang='auto', target_lang='fr')
print("Translator will auto-detect source language and translate to French")
print()

# Example 3: Multiple language translations
print("Example 3: Translate to Multiple Languages")
print("-" * 60)

languages = {
    'Spanish': 'es',
    'French': 'fr',
    'German': 'de',
    'Italian': 'it',
    'Portuguese': 'pt'
}

input_file = 'document.docx'

# Check if input file exists
if os.path.exists(input_file):
    print(f"Translating {input_file} to multiple languages...")
    
    for lang_name, lang_code in languages.items():
        output_file = f'document_{lang_code}.docx'
        print(f"  → {lang_name} ({lang_code}): {output_file}")
        
        # Create translator for this language
        translator = DocumentTranslator(source_lang='auto', target_lang=lang_code)
        
        # Translate (uncomment to actually perform translation)
        # translator.translate_document(input_file, output_file)
else:
    print(f"Note: {input_file} not found. Create it first to run this example.")
    print("Example code structure:")
    print("""
    for lang_name, lang_code in languages.items():
        output_file = f'document_{lang_code}.docx'
        translator = DocumentTranslator(source_lang='auto', target_lang=lang_code)
        translator.translate_document(input_file, output_file)
    """)

print()

# Example 4: Batch Processing
print("Example 4: Batch Processing Multiple Documents")
print("-" * 60)

import glob

# Find all .docx files in current directory
docx_files = glob.glob('*.docx')

if docx_files:
    print(f"Found {len(docx_files)} DOCX files:")
    for doc in docx_files:
        print(f"  • {doc}")
    
    print("\nBatch processing code structure:")
    print("""
    translator = DocumentTranslator(target_lang='es')
    for doc in glob.glob('*.docx'):
        if not doc.endswith('_translated.docx'):
            output = doc.replace('.docx', '_translated.docx')
            translator.translate_document(doc, output)
    """)
else:
    print("No DOCX files found in current directory")

print()

# Example 5: Custom translation with callbacks
print("Example 5: Translation with Progress Tracking")
print("-" * 60)

class ProgressTracker(DocumentTranslator):
    """Extended translator with progress tracking"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.progress_callback = None
    
    def set_progress_callback(self, callback):
        """Set a callback function for progress updates"""
        self.progress_callback = callback
    
    def translate_text(self, text):
        """Override to add progress tracking"""
        result = super().translate_text(text)
        
        if self.progress_callback:
            self.progress_callback(len(self.translation_cache))
        
        return result

# Create progress tracker
def on_progress(count):
    print(f"  Translated {count} text segments...", end='\r')

tracker = ProgressTracker(target_lang='es')
tracker.set_progress_callback(on_progress)

print("Progress tracking translator created")
print("Usage: tracker.translate_document('input.docx', 'output.docx')")
print()

# Example 6: Supported Languages
print("Example 6: List of Supported Languages")
print("-" * 60)

languages_full = {
    'Auto-detect': 'auto',
    'English': 'en',
    'Spanish': 'es',
    'French': 'fr',
    'German': 'de',
    'Italian': 'it',
    'Portuguese': 'pt',
    'Russian': 'ru',
    'Chinese (Simplified)': 'zh-cn',
    'Japanese': 'ja',
    'Korean': 'ko',
    'Arabic': 'ar',
    'Dutch': 'nl',
    'Polish': 'pl',
    'Turkish': 'tr',
    'Hindi': 'hi'
}

print("Available languages:")
for lang_name, lang_code in languages_full.items():
    print(f"  {lang_name:25} → {lang_code}")

print()
print("="*60)
print("To run actual translations, uncomment the translation lines")
print("and ensure you have DOCX files to translate.")
print("="*60)
