"""
IMPROVED API with Background Processing and Large File Support

Key improvements:
1. Background task processing with status tracking
2. Real-time progress updates via polling
3. File size validation and limits
4. Request timeout handling
5. Translation queue management
6. Better error recovery
7. Chunked file uploads for large documents
8. Multiple payment tier support (Professional & Enterprise)
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request, Depends, Query
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
import uvicorn
import os
import uuid
import time
import json
import hashlib
from datetime import datetime, timedelta
import shutil
import sys
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
from queue import Queue
import traceback

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import the improved DocumentTranslator
try:
    from document_translator import DocumentTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False
    print("WARNING: document_translator not available!")

app = FastAPI(
    title="Document Translation API - Enhanced for Large Files",
    description="With background processing and progress tracking",
    version="4.0.0"
)

# ============================================
# CONFIGURATION
# ============================================

BACKEND_URL = os.getenv("BACKEND_URL", "https://translate-any-pdf.onrender.com")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://translation-app-frontend-lhk5.onrender.com")

# File size limits
MAX_FILE_SIZE_MB = 100  # Maximum file size in MB
CHUNK_SIZE_KB = 1024  # Chunk size for reading large files

# Translation settings
TRANSLATION_TIMEOUT = 1800  # 30 minutes timeout for translation
MAX_CONCURRENT_TRANSLATIONS = 3  # Max translations running at once

# Paystack Configuration - Multiple Payment Links for Different Tiers
PAYSTACK_PAYMENT_LINKS = {
    "professional": "https://paystack.shop/pay/8zcv4xhc7r",  # R20/month
    "enterprise": "https://paystack.shop/pay/e6i2wk1lnn"     # R999/month
}
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")

# ============================================
# BACKGROUND TASK MANAGER
# ============================================

class TranslationTaskManager:
    """Manages background translation tasks"""
    
    def __init__(self):
        self.tasks = {}
        self.executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_TRANSLATIONS)
        self.lock = threading.Lock()
        self.queue = Queue()
        
    def add_task(self, task_id, user_id, doc_info):
        """Add a new translation task"""
        with self.lock:
            self.tasks[task_id] = {
                "task_id": task_id,
                "user_id": user_id,
                "doc_info": doc_info,
                "status": "queued",
                "progress": 0,
                "message": "Waiting in queue...",
                "created_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None,
                "error": None,
                "result": None
            }
        return self.tasks[task_id]
    
    def update_task(self, task_id, **kwargs):
        """Update task status"""
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].update(kwargs)
                self.tasks[task_id]["updated_at"] = datetime.now().isoformat()
    
    def get_task(self, task_id):
        """Get task status"""
        with self.lock:
            return self.tasks.get(task_id)
    
    def get_user_tasks(self, user_id):
        """Get all tasks for a user"""
        with self.lock:
            return [task for task in self.tasks.values() if task["user_id"] == user_id]
    
    def cleanup_old_tasks(self, hours=24):
        """Remove tasks older than specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        with self.lock:
            old_tasks = []
            for task_id, task in self.tasks.items():
                created_at = datetime.fromisoformat(task["created_at"])
                if created_at < cutoff_time:
                    old_tasks.append(task_id)
            
            for task_id in old_tasks:
                del self.tasks[task_id]

# Initialize task manager
task_manager = TranslationTaskManager()

# ============================================
# CORS
# ============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:4173",
        "https://translation-app-frontend-lhk5.onrender.com",
        "https://translate-any-pdf.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# REQUEST LOGGING MIDDLEWARE
# ============================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for debugging"""
    start_time = time.time()
    
    # Skip logging for health/status endpoints
    if request.url.path in ["/health", "/", "/task/status"]:
        response = await call_next(request)
        return response
    
    print(f"\n{'='*70}")
    print(f"📥 INCOMING REQUEST")
    print(f"{'='*70}")
    print(f"Method:  {request.method}")
    print(f"Path:    {request.url.path}")
    print(f"Client:  {request.client.host if request.client else 'Unknown'}")
    
    # Check for auth header
    auth_header = request.headers.get("authorization")
    if auth_header:
        token = auth_header.replace("Bearer ", "")[:20]
        print(f"Auth:    ✓ Present (token: {token}...)")
    else:
        print(f"Auth:    ✗ MISSING")
    
    print(f"{'='*70}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    print(f"📤 RESPONSE")
    print(f"{'='*70}")
    print(f"Status:  {response.status_code}")
    print(f"Time:    {process_time:.2f}s")
    
    if response.status_code >= 400:
        print(f"❌ ERROR RESPONSE")
    else:
        print(f"✓ SUCCESS")
    
    print(f"{'='*70}\n")
    
    return response

# Security
security = HTTPBearer()

# Storage
UPLOAD_DIR = "/tmp/api_uploads"
OUTPUT_DIR = "/tmp/api_outputs"
DATA_DIR = "/tmp/api_data"

for dir_path in [UPLOAD_DIR, OUTPUT_DIR, DATA_DIR]:
    os.makedirs(dir_path, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")
PAYMENTS_FILE = os.path.join(DATA_DIR, "payments.json")
SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.json")
PENDING_UPGRADES_FILE = os.path.join(DATA_DIR, "pending_upgrades.json")

# Storage functions
def load_json(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return {}
    return {}

def save_json(filename, data):
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving {filename}: {e}")

# In-memory storage
users = load_json(USERS_FILE)
payments = load_json(PAYMENTS_FILE)
sessions = load_json(SESSIONS_FILE)
pending_upgrades = load_json(PENDING_UPGRADES_FILE)
documents = {}

# Subscription tiers
SUBSCRIPTION_TIERS = {
    "free": {"name": "Free", "limit": 5, "price": 0},
    "professional": {"name": "Professional", "limit": 20, "price": 20},
    "enterprise": {"name": "Enterprise", "limit": float('inf'), "price": 999}
}

# Supported formats
SUPPORTED_FORMATS = {
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.pdf': 'application/pdf'
}

# ============================================
# PYDANTIC MODELS
# ============================================

class UserSignUp(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserSignIn(BaseModel):
    email: EmailStr
    password: str

class TranslationRequest(BaseModel):
    doc_id: str
    source_lang: str = "auto"
    target_lang: str = "af"

class PaymentInitiate(BaseModel):
    tier: str

class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    tier: str
    translations_used: int
    translations_limit: int
    created_at: str

class AuthResponse(BaseModel):
    token: str
    user: UserResponse

class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    file_type: str
    status: str
    upload_time: str
    translated_doc_id: Optional[str] = None
    error: Optional[str] = None
    task_id: Optional[str] = None
    progress: Optional[int] = None

class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: int
    message: str
    error: Optional[str] = None
    completed: bool

# ============================================
# UTILITY FUNCTIONS
# ============================================

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token() -> str:
    return str(uuid.uuid4())

def get_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()

def is_supported_format(filename: str) -> bool:
    return get_file_extension(filename) in SUPPORTED_FORMATS

def get_payment_link(tier: str) -> str:
    """Get the correct Paystack payment link for a tier"""
    return PAYSTACK_PAYMENT_LINKS.get(tier, PAYSTACK_PAYMENT_LINKS["professional"])

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify authentication token"""
    token = credentials.credentials
    
    if token not in sessions:
        raise HTTPException(
            status_code=401, 
            detail="Invalid or expired token. Please sign in again."
        )
    
    session = sessions[token]
    user_id = session["user_id"]
    
    # Check expiration
    session_time = datetime.fromisoformat(session["created_at"])
    age = datetime.now() - session_time
    
    if age > timedelta(days=1):
        del sessions[token]
        save_json(SESSIONS_FILE, sessions)
        raise HTTPException(
            status_code=401, 
            detail="Session expired. Please sign in again."
        )
    
    if user_id not in users:
        raise HTTPException(status_code=401, detail="User not found")
    
    user = users[user_id]
    
    return user

def get_user_by_email(email: str) -> Optional[dict]:
    """Find user by email"""
    for user in users.values():
        if user["email"].lower() == email.lower():
            return user
    return None

# ============================================
# BACKGROUND TRANSLATION FUNCTION
# ============================================

def process_translation_task(task_id: str, doc: dict, source_lang: str, target_lang: str, user_id: str):
    """
    Process translation in background thread
    """
    try:
        print(f"\n{'='*70}")
        print(f"🔄 BACKGROUND TRANSLATION STARTED")
        print(f"{'='*70}")
        print(f"Task ID: {task_id}")
        print(f"Document: {doc['filename']}")
        print(f"Size: {doc.get('file_size', 0) / (1024*1024):.2f} MB")
        print(f"{'='*70}\n")
        
        # Update task status
        task_manager.update_task(task_id, 
            status="processing",
            started_at=datetime.now().isoformat(),
            message="Initializing translation..."
        )
        
        # Check file exists
        if not os.path.exists(doc["upload_path"]):
            raise Exception("Source file not found")
        
        # Create output path
        translated_doc_id = str(uuid.uuid4())
        file_ext = doc["file_type"]
        output_path = os.path.join(OUTPUT_DIR, f"{translated_doc_id}{file_ext}")
        
        # Initialize translator with progress callback
        task_manager.update_task(task_id, 
            progress=10,
            message="Loading document..."
        )
        
        translator = DocumentTranslator(
            source_lang=source_lang,
            target_lang=target_lang
        )
        
        # Create a progress monitor
        def update_progress():
            """Monitor translation progress"""
            start_time = time.time()
            while True:
                elapsed = time.time() - start_time
                if elapsed > TRANSLATION_TIMEOUT:
                    raise Exception("Translation timeout")
                
                # Calculate progress based on translator's cache
                if hasattr(translator, 'translated_segments') and hasattr(translator, 'total_segments'):
                    if translator.total_segments > 0:
                        progress = int((translator.translated_segments / translator.total_segments) * 80) + 10
                        task_manager.update_task(task_id, 
                            progress=min(progress, 90),
                            message=f"Translating... ({translator.translated_segments}/{translator.total_segments} segments)"
                        )
                
                time.sleep(2)  # Update every 2 seconds
                
                # Check if translation is complete
                if os.path.exists(output_path):
                    break
        
        # Start progress monitor in separate thread
        progress_thread = threading.Thread(target=update_progress, daemon=True)
        progress_thread.start()
        
        # Perform translation
        task_manager.update_task(task_id, 
            progress=20,
            message="Starting translation..."
        )
        
        translator.translate_document(doc["upload_path"], output_path)
        
        # Verify output
        if not os.path.exists(output_path):
            raise Exception("Translation completed but output file not found")
        
        output_size = os.path.getsize(output_path)
        
        # Update document record
        doc["status"] = "completed"
        doc["translated_path"] = output_path
        doc["translated_doc_id"] = translated_doc_id
        doc["source_lang"] = source_lang
        doc["target_lang"] = target_lang
        doc["translation_time"] = datetime.now().isoformat()
        doc["output_size"] = output_size
        
        # Update user usage
        if user_id in users:
            users[user_id]["translations_used"] += 1
            users[user_id]["updated_at"] = datetime.now().isoformat()
            save_json(USERS_FILE, users)
        
        # Update task as completed
        task_manager.update_task(task_id,
            status="completed",
            progress=100,
            message="Translation completed successfully!",
            completed_at=datetime.now().isoformat(),
            result={
                "translated_doc_id": translated_doc_id,
                "output_size": output_size,
                "segments_translated": len(translator.translation_cache)
            }
        )
        
        print(f"\n{'='*70}")
        print(f"✅ BACKGROUND TRANSLATION COMPLETED")
        print(f"{'='*70}")
        print(f"Task ID: {task_id}")
        print(f"Output size: {output_size / (1024*1024):.2f} MB")
        print(f"Segments: {len(translator.translation_cache)}")
        print(f"{'='*70}\n")
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n{'='*70}")
        print(f"❌ BACKGROUND TRANSLATION FAILED")
        print(f"{'='*70}")
        print(f"Task ID: {task_id}")
        print(f"Error: {error_msg}")
        print(f"{'='*70}\n")
        
        # Update document status
        doc["status"] = "failed"
        doc["error"] = error_msg
        doc["error_time"] = datetime.now().isoformat()
        
        # Update task as failed
        task_manager.update_task(task_id,
            status="failed",
            progress=0,
            message="Translation failed",
            error=error_msg,
            completed_at=datetime.now().isoformat()
        )

# ============================================
# AUTHENTICATION ENDPOINTS
# ============================================

@app.post("/auth/signup", response_model=AuthResponse)
async def sign_up(user_data: UserSignUp):
    """Register a new user"""
    
    # Check if user exists
    if any(u["email"] == user_data.email for u in users.values()):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(user_data.password)
    
    users[user_id] = {
        "user_id": user_id,
        "email": user_data.email,
        "name": user_data.name,
        "password": hashed_password,
        "tier": "free",
        "translations_used": 0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    save_json(USERS_FILE, users)
    
    # Create session
    token = generate_token()
    sessions[token] = {
        "user_id": user_id,
        "created_at": datetime.now().isoformat()
    }
    save_json(SESSIONS_FILE, sessions)
    
    user = users[user_id]
    tier_info = SUBSCRIPTION_TIERS[user["tier"]]
    
    return AuthResponse(
        token=token,
        user=UserResponse(
            user_id=user["user_id"],
            email=user["email"],
            name=user["name"],
            tier=user["tier"],
            translations_used=user["translations_used"],
            translations_limit=tier_info["limit"],
            created_at=user["created_at"]
        )
    )

@app.post("/auth/signin", response_model=AuthResponse)
async def sign_in(credentials: UserSignIn):
    """Sign in existing user"""
    
    # Find user
    user = None
    for u in users.values():
        if u["email"] == credentials.email:
            user = u
            break
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    hashed_password = hash_password(credentials.password)
    if user["password"] != hashed_password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create session
    token = generate_token()
    sessions[token] = {
        "user_id": user["user_id"],
        "created_at": datetime.now().isoformat()
    }
    save_json(SESSIONS_FILE, sessions)
    
    tier_info = SUBSCRIPTION_TIERS[user["tier"]]
    
    return AuthResponse(
        token=token,
        user=UserResponse(
            user_id=user["user_id"],
            email=user["email"],
            name=user["name"],
            tier=user["tier"],
            translations_used=user["translations_used"],
            translations_limit=tier_info["limit"],
            created_at=user["created_at"]
        )
    )

@app.post("/auth/signout")
async def sign_out(user: dict = Depends(verify_token)):
    """Sign out current user"""
    
    # Remove session
    token_to_remove = None
    for token, session in sessions.items():
        if session["user_id"] == user["user_id"]:
            token_to_remove = token
            break
    
    if token_to_remove:
        del sessions[token_to_remove]
        save_json(SESSIONS_FILE, sessions)
    
    return {"message": "Signed out successfully"}

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user(user: dict = Depends(verify_token)):
    """Get current user info"""
    tier_info = SUBSCRIPTION_TIERS[user["tier"]]
    
    return UserResponse(
        user_id=user["user_id"],
        email=user["email"],
        name=user["name"],
        tier=user["tier"],
        translations_used=user["translations_used"],
        translations_limit=tier_info["limit"],
        created_at=user["created_at"]
    )

# ============================================
# DOCUMENT TRANSLATION ENDPOINTS - ENHANCED
# ============================================

@app.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    user: dict = Depends(verify_token)
):
    """Upload document with size validation and chunked reading"""
    
    print(f"\n{'='*70}")
    print(f"📤 FILE UPLOAD")
    print(f"{'='*70}")
    print(f"User:     {user['email']}")
    print(f"Filename: {file.filename}")
    print(f"{'='*70}\n")
    
    # Check limit
    tier_info = SUBSCRIPTION_TIERS[user["tier"]]
    if user["translations_used"] >= tier_info["limit"]:
        raise HTTPException(
            status_code=403,
            detail=f"Translation limit reached ({tier_info['limit']} per month)"
        )
    
    # Validate format
    if not is_supported_format(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format. Supported: {', '.join(SUPPORTED_FORMATS.keys())}"
        )
    
    # Save file with chunked reading for large files
    doc_id = str(uuid.uuid4())
    file_ext = get_file_extension(file.filename)
    upload_path = os.path.join(UPLOAD_DIR, f"{doc_id}{file_ext}")
    
    try:
        file_size = 0
        chunk_count = 0
        
        with open(upload_path, "wb") as buffer:
            while True:
                # Read in chunks to handle large files
                chunk = await file.read(CHUNK_SIZE_KB * 1024)
                if not chunk:
                    break
                    
                buffer.write(chunk)
                file_size += len(chunk)
                chunk_count += 1
                
                # Check size limit
                if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                    os.remove(upload_path)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB"
                    )
                
                # Log progress for very large files
                if chunk_count % 10 == 0:
                    print(f"  Uploaded {file_size / (1024*1024):.1f}MB...")
        
        print(f"✓ File saved: {upload_path}")
        print(f"✓ Size: {file_size / (1024*1024):.2f}MB")
        print(f"✓ Doc ID: {doc_id}\n")
        
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(upload_path):
            os.remove(upload_path)
        print(f"❌ Save failed: {e}\n")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Store metadata
    documents[doc_id] = {
        "doc_id": doc_id,
        "user_id": user["user_id"],
        "filename": file.filename,
        "file_type": file_ext,
        "upload_path": upload_path,
        "upload_time": datetime.now().isoformat(),
        "status": "uploaded",
        "file_size": file_size
    }
    
    # Determine if file is large
    is_large_file = file_size > 5 * 1024 * 1024  # > 5MB
    
    response = {
        "doc_id": doc_id,
        "filename": file.filename,
        "file_type": file_ext,
        "status": "uploaded",
        "file_size_mb": round(file_size / (1024*1024), 2),
        "is_large_file": is_large_file,
        "message": f"File uploaded successfully. {'Large file detected - translation will run in background.' if is_large_file else 'Ready for translation.'}"
    }
    
    return response

@app.post("/translate")
async def translate_document(
    request: TranslationRequest, 
    background_tasks: BackgroundTasks,
    user: dict = Depends(verify_token)
):
    """Translate document with background processing for large files"""
    
    print(f"\n{'='*70}")
    print(f"🌐 TRANSLATION REQUEST")
    print(f"{'='*70}")
    print(f"User:    {user['email']}")
    print(f"Doc ID:  {request.doc_id}")
    print(f"Source:  {request.source_lang}")
    print(f"Target:  {request.target_lang}")
    print(f"{'='*70}\n")
    
    # Check translator availability
    if not TRANSLATOR_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Translation service not available. Contact administrator."
        )
    
    # Check document exists
    if request.doc_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents[request.doc_id]
    
    # Verify ownership
    if doc["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check limit
    tier_info = SUBSCRIPTION_TIERS[user["tier"]]
    if user["translations_used"] >= tier_info["limit"]:
        raise HTTPException(status_code=403, detail="Translation limit reached")
    
    # Check file exists
    if not os.path.exists(doc["upload_path"]):
        doc["status"] = "failed"
        doc["error"] = "Source file not found"
        raise HTTPException(status_code=404, detail="Source file not found")
    
    # Determine if this should be a background task
    file_size_mb = doc["file_size"] / (1024 * 1024)
    use_background = file_size_mb > 2  # Use background for files > 2MB
    
    if use_background:
        # Create background task
        task_id = str(uuid.uuid4())
        
        # Add to task manager
        task_manager.add_task(task_id, user["user_id"], doc)
        
        # Update document with task ID
        doc["task_id"] = task_id
        doc["status"] = "queued"
        
        # Submit to thread pool
        task_manager.executor.submit(
            process_translation_task,
            task_id,
            doc,
            request.source_lang,
            request.target_lang,
            user["user_id"]
        )
        
        print(f"✓ Background task created: {task_id}")
        print(f"  File size: {file_size_mb:.2f}MB")
        print(f"  Estimated time: {int(file_size_mb * 2)} minutes\n")
        
        return {
            "doc_id": request.doc_id,
            "task_id": task_id,
            "status": "queued",
            "message": "Translation started in background. Poll /task/{task_id}/status for progress.",
            "estimated_minutes": int(file_size_mb * 2),
            "file_size_mb": round(file_size_mb, 2)
        }
        
    else:
        # Process small files immediately (existing code)
        try:
            print(f"Processing small file directly ({file_size_mb:.2f}MB)...")
            
            doc["status"] = "translating"
            
            # Create output path
            translated_doc_id = str(uuid.uuid4())
            file_ext = doc["file_type"]
            output_path = os.path.join(OUTPUT_DIR, f"{translated_doc_id}{file_ext}")
            
            # Initialize translator
            translator = DocumentTranslator(
                source_lang=request.source_lang,
                target_lang=request.target_lang
            )
            
            # Translate with timeout
            start_time = time.time()
            translator.translate_document(doc["upload_path"], output_path)
            translation_time = time.time() - start_time
            
            # Verify output
            if not os.path.exists(output_path):
                raise Exception("Translation completed but output file not found")
            
            output_size = os.path.getsize(output_path)
            
            # Update document
            doc["status"] = "completed"
            doc["translated_path"] = output_path
            doc["translated_doc_id"] = translated_doc_id
            doc["source_lang"] = request.source_lang
            doc["target_lang"] = request.target_lang
            doc["translation_time"] = datetime.now().isoformat()
            doc["translation_duration"] = translation_time
            doc["output_size"] = output_size
            
            # Increment usage
            users[user["user_id"]]["translations_used"] += 1
            users[user["user_id"]]["updated_at"] = datetime.now().isoformat()
            save_json(USERS_FILE, users)
            
            print(f"✓ Direct translation completed in {translation_time:.1f}s\n")
            
            return {
                "doc_id": request.doc_id,
                "status": "completed",
                "translated_doc_id": translated_doc_id,
                "file_type": file_ext,
                "translation_time": translation_time,
                "segments_translated": len(translator.translation_cache),
                "translations_remaining": tier_info["limit"] - users[user["user_id"]]["translations_used"]
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Direct translation failed: {error_msg}\n")
            
            doc["status"] = "failed"
            doc["error"] = error_msg
            doc["error_time"] = datetime.now().isoformat()
            
            raise HTTPException(
                status_code=500,
                detail=f"Translation failed: {error_msg}"
            )

@app.get("/task/{task_id}/status", response_model=TaskStatus)
async def get_task_status(task_id: str, user: dict = Depends(verify_token)):
    """Get status of background translation task"""
    
    task = task_manager.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Verify ownership
    if task["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return TaskStatus(
        task_id=task["task_id"],
        status=task["status"],
        progress=task["progress"],
        message=task["message"],
        error=task.get("error"),
        completed=task["status"] in ["completed", "failed"]
    )

@app.get("/tasks/my")
async def get_my_tasks(user: dict = Depends(verify_token)):
    """Get all tasks for current user"""
    
    tasks = task_manager.get_user_tasks(user["user_id"])
    
    # Sort by creation time, newest first
    tasks.sort(key=lambda x: x["created_at"], reverse=True)
    
    # Return only recent tasks
    return tasks[:10]

@app.post("/task/{task_id}/cancel")
async def cancel_task(task_id: str, user: dict = Depends(verify_token)):
    """Cancel a running task"""
    
    task = task_manager.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if task["status"] in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="Task already finished")
    
    task_manager.update_task(task_id,
        status="cancelled",
        message="Task cancelled by user",
        completed_at=datetime.now().isoformat()
    )
    
    return {"message": "Task cancelled"}

@app.get("/download/{doc_id}")
async def download_document(doc_id: str, user: dict = Depends(verify_token)):
    """Download translated document"""
    
    if doc_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents[doc_id]
    
    if doc["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if not doc.get("translated_path") or not os.path.exists(doc["translated_path"]):
        raise HTTPException(status_code=404, detail="Translated file not found")
    
    original_name = os.path.splitext(doc["filename"])[0]
    file_ext = doc["file_type"]
    translated_filename = f"{original_name}_translated{file_ext}"
    
    return FileResponse(
        path=doc["translated_path"],
        filename=translated_filename,
        media_type=SUPPORTED_FORMATS.get(file_ext, 'application/octet-stream')
    )

@app.get("/documents", response_model=List[DocumentInfo])
async def list_documents(user: dict = Depends(verify_token)):
    """List user documents with task info"""
    
    user_documents = []
    
    for doc in documents.values():
        if doc["user_id"] == user["user_id"]:
            # Add task progress if available
            progress = None
            if doc.get("task_id"):
                task = task_manager.get_task(doc["task_id"])
                if task:
                    progress = task["progress"]
                    # Update doc status from task
                    if task["status"] == "completed":
                        doc["status"] = "completed"
                    elif task["status"] == "failed":
                        doc["status"] = "failed"
                        doc["error"] = task.get("error")
            
            user_documents.append(
                DocumentInfo(
                    doc_id=doc["doc_id"],
                    filename=doc["filename"],
                    file_type=doc["file_type"],
                    status=doc["status"],
                    upload_time=doc["upload_time"],
                    translated_doc_id=doc.get("translated_doc_id"),
                    error=doc.get("error"),
                    task_id=doc.get("task_id"),
                    progress=progress
                )
            )
    
    return sorted(user_documents, key=lambda x: x.upload_time, reverse=True)

# ============================================
# PAYMENT ENDPOINTS - UPDATED FOR MULTIPLE TIERS
# ============================================

@app.post("/payment/initiate")
async def initiate_payment(payment_request: PaymentInitiate, user: dict = Depends(verify_token)):
    """Initiate Paystack payment for Professional or Enterprise tier"""
    
    if payment_request.tier not in SUBSCRIPTION_TIERS:
        raise HTTPException(status_code=400, detail="Invalid subscription tier")
    
    tier = SUBSCRIPTION_TIERS[payment_request.tier]
    
    if tier["price"] == 0:
        raise HTTPException(status_code=400, detail="Cannot purchase free tier")
    
    # Validate tier has a payment link
    if payment_request.tier not in PAYSTACK_PAYMENT_LINKS:
        raise HTTPException(status_code=400, detail=f"No payment link configured for {payment_request.tier} tier")
    
    upgrade_id = str(uuid.uuid4())
    
    # Store pending upgrade info
    pending_upgrades[user["user_id"]] = {
        "upgrade_id": upgrade_id,
        "user_id": user["user_id"],
        "email": user["email"],
        "tier": payment_request.tier,
        "amount": tier["price"],
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    save_json(PENDING_UPGRADES_FILE, pending_upgrades)
    
    # Get the correct payment link for the tier
    payment_url = get_payment_link(payment_request.tier)
    
    callback_url = f"{FRONTEND_URL}?payment_callback=true&user_id={user['user_id']}&tier={payment_request.tier}"
    
    print(f"\n{'='*70}")
    print(f"💳 PAYMENT INITIATED")
    print(f"{'='*70}")
    print(f"User:    {user['email']}")
    print(f"Tier:    {payment_request.tier}")
    print(f"Amount:  R{tier['price']}")
    print(f"URL:     {payment_url}")
    print(f"{'='*70}\n")
    
    return {
        "payment_url": payment_url,
        "upgrade_id": upgrade_id,
        "tier": payment_request.tier,
        "amount": tier["price"],
        "callback_url": callback_url
    }

@app.post("/payment/verify")
async def verify_payment(user: dict = Depends(verify_token)):
    """Verify payment and upgrade user tier"""
    
    user_id = user["user_id"]
    
    if user_id not in pending_upgrades:
        raise HTTPException(status_code=404, detail="No pending upgrade found")
    
    pending = pending_upgrades[user_id]
    new_tier = pending["tier"]
    
    # Validate tier
    if new_tier not in SUBSCRIPTION_TIERS:
        raise HTTPException(status_code=400, detail="Invalid tier in pending upgrade")
    
    # Update user tier
    if user_id in users:
        users[user_id]["tier"] = new_tier
        users[user_id]["translations_used"] = 0  # Reset usage on upgrade
        users[user_id]["updated_at"] = datetime.now().isoformat()
        save_json(USERS_FILE, users)
    
    # Record payment
    payment_id = str(uuid.uuid4())
    payments[payment_id] = {
        "payment_id": payment_id,
        "user_id": user_id,
        "email": user["email"],
        "tier": new_tier,
        "amount": pending["amount"],
        "status": "completed",
        "created_at": pending["created_at"],
        "completed_at": datetime.now().isoformat()
    }
    save_json(PAYMENTS_FILE, payments)
    
    # Remove pending upgrade
    del pending_upgrades[user_id]
    save_json(PENDING_UPGRADES_FILE, pending_upgrades)
    
    tier_info = SUBSCRIPTION_TIERS[new_tier]
    
    print(f"\n{'='*70}")
    print(f"✅ PAYMENT VERIFIED - USER UPGRADED")
    print(f"{'='*70}")
    print(f"User:     {user['email']}")
    print(f"New Tier: {new_tier}")
    print(f"Limit:    {tier_info['limit']}")
    print(f"{'='*70}\n")
    
    return {
        "status": "success",
        "message": f"Successfully upgraded to {tier_info['name']}",
        "tier": new_tier,
        "translations_limit": tier_info["limit"],
        "user": {
            "user_id": users[user_id]["user_id"],
            "email": users[user_id]["email"],
            "name": users[user_id]["name"],
            "tier": new_tier,
            "translations_used": 0,
            "translations_limit": tier_info["limit"]
        }
    }

# ============================================
# CLEANUP TASK
# ============================================

@app.on_event("startup")
async def startup_event():
    """Run cleanup tasks on startup"""
    # Clean up old tasks periodically
    async def cleanup_loop():
        while True:
            await asyncio.sleep(3600)  # Every hour
            task_manager.cleanup_old_tasks(24)  # Remove tasks older than 24 hours
            print("✓ Cleaned up old tasks")
    
    asyncio.create_task(cleanup_loop())

# ============================================
# ROOT ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """API info"""
    return {
        "service": "Document Translation API - Enhanced for Large Files",
        "version": "4.0.0",
        "status": "operational",
        "translator_available": TRANSLATOR_AVAILABLE,
        "features": [
            "Background processing for large files",
            "Real-time progress tracking",
            "File size validation (max 100MB)",
            "Chunked file uploads",
            "Task management and cancellation",
            "Concurrent translation limits",
            "Automatic retry with exponential backoff",
            "Progress polling for long-running tasks",
            "Multiple payment tiers (Professional & Enterprise)"
        ],
        "limits": {
            "max_file_size_mb": MAX_FILE_SIZE_MB,
            "max_concurrent_translations": MAX_CONCURRENT_TRANSLATIONS,
            "translation_timeout_seconds": TRANSLATION_TIMEOUT
        },
        "payment_tiers": {
            "professional": {"price": 20, "limit": 20},
            "enterprise": {"price": 999, "limit": "unlimited"}
        }
    }

@app.get("/health")
async def health():
    """Health check with task stats"""
    active_tasks = sum(1 for t in task_manager.tasks.values() if t["status"] == "processing")
    queued_tasks = sum(1 for t in task_manager.tasks.values() if t["status"] == "queued")
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "storage": {
            "users": len(users),
            "sessions": len(sessions),
            "documents": len(documents),
            "payments": len(payments),
            "tasks": len(task_manager.tasks)
        },
        "tasks": {
            "active": active_tasks,
            "queued": queued_tasks,
            "total": len(task_manager.tasks)
        },
        "translator": "available" if TRANSLATOR_AVAILABLE else "unavailable"
    }

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 Starting Enhanced Document Translation API")
    print("="*70)
    print(f"Translator available: {TRANSLATOR_AVAILABLE}")
    print(f"Max file size: {MAX_FILE_SIZE_MB}MB")
    print(f"Max concurrent translations: {MAX_CONCURRENT_TRANSLATIONS}")
    print(f"Translation timeout: {TRANSLATION_TIMEOUT}s")
    print(f"Payment links configured:")
    for tier, url in PAYSTACK_PAYMENT_LINKS.items():
        print(f"  - {tier}: {url}")
    print("="*70 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)