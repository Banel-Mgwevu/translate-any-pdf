"""
FastAPI REST API for Document Translation Service with Authentication & Payments

Features:
- User authentication (sign up, sign in)
- Payment tracking via PayFast webhooks
- Subscription management
- Document translation (DOCX and PDF)
- Multi-format support with auto-detection
- Translation quality metrics (BLEU, ChrF, METEOR)

IMPORTANT SETUP:
1. Install ngrok: https://ngrok.com/download
2. Run: ngrok http 8000
3. Copy ngrok URL and update BASE_URL below
4. Set passphrase in PayFast sandbox: https://sandbox.payfast.co.za
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request, Depends
from fastapi.responses import FileResponse, JSONResponse
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
import hmac
import urllib.parse
from datetime import datetime, timedelta
import shutil

# Import the existing DocumentTranslator
import sys
sys.path.insert(0, os.path.dirname(__file__))
from document_translator import DocumentTranslator

# Translation metrics imports
try:
    import sacrebleu
    from nltk.translate.meteor_score import meteor_score
    from nltk import word_tokenize
    import nltk
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    try:
        nltk.data.find('corpora/wordnet')
    except LookupError:
        nltk.download('wordnet', quiet=True)
    METRICS_SUPPORT = True
except ImportError:
    METRICS_SUPPORT = False
    print("Warning: Translation metrics not available. Install: pip install sacrebleu nltk")

# For text extraction from documents
try:
    import fitz  # PyMuPDF for PDFs
    from docx import Document as DocxDocument
    TEXT_EXTRACTION_SUPPORT = True
except ImportError:
    TEXT_EXTRACTION_SUPPORT = False
    print("Warning: Text extraction not fully available.")

# Initialize FastAPI app
app = FastAPI(
    title="Document Translation API",
    description="Translate DOCX and PDF documents with authentication and subscription management",
    version="2.1.0"
)

# ============================================
# PAYFAST CONFIGURATION - UPDATE THESE!
# ============================================

# Sandbox mode (set to False for production)
PAYFAST_SANDBOX = True

# Sandbox credentials (for testing)
SANDBOX_MERCHANT_ID = "10043424"
SANDBOX_MERCHANT_KEY = "31ujwiuzciw38"
SANDBOX_PASSPHRASE = "jt7NOE43FZPn"  # Set this in your sandbox dashboard

# Production credentials (for live)
PRODUCTION_MERCHANT_ID = "your-production-merchant-id"  # Replace with real ID
PRODUCTION_MERCHANT_KEY = "your-production-merchant-key"  # Replace with real key
PRODUCTION_PASSPHRASE = "your-production-passphrase"  # Replace with real passphrase

# ⚠️ CRITICAL: Update this with your ngrok URL or deployed server URL
# For local testing: Run "ngrok http 8000" and copy the URL here
# For production: Use your actual domain
BASE_URL = "https://translate-any-pdf.onrender.com"  # 🚨 CHANGE THIS!

# Get current credentials based on mode
PAYFAST_MERCHANT_ID = SANDBOX_MERCHANT_ID if PAYFAST_SANDBOX else PRODUCTION_MERCHANT_ID
PAYFAST_MERCHANT_KEY = SANDBOX_MERCHANT_KEY if PAYFAST_SANDBOX else PRODUCTION_MERCHANT_KEY
PAYFAST_PASSPHRASE = SANDBOX_PASSPHRASE if PAYFAST_SANDBOX else PRODUCTION_PASSPHRASE

# ============================================
# CORS CONFIGURATION
# ============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Local development
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:4173",
        # Production on Render
        "https://translation-app-frontend-lhk5.onrender.com",
        "https://translate-any-pdf.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Storage directories
UPLOAD_DIR = "/tmp/api_uploads"
OUTPUT_DIR = "/tmp/api_outputs"
DATA_DIR = "/tmp/api_data"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# JSON storage files
USERS_FILE = os.path.join(DATA_DIR, "users.json")
PAYMENTS_FILE = os.path.join(DATA_DIR, "payments.json")
SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.json")

# Supported file formats
SUPPORTED_FORMATS = {
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.pdf': 'application/pdf'
}

# Initialize storage
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

# In-memory storage (loaded from JSON)
users = load_json(USERS_FILE)
payments = load_json(PAYMENTS_FILE)
sessions = load_json(SESSIONS_FILE)
documents = {}  # Document metadata (session-based)

# Subscription tiers
SUBSCRIPTION_TIERS = {
    "free": {"name": "Free", "limit": 5, "price": 0},
    "professional": {"name": "Professional", "limit": 20, "price": 299},
    "enterprise": {"name": "Enterprise", "limit": float('inf'), "price": 999}
}

# Pydantic models
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

class SubscriptionRequest(BaseModel):
    tier: str  # 'professional' or 'enterprise'

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

class MetricsResponse(BaseModel):
    doc_id: str
    filename: str
    bleu_score: float
    chrf_score: float
    meteor_score: float
    comet_score: Optional[float] = None
    calculated_at: str
    segments_compared: int

# ============================================
# PAYFAST SIGNATURE CALCULATION (FIXED)
# ============================================

def calculate_payfast_signature(data: dict, passphrase: str = None) -> str:
    """
    Calculate PayFast signature correctly.
    
    CRITICAL: PayFast requires fields in document order (NOT alphabetical!)
    This follows the exact order from PayFast documentation.
    """
    
    # Define correct field order per PayFast docs
    field_order = [
        # Merchant details
        'merchant_id', 'merchant_key', 'return_url', 'cancel_url', 'notify_url',
        # Customer details
        'name_first', 'name_last', 'email_address', 'cell_number',
        # Transaction details
        'm_payment_id', 'amount', 'item_name', 'item_description',
        # Custom fields
        'custom_int1', 'custom_int2', 'custom_int3', 'custom_int4', 'custom_int5',
        'custom_str1', 'custom_str2', 'custom_str3', 'custom_str4', 'custom_str5',
        # Transaction options
        'email_confirmation', 'confirmation_address', 'payment_method',
        # Recurring billing
        'subscription_type', 'billing_date', 'recurring_amount', 'frequency', 'cycles'
    ]
    
    # Build parameter string in correct order
    param_list = []
    for key in field_order:
        if key in data and data[key] not in [None, '', 'None']:
            value = str(data[key]).strip()
            # Use quote_plus for URL encoding (spaces become +)
            encoded_value = urllib.parse.quote_plus(value)
            param_list.append(f"{key}={encoded_value}")
    
    param_string = "&".join(param_list)
    
    # Add passphrase if provided
    if passphrase:
        param_string += f"&passphrase={urllib.parse.quote_plus(passphrase)}"
    
    # Calculate MD5 hash
    signature = hashlib.md5(param_string.encode()).hexdigest()
    
    return signature

# Utility functions
def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token() -> str:
    """Generate a random session token"""
    return str(uuid.uuid4())

def get_file_extension(filename: str) -> str:
    """Get file extension in lowercase"""
    return os.path.splitext(filename)[1].lower()

def is_supported_format(filename: str) -> bool:
    """Check if file format is supported"""
    return get_file_extension(filename) in SUPPORTED_FORMATS

def get_media_type(filename: str) -> str:
    """Get media type for file"""
    ext = get_file_extension(filename)
    return SUPPORTED_FORMATS.get(ext, 'application/octet-stream')

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify authentication token and return user info"""
    token = credentials.credentials
    
    if token not in sessions:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    session = sessions[token]
    
    # Check if session expired (24 hours)
    session_time = datetime.fromisoformat(session["created_at"])
    if datetime.now() - session_time > timedelta(days=1):
        del sessions[token]
        save_json(SESSIONS_FILE, sessions)
        raise HTTPException(status_code=401, detail="Session expired")
    
    user_id = session["user_id"]
    if user_id not in users:
        raise HTTPException(status_code=401, detail="User not found")
    
    return users[user_id]

def extract_text_from_docx(docx_path: str) -> str:
    """Extract text from DOCX file"""
    try:
        doc = DocxDocument(docx_path)
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text)
        return "\n".join(full_text)
    except Exception as e:
        print(f"Error extracting text from DOCX: {e}")
        return ""

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF file"""
    try:
        doc = fitz.open(pdf_path)
        full_text = []
        for page in doc:
            text = page.get_text()
            if text.strip():
                full_text.append(text)
        doc.close()
        return "\n".join(full_text)
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def extract_text_from_document(file_path: str) -> str:
    """Extract text from document (auto-detect format)"""
    if file_path.lower().endswith('.docx'):
        return extract_text_from_docx(file_path)
    elif file_path.lower().endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    return ""

def calculate_translation_metrics(source_text: str, translated_text: str, source_lang: str, target_lang: str) -> Dict:
    """Calculate translation quality metrics"""
    if not METRICS_SUPPORT:
        raise HTTPException(status_code=503, detail="Metrics support not available")
    
    # Split texts into segments (by line)
    source_segments = [line.strip() for line in source_text.split('\n') if line.strip()]
    translated_segments = [line.strip() for line in translated_text.split('\n') if line.strip()]
    
    # Ensure we have same number of segments (use minimum)
    min_segments = min(len(source_segments), len(translated_segments))
    source_segments = source_segments[:min_segments]
    translated_segments = translated_segments[:min_segments]
    
    if not source_segments or not translated_segments:
        raise HTTPException(status_code=400, detail="No text content found for comparison")
    
    # Calculate BLEU score
    bleu = sacrebleu.corpus_bleu(translated_segments, [source_segments])
    bleu_score = bleu.score
    
    # Calculate ChrF score
    chrf = sacrebleu.corpus_chrf(translated_segments, [source_segments])
    chrf_score = chrf.score
    
    # Calculate METEOR score (average across all segments)
    meteor_scores = []
    for src, tgt in zip(source_segments, translated_segments):
        try:
            src_tokens = word_tokenize(src.lower())
            tgt_tokens = word_tokenize(tgt.lower())
            if src_tokens and tgt_tokens:
                score = meteor_score([src_tokens], tgt_tokens)
                meteor_scores.append(score)
        except Exception as e:
            print(f"METEOR calculation error: {e}")
            continue
    
    meteor_avg = sum(meteor_scores) / len(meteor_scores) if meteor_scores else 0.0
    
    return {
        "bleu_score": round(bleu_score, 2),
        "chrf_score": round(chrf_score, 2),
        "meteor_score": round(meteor_avg * 100, 2),
        "comet_score": None,
        "segments_compared": min_segments
    }

# ============================================
# AUTHENTICATION ENDPOINTS
# ============================================

@app.post("/auth/signup", response_model=AuthResponse)
async def sign_up(user_data: UserSignUp):
    """Register a new user"""
    
    # Check if user already exists
    if any(u["email"] == user_data.email for u in users.values()):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
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
    
    # Return user info
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
    """Sign in an existing user"""
    
    # Find user by email
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
    
    # Return user info
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
    
    # Find and remove session
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
    """Get current user information"""
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
# PAYMENT ENDPOINTS (FIXED)
# ============================================

@app.post("/payment/initiate")
async def initiate_payment(request: SubscriptionRequest, user: dict = Depends(verify_token)):
    """Initiate a payment for subscription upgrade"""
    
    if request.tier not in ["professional", "enterprise"]:
        raise HTTPException(status_code=400, detail="Invalid subscription tier")
    
    if request.tier == user["tier"]:
        raise HTTPException(status_code=400, detail="Already subscribed to this tier")
    
    tier_info = SUBSCRIPTION_TIERS[request.tier]
    
    # Create payment record
    payment_id = str(uuid.uuid4())
    payment_record = {
        "payment_id": payment_id,
        "user_id": user["user_id"],
        "tier": request.tier,
        "amount": tier_info["price"],
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    payments[payment_id] = payment_record
    save_json(PAYMENTS_FILE, payments)
    
    # Build payment data in correct order
    payment_data = {
        'merchant_id': PAYFAST_MERCHANT_ID,
        'merchant_key': PAYFAST_MERCHANT_KEY,
        'return_url': f'{BASE_URL}/payment/success',
        'cancel_url': f'{BASE_URL}/payment/cancel',
        'notify_url': f'{BASE_URL}/payment/notify',
        'amount': f"{tier_info['price']:.2f}",
        'item_name': f"{tier_info['name']} Subscription",
        'item_description': f"Monthly subscription to {tier_info['name']} plan",
        'custom_str1': payment_id,
        'custom_str2': user["user_id"]
    }
    
    # Generate signature with passphrase
    signature = calculate_payfast_signature(payment_data, PAYFAST_PASSPHRASE)
    payment_data['signature'] = signature
    
    # PayFast URL
    payfast_url = "https://sandbox.payfast.co.za/eng/process" if PAYFAST_SANDBOX else "https://www.payfast.co.za/eng/process"
    
    # Log payment details
    print(f"\n{'='*70}")
    print(f"💳 PAYMENT INITIATED - {'SANDBOX MODE' if PAYFAST_SANDBOX else 'PRODUCTION'}")
    print(f"{'='*70}")
    print(f"Payment ID:    {payment_id}")
    print(f"Amount:        R{tier_info['price']:.2f}")
    print(f"Plan:          {tier_info['name']}")
    print(f"User:          {user['email']}")
    print(f"Notify URL:    {payment_data['notify_url']}")
    print(f"Signature:     {signature}")
    print(f"PayFast URL:   {payfast_url}")
    print(f"{'='*70}\n")
    
    # Check if notify_url is accessible
    if 'localhost' in BASE_URL or '127.0.0.1' in BASE_URL or 'your-ngrok-url' in BASE_URL:
        print("⚠️  WARNING: notify_url uses localhost or placeholder - webhooks will fail!")
        print("   1. Run: ngrok http 8000")
        print("   2. Copy ngrok URL")
        print("   3. Update BASE_URL in this file")
        print("   4. Restart the server\n")
    
    return {
        "payment_id": payment_id,
        "payment_url": payfast_url,
        "payment_data": payment_data,
        "message": "Redirect user to payment_url with payment_data"
    }

@app.post("/payment/notify")
async def payment_notify(request: Request):
    """PayFast IPN (Instant Payment Notification) webhook"""
    
    # Get form data
    form_data = await request.form()
    data = dict(form_data)
    
    print(f"\n{'='*70}")
    print(f"🔔 PAYFAST WEBHOOK RECEIVED")
    print(f"{'='*70}")
    for key, value in data.items():
        print(f"{key:20s}: {value}")
    print(f"{'='*70}\n")
    
    # Verify signature
    received_signature = data.get("signature", "")
    
    # Remove signature for verification
    verify_data = {k: v for k, v in data.items() if k != 'signature'}
    
    # Calculate expected signature
    calculated_signature = calculate_payfast_signature(verify_data, PAYFAST_PASSPHRASE)
    
    # Verify
    signature_valid = (received_signature == calculated_signature)
    
    print(f"🔐 SIGNATURE VERIFICATION:")
    print(f"   Received:   {received_signature}")
    print(f"   Calculated: {calculated_signature}")
    print(f"   Valid:      {'✅ YES' if signature_valid else '❌ NO'}\n")
    
    if not signature_valid:
        if PAYFAST_SANDBOX:
            print("⚠️  Signature mismatch in sandbox - continuing for debugging")
            print("   In production, this request would be rejected!\n")
        else:
            print("❌ SIGNATURE INVALID - Rejecting webhook")
            raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Get payment details
    payment_id = data.get("custom_str1")
    user_id = data.get("custom_str2")
    payment_status = data.get("payment_status")
    amount_gross = data.get("amount_gross")
    
    print(f"📋 PAYMENT DETAILS:")
    print(f"   Payment ID:  {payment_id}")
    print(f"   User ID:     {user_id}")
    print(f"   Status:      {payment_status}")
    print(f"   Amount:      R{amount_gross}\n")
    
    if not payment_id or payment_id not in payments:
        print(f"❌ Payment {payment_id} not found!\n")
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Update payment status
    payment = payments[payment_id]
    payment["status"] = "completed" if payment_status == "COMPLETE" else "failed"
    payment["updated_at"] = datetime.now().isoformat()
    payment["payfast_data"] = data
    
    save_json(PAYMENTS_FILE, payments)
    
    # If payment successful, upgrade user subscription
    if payment_status == "COMPLETE":
        if user_id in users:
            users[user_id]["tier"] = payment["tier"]
            users[user_id]["translations_used"] = 0  # Reset usage on upgrade
            users[user_id]["updated_at"] = datetime.now().isoformat()
            save_json(USERS_FILE, users)
            print(f"✅ PAYMENT SUCCESSFUL - User {user_id} upgraded to {payment['tier']}\n")
        else:
            print(f"❌ User {user_id} not found!\n")
    else:
        print(f"❌ PAYMENT FAILED or CANCELLED\n")
    
    print(f"{'='*70}")
    print(f"Returning 200 OK to PayFast")
    print(f"{'='*70}\n")
    
    return {"status": "success"}

@app.get("/payment/status/{payment_id}")
async def get_payment_status(payment_id: str, user: dict = Depends(verify_token)):
    """Check payment status"""
    
    if payment_id not in payments:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment = payments[payment_id]
    
    # Verify user owns this payment
    if payment["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to view this payment")
    
    return payment

@app.get("/payments")
async def list_payments(user: dict = Depends(verify_token)):
    """List all payments for current user"""
    
    user_payments = [
        p for p in payments.values() 
        if p["user_id"] == user["user_id"]
    ]
    
    return {
        "total": len(user_payments),
        "payments": sorted(user_payments, key=lambda x: x["created_at"], reverse=True)
    }

# ============================================
# DOCUMENT TRANSLATION ENDPOINTS
# ============================================

@app.post("/upload")
async def upload_document(file: UploadFile = File(...), user: dict = Depends(verify_token)):
    """Upload a document for translation (supports DOCX and PDF)"""
    
    # Check translation limit
    tier_info = SUBSCRIPTION_TIERS[user["tier"]]
    if user["translations_used"] >= tier_info["limit"]:
        raise HTTPException(
            status_code=403, 
            detail=f"Translation limit reached ({tier_info['limit']} translations per month). Please upgrade your plan."
        )
    
    # Validate file format
    if not is_supported_format(file.filename):
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format. Supported formats: {', '.join(SUPPORTED_FORMATS.keys())}"
        )
    
    doc_id = str(uuid.uuid4())
    file_ext = get_file_extension(file.filename)
    upload_path = os.path.join(UPLOAD_DIR, f"{doc_id}{file_ext}")
    
    try:
        with open(upload_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    documents[doc_id] = {
        "doc_id": doc_id,
        "user_id": user["user_id"],
        "filename": file.filename,
        "file_type": file_ext,
        "upload_path": upload_path,
        "upload_time": datetime.now().isoformat(),
        "status": "uploaded"
    }
    
    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "file_type": file_ext,
        "status": "uploaded",
        "message": f"File uploaded successfully. Format: {file_ext.upper()}"
    }

@app.post("/translate")
async def translate_document(request: TranslationRequest, user: dict = Depends(verify_token)):
    """Translate a document (DOCX or PDF)"""
    
    if request.doc_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents[request.doc_id]
    
    # Verify ownership
    if doc["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check translation limit
    tier_info = SUBSCRIPTION_TIERS[user["tier"]]
    if user["translations_used"] >= tier_info["limit"]:
        raise HTTPException(status_code=403, detail="Translation limit reached")
    
    try:
        doc["status"] = "translating"
        
        translated_doc_id = str(uuid.uuid4())
        file_ext = doc["file_type"]
        output_path = os.path.join(OUTPUT_DIR, f"{translated_doc_id}{file_ext}")
        
        # Initialize translator
        translator = DocumentTranslator(
            source_lang=request.source_lang,
            target_lang=request.target_lang
        )
        
        # Translate document
        print(f"\n{'='*60}")
        print(f"API Translation Request")
        print(f"{'='*60}")
        print(f"User: {user['email']}")
        print(f"File: {doc['filename']} ({file_ext.upper()})")
        print(f"Source Lang: {request.source_lang}")
        print(f"Target Lang: {request.target_lang}")
        print(f"{'='*60}\n")
        
        translator.translate_document(doc["upload_path"], output_path)
        
        doc["status"] = "completed"
        doc["translated_path"] = output_path
        doc["translated_doc_id"] = translated_doc_id
        doc["source_lang"] = request.source_lang
        doc["target_lang"] = request.target_lang
        doc["translation_time"] = datetime.now().isoformat()
        
        # Increment usage counter
        users[user["user_id"]]["translations_used"] += 1
        users[user["user_id"]]["updated_at"] = datetime.now().isoformat()
        save_json(USERS_FILE, users)
        
        print(f"Translation completed successfully!")
        print(f"Translated segments: {len(translator.translation_cache)}")
        print(f"User usage: {users[user['user_id']]['translations_used']}/{tier_info['limit']}\n")
        
        return {
            "doc_id": request.doc_id,
            "status": "completed",
            "translated_doc_id": translated_doc_id,
            "file_type": file_ext,
            "segments_translated": len(translator.translation_cache),
            "source_lang": request.source_lang,
            "target_lang": request.target_lang,
            "translations_remaining": tier_info["limit"] - users[user["user_id"]]["translations_used"]
        }
        
    except Exception as e:
        doc["status"] = "failed"
        doc["error"] = str(e)
        print(f"Translation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

@app.get("/download/{doc_id}")
async def download_document(doc_id: str, user: dict = Depends(verify_token)):
    """Download a translated document"""
    
    if doc_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents[doc_id]
    
    if doc["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if not doc.get("translated_path") or not os.path.exists(doc["translated_path"]):
        raise HTTPException(status_code=404, detail="Translated file not found")
    
    # Generate appropriate filename
    original_name = os.path.splitext(doc["filename"])[0]
    file_ext = doc["file_type"]
    translated_filename = f"{original_name}_translated{file_ext}"
    
    return FileResponse(
        path=doc["translated_path"],
        filename=translated_filename,
        media_type=get_media_type(doc["filename"])
    )

@app.get("/metrics/{doc_id}", response_model=MetricsResponse)
async def get_translation_metrics(doc_id: str, user: dict = Depends(verify_token)):
    """Calculate and return translation quality metrics for a document"""
    
    if not METRICS_SUPPORT or not TEXT_EXTRACTION_SUPPORT:
        raise HTTPException(
            status_code=503, 
            detail="Translation metrics not available. Install required packages: pip install sacrebleu nltk python-docx pymupdf"
        )
    
    if doc_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents[doc_id]
    
    if doc["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if doc["status"] != "completed":
        raise HTTPException(status_code=400, detail="Document not yet translated")
    
    if not doc.get("translated_path") or not os.path.exists(doc["translated_path"]):
        raise HTTPException(status_code=404, detail="Translated document not found")
    
    try:
        print(f"\n{'='*60}")
        print(f"Calculating Translation Metrics")
        print(f"{'='*60}")
        print(f"Document: {doc['filename']}")
        print(f"Source -> Target: {doc.get('source_lang', 'auto')} -> {doc.get('target_lang', 'unknown')}")
        print(f"{'='*60}\n")
        
        # Extract text from both documents
        source_text = extract_text_from_document(doc["upload_path"])
        translated_text = extract_text_from_document(doc["translated_path"])
        
        if not source_text or not translated_text:
            raise HTTPException(status_code=400, detail="Could not extract text from documents")
        
        metrics = calculate_translation_metrics(
            source_text, 
            translated_text,
            doc.get("source_lang", "auto"),
            doc.get("target_lang", "unknown")
        )
        
        print(f"\nMetrics Results:")
        print(f"  BLEU Score:   {metrics['bleu_score']}")
        print(f"  ChrF Score:   {metrics['chrf_score']}")
        print(f"  METEOR Score: {metrics['meteor_score']}")
        print(f"  Segments:     {metrics['segments_compared']}")
        print(f"{'='*60}\n")
        
        return MetricsResponse(
            doc_id=doc_id,
            filename=doc["filename"],
            bleu_score=metrics["bleu_score"],
            chrf_score=metrics["chrf_score"],
            meteor_score=metrics["meteor_score"],
            comet_score=metrics.get("comet_score"),
            calculated_at=datetime.now().isoformat(),
            segments_compared=metrics["segments_compared"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error calculating metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate metrics: {str(e)}")

@app.get("/documents", response_model=List[DocumentInfo])
async def list_documents(user: dict = Depends(verify_token)):
    """List all documents for current user"""
    
    user_documents = [
        DocumentInfo(
            doc_id=doc["doc_id"],
            filename=doc["filename"],
            file_type=doc["file_type"],
            status=doc["status"],
            upload_time=doc["upload_time"],
            translated_doc_id=doc.get("translated_doc_id")
        )
        for doc in documents.values()
        if doc["user_id"] == user["user_id"]
    ]
    
    return sorted(user_documents, key=lambda x: x.upload_time, reverse=True)

@app.get("/document/{doc_id}")
async def get_document_info(doc_id: str, user: dict = Depends(verify_token)):
    """Get detailed information about a document"""
    
    if doc_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents[doc_id]
    
    if doc["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Remove sensitive paths from response
    response_doc = {k: v for k, v in doc.items() if k not in ["upload_path", "translated_path"]}
    
    return response_doc

@app.delete("/document/{doc_id}")
async def delete_document(doc_id: str, user: dict = Depends(verify_token)):
    """Delete a document and its translations"""
    
    if doc_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents[doc_id]
    
    if doc["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Delete files
    try:
        if os.path.exists(doc["upload_path"]):
            os.remove(doc["upload_path"])
        
        if doc.get("translated_path") and os.path.exists(doc["translated_path"]):
            os.remove(doc["translated_path"])
    except Exception as e:
        print(f"Error deleting files: {e}")
    
    # Remove from documents
    del documents[doc_id]
    
    return {"message": "Document deleted successfully"}

@app.get("/stats")
async def get_user_stats(user: dict = Depends(verify_token)):
    """Get user statistics"""
    
    tier_info = SUBSCRIPTION_TIERS[user["tier"]]
    
    # Count user documents
    user_docs = [doc for doc in documents.values() if doc["user_id"] == user["user_id"]]
    completed_docs = [doc for doc in user_docs if doc["status"] == "completed"]
    
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "tier": user["tier"],
        "translations_used": user["translations_used"],
        "translations_limit": tier_info["limit"],
        "translations_remaining": tier_info["limit"] - user["translations_used"] if tier_info["limit"] != float('inf') else "unlimited",
        "total_documents": len(user_docs),
        "completed_translations": len(completed_docs),
        "member_since": user["created_at"],
        "metrics_available": METRICS_SUPPORT and TEXT_EXTRACTION_SUPPORT
    }

@app.get("/supported-formats")
async def get_supported_formats():
    """Get list of supported file formats"""
    return {
        "formats": list(SUPPORTED_FORMATS.keys()),
        "details": {
            ".docx": {
                "name": "Microsoft Word Document",
                "features": [
                    "Full formatting preservation",
                    "Images and graphics",
                    "Tables and lists",
                    "Headers and footers",
                    "Exact layout maintained"
                ]
            },
            ".pdf": {
                "name": "Portable Document Format",
                "features": [
                    "Text extraction and translation",
                    "Paragraph structure maintained",
                    "Page breaks preserved",
                    "Best for text-heavy documents"
                ],
                "limitations": [
                    "Complex layouts may be simplified",
                    "Images not included in output",
                    "Only text-based PDFs (not scanned images)"
                ]
            }
        }
    }

@app.get("/languages")
async def get_supported_languages():
    """Get list of supported languages"""
    return {
        "popular": {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "zh-cn": "Chinese (Simplified)",
            "ja": "Japanese",
            "ko": "Korean",
            "ar": "Arabic",
            "af": "Afrikaans"
        },
        "note": "Supports 100+ languages via Google Translate. Use 'auto' for automatic source language detection."
    }

@app.get("/")
async def root():
    """API information"""
    return {
        "service": "Document Translation API with Authentication & Metrics",
        "version": "2.1.0",
        "mode": "SANDBOX" if PAYFAST_SANDBOX else "PRODUCTION",
        "features": [
            "User authentication",
            "Subscription management",
            "PayFast payment integration",
            "Multi-format document translation (DOCX, PDF)",
            "Usage tracking",
            "File format auto-detection",
            "100+ language support",
            "Translation quality metrics (BLEU, ChrF, METEOR)"
        ],
        "supported_formats": list(SUPPORTED_FORMATS.keys()),
        "metrics_available": METRICS_SUPPORT and TEXT_EXTRACTION_SUPPORT,
        "endpoints": {
            "docs": "/docs",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "mode": "SANDBOX" if PAYFAST_SANDBOX else "PRODUCTION",
        "storage": {
            "users": len(users),
            "payments": len(payments),
            "active_sessions": len(sessions),
            "documents": len(documents)
        },
        "supported_formats": list(SUPPORTED_FORMATS.keys()),
        "metrics_support": METRICS_SUPPORT and TEXT_EXTRACTION_SUPPORT
    }

# ============================================
# STARTUP
# ============================================

@app.on_event("startup")
async def startup():
    """Print configuration on startup"""
    print("\n" + "="*70)
    print("🚀 DOCUMENT TRANSLATION API v2.1")
    print("="*70)
    print(f"\n📋 PayFast Configuration:")
    print(f"   Mode:          {'SANDBOX (Test)' if PAYFAST_SANDBOX else 'PRODUCTION (Live)'}")
    print(f"   Merchant ID:   {PAYFAST_MERCHANT_ID}")
    print(f"   Base URL:      {BASE_URL}")
    print(f"   Notify URL:    {BASE_URL}/payment/notify")
    
    if 'your-ngrok-url' in BASE_URL or 'localhost' in BASE_URL:
        print(f"\n⚠️  WARNING: Update BASE_URL with your ngrok URL!")
        print(f"   1. Run: ngrok http 8000")
        print(f"   2. Copy the ngrok URL (e.g., https://abc123.ngrok.io)")
        print(f"   3. Update BASE_URL in this file")
        print(f"   4. Restart the server")
        print(f"\n   Without this, PayFast webhooks will not work!")
    else:
        print(f"\n✅ Configuration looks good!")
    
    print(f"\n📚 Features:")
    print(f"   ✓ User authentication")
    print(f"   ✓ PayFast payment integration")
    print(f"   ✓ DOCX & PDF translation")
    print(f"   ✓ Translation metrics: {'✓ Available' if METRICS_SUPPORT else '✗ Not available'}")
    
    print(f"\n🔗 URLs:")
    print(f"   API:           http://localhost:8000")
    print(f"   Docs:          http://localhost:8000/docs")
    print(f"   Health:        http://localhost:8000/health")
    
    if PAYFAST_SANDBOX:
        print(f"\n🧪 Sandbox Testing:")
        print(f"   PayFast:       https://sandbox.payfast.co.za")
        print(f"   Username:      sbtu01@payfast.io")
        print(f"   Password:      clientpass")
    
    print("="*70 + "\n")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)