# Windows Installation Troubleshooting Guide

## Error: "ModuleNotFoundError: No module named 'ooxml'"

This error means the `ooxml` folder is not in the correct location.

### Quick Fix (Choose One)

#### Option 1: Verify All Files Are Present

Run this command to check your setup:
```powershell
python fix_setup.py
```

This will tell you exactly what's missing.

#### Option 2: Manual Check

1. Open File Explorer and navigate to your project folder
2. Verify you have these folders:
   ```
   C:\Users\X\Desktop\translator_ai\files\
   ├── ooxml\           ← Must be present!
   │   ├── __init__.py
   │   ├── document.py
   │   └── xmleditor.py
   ├── scripts\         ← Must be present!
   │   ├── pack.py
   │   └── unpack.py
   ├── document_translator.py
   ├── document_translator_gui.py
   └── ... other files
   ```

3. If `ooxml\` or `scripts\` folders are missing:
   - You need to re-download ALL files
   - Make sure to extract the complete archive
   - Don't just copy individual .py files

### Detailed Solution Steps

#### Step 1: Check Current Directory Structure

```powershell
# List all files and folders
dir
```

You should see:
- `ooxml` folder
- `scripts` folder
- `document_translator.py`
- Other .py and .md files

#### Step 2: If Folders Are Missing

The `ooxml` and `scripts` folders contain essential code. You must have them.

**Where to get them:**
- Re-download the complete package from where you got it
- Extract ALL files, not just the Python scripts
- Make sure folder structure is preserved during extraction

#### Step 3: Verify Installation

```powershell
python fix_setup.py
```

This will check everything and tell you what's wrong.

## Other Common Windows Issues

### Issue: "pip install" Warnings

**Warning about PATH:**
```
WARNING: The script chardetect.exe is installed in '...' which is not on PATH.
```

**Solution:** This is just a warning, not an error. You can ignore it or add the directory to your PATH.

### Issue: Dependency Conflicts

**Error:**
```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed.
```

**Solution:** This is also just a warning. The translator will still work.

If you have issues, you can create a virtual environment:

```powershell
# Create virtual environment
python -m venv translator_env

# Activate it
translator_env\Scripts\activate

# Install dependencies
pip install googletrans==4.0.0rc1 defusedxml

# Now run the translator
python document_translator.py input.docx output.docx es
```

### Issue: Cannot Find Python

**Error:**
```
'python' is not recognized as an internal or external command
```

**Solution:**
Try using `python3` or `py` instead:
```powershell
python3 document_translator.py input.docx output.docx es
# or
py document_translator.py input.docx output.docx es
```

## Step-by-Step Windows Installation

### 1. Ensure Complete File Structure

Your folder should contain:

```
translator_ai\files\
├── ooxml\                          ← REQUIRED FOLDER
│   ├── __init__.py
│   ├── document.py
│   └── xmleditor.py
├── scripts\                        ← REQUIRED FOLDER
│   ├── pack.py
│   └── unpack.py
├── document_translator.py          ← Main program
├── document_translator_gui.py      ← GUI program
├── create_sample_document.js
├── examples.py
├── fix_setup.py                    ← NEW: Setup checker
├── test_installation.py
├── requirements.txt
├── README.md
├── QUICKSTART.md
└── sample_document.docx
```

### 2. Install Dependencies

```powershell
pip install googletrans==4.0.0rc1 defusedxml
```

### 3. Verify Installation

```powershell
python fix_setup.py
```

### 4. Test with Sample Document

```powershell
# If you have Node.js installed:
node create_sample_document.js

# Translate the sample
python document_translator.py sample_document.docx translated.docx es
```

### 5. Use the GUI (Easier)

```powershell
python document_translator_gui.py
```

Then use the visual interface to select files.

## Quick Test Commands

Run these in order to test your installation:

```powershell
# 1. Check setup
python fix_setup.py

# 2. Test installation
python test_installation.py

# 3. Try translation (if you have a .docx file)
python document_translator.py input.docx output.docx es
```

## Still Having Issues?

### Check Python Version

```powershell
python --version
```

You need Python 3.8 or higher.

### Check pip Version

```powershell
pip --version
```

### Reinstall Dependencies

```powershell
pip uninstall googletrans httpx httpcore -y
pip install googletrans==4.0.0rc1 defusedxml
```

### Use Virtual Environment (Recommended)

```powershell
# Create clean environment
python -m venv venv

# Activate it
venv\Scripts\activate

# You should see (venv) in your prompt
# Now install
pip install googletrans==4.0.0rc1 defusedxml

# Run translator
python document_translator.py input.docx output.docx es

# When done, deactivate
deactivate
```

## Contact & Support

If you're still stuck:

1. Run `python fix_setup.py` and share the output
2. Run `dir` and verify you have `ooxml\` and `scripts\` folders
3. Check that you downloaded ALL files, not just .py scripts
4. Verify your Python version is 3.8+

## Most Common Mistake

**You copied individual .py files but forgot the folders!**

The `ooxml` and `scripts` folders are **essential**. They contain the core functionality. You must have them in the same directory as `document_translator.py`.

**Solution:** Download and extract the complete package with all folders intact.
