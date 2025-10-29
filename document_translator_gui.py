#!/usr/bin/env python3
"""
Document Translator GUI - Interactive interface for translating documents

A user-friendly graphical interface for the document translator
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
from document_translator import DocumentTranslator


class DocumentTranslatorGUI:
    """GUI for document translation"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Document Translator - Preserve Structure & Formatting")
        self.root.geometry("700x600")
        
        # Variables
        self.input_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.source_lang = tk.StringVar(value='auto')
        self.target_lang = tk.StringVar(value='es')
        
        # Language options
        self.languages = {
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
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        
        # Title
        title_frame = ttk.Frame(self.root, padding="10")
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        title_label = ttk.Label(
            title_frame,
            text="Document Translator",
            font=('Helvetica', 16, 'bold')
        )
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        subtitle_label = ttk.Label(
            title_frame,
            text="Translate DOCX files while preserving structure, formatting, images & logos",
            font=('Helvetica', 9)
        )
        subtitle_label.grid(row=1, column=0, sticky=tk.W)
        
        # Input file selection
        input_frame = ttk.LabelFrame(self.root, text="Input Document", padding="10")
        input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        
        ttk.Entry(input_frame, textvariable=self.input_file, width=60).grid(
            row=0, column=0, padx=(0, 5)
        )
        ttk.Button(input_frame, text="Browse...", command=self.browse_input).grid(
            row=0, column=1
        )
        
        # Output file selection
        output_frame = ttk.LabelFrame(self.root, text="Output Document", padding="10")
        output_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        
        ttk.Entry(output_frame, textvariable=self.output_file, width=60).grid(
            row=0, column=0, padx=(0, 5)
        )
        ttk.Button(output_frame, text="Browse...", command=self.browse_output).grid(
            row=0, column=1
        )
        
        # Language selection
        lang_frame = ttk.LabelFrame(self.root, text="Language Settings", padding="10")
        lang_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        
        ttk.Label(lang_frame, text="Source Language:").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10)
        )
        source_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.source_lang,
            values=list(self.languages.keys()),
            state='readonly',
            width=25
        )
        source_combo.grid(row=0, column=1, sticky=tk.W)
        source_combo.set('Auto-detect')
        
        ttk.Label(lang_frame, text="Target Language:").grid(
            row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0)
        )
        target_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.target_lang,
            values=list(self.languages.keys()),
            state='readonly',
            width=25
        )
        target_combo.grid(row=1, column=1, sticky=tk.W, pady=(10, 0))
        target_combo.set('Spanish')
        
        # Features info
        features_frame = ttk.LabelFrame(self.root, text="Features", padding="10")
        features_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        
        features_text = """✓ Preserves document structure and layout
✓ Keeps all images and logos intact
✓ Maintains text formatting (bold, italic, colors, fonts)
✓ Preserves tables, lists, and styles
✓ Translates headers and footers
✓ Skips email addresses, URLs, and numbers"""
        
        ttk.Label(features_frame, text=features_text, justify=tk.LEFT).grid(
            row=0, column=0, sticky=tk.W
        )
        
        # Progress area
        progress_frame = ttk.LabelFrame(self.root, text="Progress", padding="10")
        progress_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=5)
        
        self.progress_text = scrolledtext.ScrolledText(
            progress_frame,
            height=8,
            width=70,
            state='disabled',
            wrap=tk.WORD
        )
        self.progress_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Translate button
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.grid(row=6, column=0)
        
        self.translate_button = ttk.Button(
            button_frame,
            text="Translate Document",
            command=self.translate_document,
            style='Accent.TButton'
        )
        self.translate_button.grid(row=0, column=0)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(5, weight=1)
        
    def browse_input(self):
        """Browse for input file"""
        filename = filedialog.askopenfilename(
            title="Select Input Document",
            filetypes=[("Word Documents", "*.docx"), ("All Files", "*.*")]
        )
        if filename:
            self.input_file.set(filename)
            # Auto-suggest output filename
            if not self.output_file.get():
                base, ext = os.path.splitext(filename)
                self.output_file.set(f"{base}_translated{ext}")
    
    def browse_output(self):
        """Browse for output file"""
        filename = filedialog.asksaveasfilename(
            title="Save Translated Document As",
            defaultextension=".docx",
            filetypes=[("Word Documents", "*.docx"), ("All Files", "*.*")]
        )
        if filename:
            self.output_file.set(filename)
    
    def log_progress(self, message):
        """Log progress message"""
        self.progress_text.config(state='normal')
        self.progress_text.insert(tk.END, message + '\n')
        self.progress_text.see(tk.END)
        self.progress_text.config(state='disabled')
        self.root.update()
    
    def translate_document(self):
        """Start translation process"""
        
        # Validate inputs
        if not self.input_file.get():
            messagebox.showerror("Error", "Please select an input document")
            return
        
        if not self.output_file.get():
            messagebox.showerror("Error", "Please specify an output filename")
            return
        
        if not os.path.exists(self.input_file.get()):
            messagebox.showerror("Error", "Input file does not exist")
            return
        
        # Clear progress
        self.progress_text.config(state='normal')
        self.progress_text.delete('1.0', tk.END)
        self.progress_text.config(state='disabled')
        
        # Disable button
        self.translate_button.config(state='disabled')
        
        # Get language codes
        source_lang_code = self.languages[self.source_lang.get()]
        target_lang_code = self.languages[self.target_lang.get()]
        
        # Run translation in thread
        def translate_thread():
            try:
                self.log_progress("Starting translation...")
                self.log_progress(f"Input: {self.input_file.get()}")
                self.log_progress(f"Output: {self.output_file.get()}")
                self.log_progress(f"Translating from {self.source_lang.get()} to {self.target_lang.get()}\n")
                
                translator = DocumentTranslator(
                    source_lang=source_lang_code,
                    target_lang=target_lang_code
                )
                
                translator.translate_document(
                    self.input_file.get(),
                    self.output_file.get()
                )
                
                self.log_progress("\n✓ Translation completed successfully!")
                messagebox.showinfo(
                    "Success",
                    f"Document translated successfully!\n\nOutput saved to:\n{self.output_file.get()}"
                )
                
            except Exception as e:
                self.log_progress(f"\n✗ Error: {str(e)}")
                messagebox.showerror("Error", f"Translation failed:\n{str(e)}")
            
            finally:
                self.translate_button.config(state='normal')
        
        thread = threading.Thread(target=translate_thread, daemon=True)
        thread.start()


def main():
    """Main entry point"""
    root = tk.Tk()
    app = DocumentTranslatorGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
