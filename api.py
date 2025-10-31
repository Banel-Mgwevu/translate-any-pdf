#!/usr/bin/env python3
"""
FastAPI REST API for Document Translation Service

API Endpoints:
- POST /upload - Upload document for translation
- POST /translate - Translate document with selected source/target language
- GET /download/{doc_id} - Download translated file
- GET /metrics/{doc_id} - Fetch evaluation metrics
- POST /backtranslate - Perform back-translation
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
import uuid
import time
from datetime import datetime
import shutil

# Import the existing DocumentTranslator
import sys
sys.path.insert(0, os.path.dirname(__file__))
from document_translator import DocumentTranslator

# Initialize FastAPI app
app = FastAPI(
    title="Document Translation API",
    description="Translate DOCX documents while preserving structure and formatting",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Storage directories
UPLOAD_DIR = "/tmp/api_uploads"
OUTPUT_DIR = "/tmp/api_outputs"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# In-memory storage for document metadata and metrics
documents = {}


class TranslationRequest(BaseModel):
    """Request model for translation"""
    doc_id: str
    source_lang: str = "auto"
    target_lang: str = "es"


class BackTranslationRequest(BaseModel):
    """Request model for back-translation"""
    doc_id: str
    intermediate_lang: str = "es"
    final_lang: str = "en"


class TranslationResponse(BaseModel):
    """Response model for translation"""
    doc_id: str
    status: str
    message: str
    translated_doc_id: Optional[str] = None


class MetricsResponse(BaseModel):
    """Response model for metrics"""
    doc_id: str
    original_filename: str
    translated_filename: Optional[str] = None
    source_lang: str
    target_lang: str
    upload_time: str
    translation_time: Optional[str] = None
    translation_duration: Optional[float] = None
    segments_translated: Optional[int] = None
    status: str


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "service": "Document Translation API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "POST /upload",
            "translate": "POST /translate",
            "download": "GET /download/{doc_id}",
            "metrics": "GET /metrics/{doc_id}",
            "backtranslate": "POST /backtranslate"
        }
    }


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document for translation
    
    Args:
        file: DOCX file to upload
        
    Returns:
        Document ID and upload confirmation
    """
    # Validate file type
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")
    
    # Generate unique document ID
    doc_id = str(uuid.uuid4())
    
    # Save uploaded file
    upload_path = os.path.join(UPLOAD_DIR, f"{doc_id}.docx")
    
    try:
        with open(upload_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Store document metadata
    documents[doc_id] = {
        "doc_id": doc_id,
        "original_filename": file.filename,
        "upload_path": upload_path,
        "upload_time": datetime.now().isoformat(),
        "status": "uploaded",
        "translated_path": None,
        "translated_doc_id": None,
        "source_lang": None,
        "target_lang": None,
        "translation_time": None,
        "translation_duration": None,
        "segments_translated": None
    }
    
    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "status": "uploaded",
        "message": f"Document uploaded successfully with ID: {doc_id}"
    }


@app.post("/translate", response_model=TranslationResponse)
async def translate_document(request: TranslationRequest, background_tasks: BackgroundTasks):
    """
    Translate a document with selected source/target language
    
    Args:
        request: Translation request with doc_id, source_lang, and target_lang
        
    Returns:
        Translation status and new document ID
    """
    # Validate document exists
    if request.doc_id not in documents:
        raise HTTPException(status_code=404, detail=f"Document ID '{request.doc_id}' not found")
    
    doc_info = documents[request.doc_id]
    
    if doc_info["status"] == "translating":
        raise HTTPException(status_code=409, detail="Document is already being translated")
    
    # Generate new document ID for translated version
    translated_doc_id = str(uuid.uuid4())
    output_path = os.path.join(OUTPUT_DIR, f"{translated_doc_id}.docx")
    
    # Update status
    doc_info["status"] = "translating"
    doc_info["source_lang"] = request.source_lang
    doc_info["target_lang"] = request.target_lang
    doc_info["translated_doc_id"] = translated_doc_id
    
    try:
        # Perform translation
        start_time = time.time()
        
        translator = DocumentTranslator(
            source_lang=request.source_lang,
            target_lang=request.target_lang
        )
        
        translator.translate_document(doc_info["upload_path"], output_path)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Update document info
        doc_info["status"] = "completed"
        doc_info["translated_path"] = output_path
        doc_info["translation_time"] = datetime.now().isoformat()
        doc_info["translation_duration"] = duration
        doc_info["segments_translated"] = len(translator.translation_cache)
        
        # Store translated document metadata
        documents[translated_doc_id] = {
            "doc_id": translated_doc_id,
            "original_filename": doc_info["original_filename"].replace(".docx", f"_translated_{request.target_lang}.docx"),
            "upload_path": output_path,
            "upload_time": datetime.now().isoformat(),
            "status": "translated",
            "source_doc_id": request.doc_id,
            "source_lang": request.source_lang,
            "target_lang": request.target_lang
        }
        
        return TranslationResponse(
            doc_id=request.doc_id,
            status="completed",
            message=f"Document translated successfully from {request.source_lang} to {request.target_lang}",
            translated_doc_id=translated_doc_id
        )
        
    except Exception as e:
        doc_info["status"] = "failed"
        doc_info["error"] = str(e)
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


@app.get("/download/{doc_id}")
async def download_document(doc_id: str):
    """
    Download a translated document
    
    Args:
        doc_id: Document ID (can be original or translated)
        
    Returns:
        File download
    """
    # Check if document exists
    if doc_id not in documents:
        raise HTTPException(status_code=404, detail=f"Document ID '{doc_id}' not found")
    
    doc_info = documents[doc_id]
    
    # Determine which file to download
    if doc_info.get("translated_path") and os.path.exists(doc_info["translated_path"]):
        file_path = doc_info["translated_path"]
        filename = doc_info["original_filename"].replace(".docx", "_translated.docx")
    elif os.path.exists(doc_info["upload_path"]):
        file_path = doc_info["upload_path"]
        filename = doc_info["original_filename"]
    else:
        raise HTTPException(status_code=404, detail="File not found on server")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@app.get("/metrics/{doc_id}", response_model=MetricsResponse)
async def get_metrics(doc_id: str):
    """
    Fetch evaluation metrics for a document
    
    Args:
        doc_id: Document ID
        
    Returns:
        Document metrics including translation stats
    """
    if doc_id not in documents:
        raise HTTPException(status_code=404, detail=f"Document ID '{doc_id}' not found")
    
    doc_info = documents[doc_id]
    
    return MetricsResponse(
        doc_id=doc_id,
        original_filename=doc_info["original_filename"],
        translated_filename=doc_info.get("original_filename", "").replace(".docx", "_translated.docx") if doc_info.get("translated_path") else None,
        source_lang=doc_info.get("source_lang", "N/A"),
        target_lang=doc_info.get("target_lang", "N/A"),
        upload_time=doc_info["upload_time"],
        translation_time=doc_info.get("translation_time"),
        translation_duration=doc_info.get("translation_duration"),
        segments_translated=doc_info.get("segments_translated"),
        status=doc_info["status"]
    )


@app.post("/backtranslate", response_model=TranslationResponse)
async def backtranslate_document(request: BackTranslationRequest):
    """
    Perform back-translation on a document
    (Translate to intermediate language, then back to original/final language)
    
    Args:
        request: Back-translation request with doc_id, intermediate_lang, and final_lang
        
    Returns:
        Back-translation status and document IDs
    """
    # Validate document exists
    if request.doc_id not in documents:
        raise HTTPException(status_code=404, detail=f"Document ID '{request.doc_id}' not found")
    
    doc_info = documents[request.doc_id]
    
    try:
        # Step 1: Translate to intermediate language
        intermediate_doc_id = str(uuid.uuid4())
        intermediate_path = os.path.join(OUTPUT_DIR, f"{intermediate_doc_id}.docx")
        
        translator1 = DocumentTranslator(
            source_lang="auto",
            target_lang=request.intermediate_lang
        )
        
        print(f"Step 1: Translating to {request.intermediate_lang}...")
        translator1.translate_document(doc_info["upload_path"], intermediate_path)
        
        # Step 2: Translate back to final language
        final_doc_id = str(uuid.uuid4())
        final_path = os.path.join(OUTPUT_DIR, f"{final_doc_id}.docx")
        
        translator2 = DocumentTranslator(
            source_lang=request.intermediate_lang,
            target_lang=request.final_lang
        )
        
        print(f"Step 2: Translating back to {request.final_lang}...")
        translator2.translate_document(intermediate_path, final_path)
        
        # Store intermediate document
        documents[intermediate_doc_id] = {
            "doc_id": intermediate_doc_id,
            "original_filename": doc_info["original_filename"].replace(".docx", f"_intermediate_{request.intermediate_lang}.docx"),
            "upload_path": intermediate_path,
            "upload_time": datetime.now().isoformat(),
            "status": "intermediate",
            "source_doc_id": request.doc_id
        }
        
        # Store final back-translated document
        documents[final_doc_id] = {
            "doc_id": final_doc_id,
            "original_filename": doc_info["original_filename"].replace(".docx", f"_backtranslated_{request.final_lang}.docx"),
            "upload_path": final_path,
            "upload_time": datetime.now().isoformat(),
            "status": "backtranslated",
            "source_doc_id": request.doc_id,
            "intermediate_doc_id": intermediate_doc_id
        }
        
        return TranslationResponse(
            doc_id=request.doc_id,
            status="completed",
            message=f"Back-translation completed: {request.intermediate_lang} → {request.final_lang}",
            translated_doc_id=final_doc_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Back-translation failed: {str(e)}")


@app.delete("/document/{doc_id}")
async def delete_document(doc_id: str):
    """
    Delete a document and its associated files
    
    Args:
        doc_id: Document ID to delete
        
    Returns:
        Deletion confirmation
    """
    if doc_id not in documents:
        raise HTTPException(status_code=404, detail=f"Document ID '{doc_id}' not found")
    
    doc_info = documents[doc_id]
    
    # Delete files
    try:
        if os.path.exists(doc_info["upload_path"]):
            os.remove(doc_info["upload_path"])
        
        if doc_info.get("translated_path") and os.path.exists(doc_info["translated_path"]):
            os.remove(doc_info["translated_path"])
        
        # Remove from storage
        del documents[doc_id]
        
        return {
            "doc_id": doc_id,
            "status": "deleted",
            "message": "Document deleted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@app.get("/documents")
async def list_documents():
    """
    List all documents in the system
    
    Returns:
        List of all documents with their metadata
    """
    return {
        "total_documents": len(documents),
        "documents": [
            {
                "doc_id": doc_id,
                "filename": info["original_filename"],
                "status": info["status"],
                "upload_time": info["upload_time"]
            }
            for doc_id, info in documents.items()
        ]
    }


if __name__ == "__main__":
    print("=" * 60)
    print("Document Translation API Server")
    print("=" * 60)
    print("Starting server on http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)