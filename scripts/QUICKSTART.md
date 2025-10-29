# Quick Start Guide - Document Translator

## 🚀 Get Started in 3 Steps

### Step 1: Install Dependencies
```bash
pip install googletrans==4.0.0rc1 defusedxml --break-system-packages
```

Or use the installation script:
```bash
bash install.sh
```

### Step 2: Create a Sample Document (Optional)
```bash
node create_sample_document.js
```

This creates `sample_document.docx` with:
- Company letterhead with name and address
- Professional formatting
- Multiple sections
- Various text styles

### Step 3: Translate!

#### Option A: Command Line (Simple)
```bash
# Translate to Spanish (default)
python document_translator.py sample_document.docx translated.docx

# Translate to French
python document_translator.py sample_document.docx translated_fr.docx fr

# Translate from English to German
python document_translator.py sample_document.docx translated_de.docx de en
```

#### Option B: GUI (User-Friendly)
```bash
python document_translator_gui.py
```

Then:
1. Click "Browse..." to select your document
2. Choose output filename
3. Select target language from dropdown
4. Click "Translate Document"

## 📝 Common Use Cases

### Business Documents
```bash
# Translate a business proposal to Spanish
python document_translator.py proposal.docx propuesta.docx es

# Translate a contract to French
python document_translator.py contract.docx contrat.docx fr
```

### Multiple Languages
```python
# Use the Python script for batch processing
python examples.py
```

### Custom Translation
```python
from document_translator import DocumentTranslator

# Create translator
translator = DocumentTranslator(source_lang='en', target_lang='ja')

# Translate document
translator.translate_document('document.docx', 'document_japanese.docx')
```

## 🌐 Language Codes

Quick reference for common languages:

| Language | Code | Language | Code |
|----------|------|----------|------|
| English  | en   | Spanish  | es   |
| French   | fr   | German   | de   |
| Italian  | it   | Portuguese | pt |
| Russian  | ru   | Chinese  | zh-cn |
| Japanese | ja   | Korean   | ko   |
| Arabic   | ar   | Dutch    | nl   |

Use `auto` to auto-detect the source language.

## ✅ What's Preserved

- ✅ All text formatting (bold, italic, colors, fonts)
- ✅ Images and logos
- ✅ Company addresses and contact info
- ✅ Tables with all formatting
- ✅ Headers and footers
- ✅ Document structure and layout
- ✅ Lists (numbered and bulleted)
- ✅ Page breaks and spacing

## ⏱️ Expected Time

- Small document (1-5 pages): ~30 seconds
- Medium document (10-20 pages): ~2-3 minutes
- Large document (50+ pages): ~10-15 minutes

## 🆘 Troubleshooting

### "Translation failed" Error
- Check your internet connection
- Verify Google Translate is accessible
- Try again after a few seconds

### Document Structure Changed
- Ensure file is .docx format (not .doc)
- Verify file is not password-protected
- Check file opens correctly in Microsoft Word

### Some Text Not Translated
- Email addresses are preserved (not translated)
- URLs are preserved (not translated)
- Pure numbers are preserved (not translated)

## 📚 Learn More

- Read `README.md` for detailed documentation
- Check `examples.py` for code examples
- Open `sample_document.docx` to see structure

## 💡 Tips

1. **Always keep backups** of original documents
2. **Test with sample** document first
3. **Review translations** for accuracy
4. **Use specific language codes** when possible
5. **Preview in Word** before distributing

## 🎯 Next Steps

1. Try translating the sample document
2. Experiment with different languages
3. Test with your own documents
4. Explore the GUI interface
5. Read the full README for advanced features

---

**Need Help?** Check the README.md file or the troubleshooting section above.
