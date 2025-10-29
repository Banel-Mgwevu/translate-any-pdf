# Document Translator

A powerful Python application that translates Microsoft Word (.docx) documents while **perfectly preserving** all document structure, formatting, images, and logos.

## 🌟 Features

### Preservation
- ✅ **Document Structure** - Maintains all headings, paragraphs, and sections
- ✅ **Text Formatting** - Preserves bold, italic, underline, colors, fonts, and sizes
- ✅ **Images & Logos** - Keeps all images intact and in their original positions
- ✅ **Tables** - Maintains table structure, borders, and formatting
- ✅ **Lists** - Preserves numbered and bulleted lists
- ✅ **Headers & Footers** - Translates and preserves headers and footers
- ✅ **Styles** - Keeps all paragraph and character styles
- ✅ **Layout** - Maintains page layout, margins, and spacing

### Smart Translation
- 🌍 Supports 15+ languages
- 🔄 Auto-detects source language
- 📧 Skips email addresses (preserves formatting)
- 🔗 Skips URLs and web links
- 🔢 Skips pure numbers and dates
- 💾 Caches translations for efficiency

## 📋 Requirements

### System Requirements
- Python 3.8 or higher
- Node.js (for creating sample documents)
- Internet connection (for translation API)

### Python Packages
```bash
pip install googletrans==4.0.0rc1 defusedxml --break-system-packages
```

### Optional (for GUI)
```bash
pip install tkinter
```

## 🚀 Installation

1. **Clone or download** the application files
2. **Install dependencies**:
   ```bash
   pip install googletrans==4.0.0rc1 defusedxml --break-system-packages
   ```

3. **Verify installation**:
   ```bash
   python document_translator.py --help
   ```

## 💻 Usage

### Command Line Interface

#### Basic Usage
```bash
python document_translator.py input.docx output.docx [target_language] [source_language]
```

#### Examples

**Translate to Spanish (default):**
```bash
python document_translator.py document.docx translated.docx
```

**Translate to French:**
```bash
python document_translator.py document.docx translated_fr.docx fr
```

**Translate from English to German:**
```bash
python document_translator.py document.docx translated_de.docx de en
```

**Translate to Portuguese with auto-detect:**
```bash
python document_translator.py document.docx translated_pt.docx pt auto
```

### Graphical User Interface

For a user-friendly interface:

```bash
python document_translator_gui.py
```

**GUI Features:**
- Browse and select input/output files
- Choose source and target languages from dropdown
- Real-time progress monitoring
- Error handling with detailed messages

## 🌐 Supported Languages

| Language | Code | Language | Code |
|----------|------|----------|------|
| English | en | Spanish | es |
| French | fr | German | de |
| Italian | it | Portuguese | pt |
| Russian | ru | Chinese (Simplified) | zh-cn |
| Japanese | ja | Korean | ko |
| Arabic | ar | Dutch | nl |
| Polish | pl | Turkish | tr |
| Hindi | hi | Auto-detect | auto |

## 📝 Creating a Sample Document

To test the translator, create a sample document:

```bash
node create_sample_document.js
```

This creates `sample_document.docx` with:
- Company letterhead
- Address information
- Multiple sections
- Various formatting styles
- Professional layout

Then translate it:
```bash
python document_translator.py sample_document.docx translated.docx es
```

## 🔧 How It Works

### Translation Process

1. **Unpacking** - Extracts the DOCX file (which is a ZIP archive containing XML files)
2. **Parsing** - Reads the XML structure while preserving all formatting
3. **Translation** - Translates text content using Google Translate API
4. **Smart Filtering** - Skips emails, URLs, and numbers
5. **Preservation** - Maintains all images, styles, and structure
6. **Repacking** - Creates the translated DOCX file

### Architecture

```
document_translator.py          # Main translation logic
├── DocumentTranslator          # Core translator class
│   ├── translate_text()       # Translates individual text segments
│   ├── should_translate_node() # Determines what to translate
│   └── translate_xml_text_nodes() # Recursively processes XML
├── ooxml/                     # OOXML manipulation library
│   └── document.py           # Document structure handler
└── scripts/                   # Utility scripts
    ├── unpack.py            # Extracts DOCX files
    └── pack.py              # Creates DOCX files
```

## 📊 What Gets Translated

### ✅ Translated
- Paragraph text
- Headings and titles
- Table content
- List items
- Headers and footers
- Text in text boxes
- Captions

### ❌ Not Translated (Preserved as-is)
- Email addresses (e.g., info@company.com)
- URLs (e.g., www.example.com)
- Pure numbers (e.g., 12345, $1,000)
- Simple dates (e.g., 2025-10-27)
- Images and logos
- Charts and diagrams

## 🎨 Use Cases

### Business Documents
- Translate business proposals while keeping company logos
- Convert contracts while maintaining legal formatting
- Localize marketing materials with branded headers

### Academic Papers
- Translate research papers preserving structure
- Convert thesis documents maintaining formatting
- Localize educational materials with diagrams

### Technical Documentation
- Translate user manuals with screenshots
- Convert technical specifications with tables
- Localize product documentation with logos

## ⚙️ Advanced Options

### Custom Translation Service

To use a different translation service, modify the `translate_text()` method in `DocumentTranslator` class:

```python
def translate_text(self, text):
    # Replace with your translation API
    # Example: Azure Translator, DeepL, etc.
    result = your_translation_service.translate(text, target=self.target_lang)
    return result
```

### Batch Processing

Process multiple documents:

```python
import glob
from document_translator import DocumentTranslator

translator = DocumentTranslator(target_lang='fr')
for doc in glob.glob('*.docx'):
    output = doc.replace('.docx', '_translated.docx')
    translator.translate_document(doc, output)
```

## 🐛 Troubleshooting

### Common Issues

**Issue: "Translation failed" errors**
- Check internet connection
- Verify the Google Translate service is accessible
- Try reducing translation frequency (add delay in translate_text)

**Issue: Document structure is altered**
- Ensure input file is a valid .docx (not .doc)
- Verify file is not password-protected
- Check that file is not corrupted

**Issue: Some text not translated**
- Check if text appears as an email, URL, or number
- Verify the text is not inside an image
- Some text boxes may require manual translation

**Issue: Images missing**
- Ensure images are embedded, not linked
- Check that original document opens correctly in Word
- Verify sufficient disk space for temporary files

## 📄 File Structure

```
document_translator/
├── document_translator.py       # Main CLI application
├── document_translator_gui.py   # GUI application
├── create_sample_document.js    # Sample document generator
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── ooxml/                       # OOXML library
│   ├── __init__.py
│   ├── document.py
│   └── xmleditor.py
└── scripts/                     # Utility scripts
    ├── unpack.py
    └── pack.py
```

## 📜 License

This application uses the OOXML library which is proprietary. See LICENSE.txt for details.

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Support for more translation services (DeepL, Azure, AWS)
- Better handling of complex formatting
- Support for .doc (older Word format)
- Parallel processing for large documents
- Translation memory/glossary support

## 💡 Tips

1. **Large Documents**: For documents over 50 pages, consider breaking into sections
2. **Technical Terms**: Create a glossary file for consistent technical translations
3. **Review**: Always review translated documents for context-specific accuracy
4. **Backup**: Keep original documents before translation
5. **Testing**: Test with sample documents first to verify formatting preservation

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Verify all requirements are installed
3. Test with the provided sample document
4. Review error messages for specific issues

## 🎯 Best Practices

- **Always preview** translated documents in Word before distribution
- **Keep originals** - never overwrite source documents
- **Use specific language codes** when you know the source language
- **Review technical terms** that may need manual adjustment
- **Test formatting** by opening in Word after translation
- **Back up important documents** before batch processing

## 📈 Performance

- **Small documents** (1-5 pages): ~30 seconds
- **Medium documents** (10-20 pages): ~2-3 minutes
- **Large documents** (50+ pages): ~10-15 minutes

Translation speed depends on:
- Document size and complexity
- Internet connection speed
- Google Translate API response time
- Number of unique text segments

---

**Built with ❤️ using Python, OOXML, and Google Translate**
