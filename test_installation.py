#!/usr/bin/env python3
"""
Test script to verify Document Translator installation
"""

import sys
import os

def test_imports():
    """Test if all required modules can be imported"""
    print("Testing imports...")
    
    try:
        import googletrans
        print("  ✓ googletrans imported successfully")
    except ImportError as e:
        print(f"  ✗ googletrans import failed: {e}")
        return False
    
    try:
        import defusedxml
        print("  ✓ defusedxml imported successfully")
    except ImportError as e:
        print(f"  ✗ defusedxml import failed: {e}")
        return False
    
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from ooxml.document import Document
        print("  ✓ ooxml.document imported successfully")
    except ImportError as e:
        print(f"  ✗ ooxml.document import failed: {e}")
        return False
    
    try:
        from document_translator import DocumentTranslator
        print("  ✓ DocumentTranslator imported successfully")
    except ImportError as e:
        print(f"  ✗ DocumentTranslator import failed: {e}")
        return False
    
    return True

def test_translator_init():
    """Test if translator can be initialized"""
    print("\nTesting DocumentTranslator initialization...")
    
    try:
        from document_translator import DocumentTranslator
        translator = DocumentTranslator(source_lang='en', target_lang='es')
        print("  ✓ DocumentTranslator initialized successfully")
        print(f"    Source: {translator.source_lang}")
        print(f"    Target: {translator.target_lang}")
        return True
    except Exception as e:
        print(f"  ✗ Initialization failed: {e}")
        return False

def test_sample_document():
    """Test if sample document exists"""
    print("\nChecking for sample document...")
    
    sample_path = 'sample_document.docx'
    if os.path.exists(sample_path):
        size = os.path.getsize(sample_path)
        print(f"  ✓ Sample document found ({size} bytes)")
        return True
    else:
        print(f"  ⚠ Sample document not found")
        print(f"    Run: node create_sample_document.js")
        return False

def test_scripts():
    """Test if utility scripts exist"""
    print("\nChecking utility scripts...")
    
    scripts = ['scripts/unpack.py', 'scripts/pack.py']
    all_exist = True
    
    for script in scripts:
        if os.path.exists(script):
            print(f"  ✓ {script} found")
        else:
            print(f"  ✗ {script} not found")
            all_exist = False
    
    return all_exist

def test_ooxml_library():
    """Test if ooxml library is accessible"""
    print("\nChecking ooxml library...")
    
    files = ['ooxml/__init__.py', 'ooxml/document.py', 'ooxml/xmleditor.py']
    all_exist = True
    
    for file in files:
        if os.path.exists(file):
            print(f"  ✓ {file} found")
        else:
            print(f"  ✗ {file} not found")
            all_exist = False
    
    return all_exist

def test_simple_translation():
    """Test a simple text translation"""
    print("\nTesting simple translation...")
    
    try:
        from googletrans import Translator
        translator = Translator()
        
        # Test translation
        result = translator.translate("Hello, World!", src='en', dest='es')
        
        print(f"  Original: 'Hello, World!'")
        print(f"  Translated: '{result.text}'")
        print(f"  ✓ Translation works!")
        
        return True
    except Exception as e:
        print(f"  ✗ Translation test failed: {e}")
        print(f"    Check internet connection")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Document Translator - Installation Test")
    print("=" * 60)
    print()
    
    tests = [
        ("Module Imports", test_imports),
        ("Translator Initialization", test_translator_init),
        ("Sample Document", test_sample_document),
        ("Utility Scripts", test_scripts),
        ("OOXML Library", test_ooxml_library),
        ("Simple Translation", test_simple_translation),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"  ✗ Test failed with exception: {e}")
            results.append((name, False))
        print()
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Installation is complete.")
        print("\nNext steps:")
        print("  1. Try: python document_translator.py sample_document.docx translated.docx es")
        print("  2. Or:  python document_translator_gui.py")
        print("  3. Read: QUICKSTART.md for more examples")
    else:
        print("\n⚠ Some tests failed. Please check the errors above.")
        print("\nTroubleshooting:")
        print("  1. Install dependencies: pip install -r requirements.txt --break-system-packages")
        print("  2. Check Python version: python --version (need 3.8+)")
        print("  3. Verify internet connection for translation tests")
        print("  4. See README.md for detailed installation instructions")
    
    print("=" * 60)
    
    return 0 if passed == total else 1

if __name__ == '__main__':
    sys.exit(main())
