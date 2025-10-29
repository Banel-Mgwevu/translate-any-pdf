#!/usr/bin/env python3
"""
Setup Fix Script - Verifies and fixes the Document Translator installation
"""

import os
import sys
import shutil

def check_and_fix_structure():
    """Check directory structure and provide fixes"""
    
    print("=" * 60)
    print("Document Translator - Setup Verification & Fix")
    print("=" * 60)
    print()
    
    current_dir = os.path.dirname(os.path.abspath(__file__)) if __file__ != '<stdin>' else os.getcwd()
    print(f"Current directory: {current_dir}")
    print()
    
    # Check required files and directories
    required_items = {
        'files': [
            'document_translator.py',
            'document_translator_gui.py',
            'requirements.txt',
            'README.md'
        ],
        'directories': [
            'ooxml',
            'scripts'
        ]
    }
    
    missing_items = []
    
    print("Checking required files...")
    for file in required_items['files']:
        if os.path.exists(os.path.join(current_dir, file)):
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} - MISSING")
            missing_items.append(file)
    
    print("\nChecking required directories...")
    for directory in required_items['directories']:
        dir_path = os.path.join(current_dir, directory)
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            # Check if directory has files
            files_in_dir = os.listdir(dir_path)
            if files_in_dir:
                print(f"  ✓ {directory}/ ({len(files_in_dir)} files)")
            else:
                print(f"  ⚠ {directory}/ (empty)")
                missing_items.append(directory)
        else:
            print(f"  ✗ {directory}/ - MISSING")
            missing_items.append(directory)
    
    print()
    
    if missing_items:
        print("=" * 60)
        print("ISSUE DETECTED: Missing Required Files/Directories")
        print("=" * 60)
        print()
        print("The following items are missing:")
        for item in missing_items:
            print(f"  • {item}")
        print()
        print("SOLUTION:")
        print("1. Make sure you extracted ALL files from the download")
        print("2. The folder structure should look like this:")
        print()
        print("   your_folder/")
        print("   ├── document_translator.py")
        print("   ├── document_translator_gui.py")
        print("   ├── ooxml/")
        print("   │   ├── __init__.py")
        print("   │   ├── document.py")
        print("   │   └── xmleditor.py")
        print("   ├── scripts/")
        print("   │   ├── pack.py")
        print("   │   └── unpack.py")
        print("   └── ... (other files)")
        print()
        print("3. If ooxml/ and scripts/ folders are missing:")
        print("   - Re-download all files")
        print("   - Make sure to download the complete package")
        print("   - Check that the folders were extracted")
        print()
        return False
    else:
        print("=" * 60)
        print("✓ ALL REQUIRED FILES FOUND!")
        print("=" * 60)
        print()
        print("Your installation structure is correct.")
        print()
        print("Next steps:")
        print("1. Install dependencies:")
        print("   pip install googletrans==4.0.0rc1 defusedxml")
        print()
        print("2. Test the installation:")
        print("   python test_installation.py")
        print()
        print("3. Try translating:")
        print("   python document_translator.py sample_document.docx output.docx es")
        print()
        return True

if __name__ == '__main__':
    success = check_and_fix_structure()
    sys.exit(0 if success else 1)