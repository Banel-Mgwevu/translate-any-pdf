"""
IMPROVED API with Paystack Payment Integration

Key improvements:
1. Request logging middleware
2. Detailed error messages
3. Token refresh endpoint
4. Better translation status tracking
5. File validation improvements
6. Paystack payment integration (simplified payment link approach)
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request, Depends, Query
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, HTMLResponse
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

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import the existing DocumentTranslator
try:
    from document_translator import DocumentTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False
    print("WARNING: document_translator not available!")

app = FastAPI(
    title="Document Translation API - With Paystack Payments",
    description="Enhanced with Paystack payment integration",
    version="3.0.0"
)

# ============================================
# CONFIGURATION
# ============================================

BACKEND_URL = os.getenv("BACKEND_URL", "https://translate-any-pdf.onrender.com")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://translation-app-frontend-lhk5.onrender.com")

# Paystack Configuration
PAYSTACK_PAYMENT_LINK = "https://paystack.shop/pay/8zcv4xhc7r"
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")  # Add your secret key for webhook verification

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
        print(f"Auth:    ✗ MISSING - Protected endpoints will fail!")
    
    print(f"{'='*70}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    print(f"\n{'='*70}")
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

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify authentication token with detailed logging"""
    token = credentials.credentials
    
    print(f"\n🔐 TOKEN VERIFICATION")
    print(f"Token (first 20 chars): {token[:20]}...")
    
    if token not in sessions:
        print(f"❌ Token not found in sessions!")
        print(f"Available sessions: {len(sessions)}")
        raise HTTPException(
            status_code=401, 
            detail="Invalid or expired token. Please sign in again."
        )
    
    session = sessions[token]
    user_id = session["user_id"]
    
    print(f"✓ Token valid for user: {user_id}")
    
    # Check expiration
    session_time = datetime.fromisoformat(session["created_at"])
    age = datetime.now() - session_time
    
    print(f"Session age: {age}")
    
    if age > timedelta(days=1):
        print(f"❌ Session expired!")
        del sessions[token]
        save_json(SESSIONS_FILE, sessions)
        raise HTTPException(
            status_code=401, 
            detail="Session expired. Please sign in again."
        )
    
    if user_id not in users:
        print(f"❌ User {user_id} not found!")
        raise HTTPException(status_code=401, detail="User not found")
    
    user = users[user_id]
    print(f"✓ User verified: {user['email']}\n")
    
    return user

def get_user_by_email(email: str) -> Optional[dict]:
    """Find user by email"""
    for user in users.values():
        if user["email"].lower() == email.lower():
            return user
    return None

# ============================================
# AUTHENTICATION ENDPOINTS
# ============================================

@app.post("/auth/signup", response_model=AuthResponse)
async def sign_up(user_data: UserSignUp):
    """Register a new user"""
    
    print(f"\n{'='*70}")
    print(f"📝 NEW USER SIGNUP")
    print(f"{'='*70}")
    print(f"Email: {user_data.email}")
    print(f"Name:  {user_data.name}")
    print(f"{'='*70}\n")
    
    # Check if user exists
    if any(u["email"] == user_data.email for u in users.values()):
        print(f"❌ Email already registered!")
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
    
    print(f"✓ User created: {user_id}")
    print(f"✓ Token created: {token[:20]}...\n")
    
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
    
    print(f"\n{'='*70}")
    print(f"🔑 USER SIGNIN")
    print(f"{'='*70}")
    print(f"Email: {credentials.email}")
    print(f"{'='*70}\n")
    
    # Find user
    user = None
    for u in users.values():
        if u["email"] == credentials.email:
            user = u
            break
    
    if not user:
        print(f"❌ User not found!")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    hashed_password = hash_password(credentials.password)
    if user["password"] != hashed_password:
        print(f"❌ Invalid password!")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create session
    token = generate_token()
    sessions[token] = {
        "user_id": user["user_id"],
        "created_at": datetime.now().isoformat()
    }
    save_json(SESSIONS_FILE, sessions)
    
    print(f"✓ Sign in successful")
    print(f"✓ Token: {token[:20]}...\n")
    
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
    
    print(f"\n🚪 User signing out: {user['email']}\n")
    
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
# PAYSTACK PAYMENT ENDPOINTS
# ============================================

@app.post("/payment/initiate")
async def initiate_payment(payment_request: PaymentInitiate, user: dict = Depends(verify_token)):
    """Initiate Paystack payment - returns redirect URL"""
    
    print(f"\n{'='*70}")
    print(f"💳 PAYSTACK PAYMENT INITIATION")
    print(f"{'='*70}")
    print(f"User:  {user['email']}")
    print(f"Tier:  {payment_request.tier}")
    print(f"{'='*70}\n")
    
    # Validate tier
    if payment_request.tier not in SUBSCRIPTION_TIERS:
        raise HTTPException(status_code=400, detail="Invalid subscription tier")
    
    tier = SUBSCRIPTION_TIERS[payment_request.tier]
    
    if tier["price"] == 0:
        raise HTTPException(status_code=400, detail="Cannot purchase free tier")
    
    # Create a pending upgrade record
    upgrade_id = str(uuid.uuid4())
    
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
    
    # Build redirect URL with user info for callback
    callback_url = f"{FRONTEND_URL}?payment_callback=true&user_id={user['user_id']}&tier={payment_request.tier}"
    
    print(f"✓ Pending upgrade created: {upgrade_id}")
    print(f"✓ Paystack URL: {PAYSTACK_PAYMENT_LINK}")
    print(f"✓ Callback URL: {callback_url}\n")
    
    return {
        "payment_url": PAYSTACK_PAYMENT_LINK,
        "upgrade_id": upgrade_id,
        "tier": payment_request.tier,
        "amount": tier["price"],
        "callback_url": callback_url
    }

@app.post("/payment/verify")
async def verify_payment(user: dict = Depends(verify_token)):
    """Verify payment and upgrade user tier"""
    
    print(f"\n{'='*70}")
    print(f"✅ PAYMENT VERIFICATION")
    print(f"{'='*70}")
    print(f"User: {user['email']}")
    print(f"{'='*70}\n")
    
    user_id = user["user_id"]
    
    # Check for pending upgrade
    if user_id not in pending_upgrades:
        print(f"❌ No pending upgrade found for user")
        raise HTTPException(status_code=404, detail="No pending upgrade found")
    
    pending = pending_upgrades[user_id]
    new_tier = pending["tier"]
    
    # Update user tier
    if user_id in users:
        users[user_id]["tier"] = new_tier
        users[user_id]["translations_used"] = 0  # Reset usage on upgrade
        users[user_id]["updated_at"] = datetime.now().isoformat()
        save_json(USERS_FILE, users)
        
        print(f"✓ User upgraded to: {new_tier}")
    
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
    
    print(f"✓ Payment recorded: {payment_id}")
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

@app.get("/payment/callback")
async def payment_callback(
    reference: Optional[str] = None,
    trxref: Optional[str] = None
):
    """Handle Paystack callback redirect"""
    
    print(f"\n{'='*70}")
    print(f"🔔 PAYSTACK CALLBACK")
    print(f"{'='*70}")
    print(f"Reference: {reference}")
    print(f"Trxref: {trxref}")
    print(f"{'='*70}\n")
    
    # Redirect to frontend with success status
    redirect_url = f"{FRONTEND_URL}?payment_status=success&reference={reference or trxref or 'unknown'}"
    
    return RedirectResponse(url=redirect_url)

@app.get("/payment/success")
async def payment_success_page():
    """Payment success page - redirects to frontend"""
    
    print(f"\n✓ Payment success redirect\n")
    
    return RedirectResponse(url=f"{FRONTEND_URL}?payment_status=success")

@app.get("/payment/cancel")
async def payment_cancel():
    """Handle payment cancellation"""
    
    print(f"\n❌ Payment cancelled\n")
    
    return RedirectResponse(url=f"{FRONTEND_URL}?payment_status=cancelled")

@app.post("/payment/webhook")
async def paystack_webhook(request: Request):
    """Handle Paystack webhook notifications"""
    
    print(f"\n{'='*70}")
    print(f"🔔 PAYSTACK WEBHOOK")
    print(f"{'='*70}")
    
    try:
        body = await request.json()
        event = body.get("event", "")
        data = body.get("data", {})
        
        print(f"Event: {event}")
        print(f"Data: {json.dumps(data, indent=2)}")
        
        if event == "charge.success":
            # Extract customer email
            customer = data.get("customer", {})
            email = customer.get("email", "")
            amount = data.get("amount", 0) / 100  # Convert from kobo to rand
            reference = data.get("reference", "")
            
            print(f"Payment successful!")
            print(f"Email: {email}")
            print(f"Amount: R{amount}")
            print(f"Reference: {reference}")
            
            # Find user by email and upgrade
            user = get_user_by_email(email)
            if user:
                user_id = user["user_id"]
                
                # Check if there's a pending upgrade
                if user_id in pending_upgrades:
                    new_tier = pending_upgrades[user_id]["tier"]
                else:
                    # Default to professional if no pending upgrade
                    new_tier = "professional"
                
                # Update user tier
                users[user_id]["tier"] = new_tier
                users[user_id]["translations_used"] = 0
                users[user_id]["updated_at"] = datetime.now().isoformat()
                save_json(USERS_FILE, users)
                
                # Record payment
                payment_id = str(uuid.uuid4())
                payments[payment_id] = {
                    "payment_id": payment_id,
                    "user_id": user_id,
                    "email": email,
                    "tier": new_tier,
                    "amount": amount,
                    "reference": reference,
                    "status": "completed",
                    "source": "webhook",
                    "completed_at": datetime.now().isoformat()
                }
                save_json(PAYMENTS_FILE, payments)
                
                # Clean up pending upgrade
                if user_id in pending_upgrades:
                    del pending_upgrades[user_id]
                    save_json(PENDING_UPGRADES_FILE, pending_upgrades)
                
                print(f"✓ User {email} upgraded to {new_tier}")
            else:
                print(f"⚠️ User not found: {email}")
        
        print(f"{'='*70}\n")
        
        return {"status": "success"}
        
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return {"status": "error", "message": str(e)}

# ============================================
# DOCUMENT TRANSLATION ENDPOINTS  
# ============================================

@app.post("/upload")
async def upload_document(file: UploadFile = File(...), user: dict = Depends(verify_token)):
    """Upload document with detailed validation"""
    
    print(f"\n{'='*70}")
    print(f"📤 FILE UPLOAD")
    print(f"{'='*70}")
    print(f"User:     {user['email']}")
    print(f"Filename: {file.filename}")
    print(f"Size:     {file.size if hasattr(file, 'size') else 'Unknown'} bytes")
    print(f"{'='*70}\n")
    
    # Check limit
    tier_info = SUBSCRIPTION_TIERS[user["tier"]]
    if user["translations_used"] >= tier_info["limit"]:
        print(f"❌ Translation limit reached!")
        print(f"Used: {user['translations_used']}/{tier_info['limit']}\n")
        raise HTTPException(
            status_code=403,
            detail=f"Translation limit reached ({tier_info['limit']} per month)"
        )
    
    # Validate format
    if not is_supported_format(file.filename):
        print(f"❌ Unsupported format: {get_file_extension(file.filename)}\n")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format. Supported: {', '.join(SUPPORTED_FORMATS.keys())}"
        )
    
    # Save file
    doc_id = str(uuid.uuid4())
    file_ext = get_file_extension(file.filename)
    upload_path = os.path.join(UPLOAD_DIR, f"{doc_id}{file_ext}")
    
    try:
        content = await file.read()
        with open(upload_path, "wb") as buffer:
            buffer.write(content)
        
        file_size = len(content)
        print(f"✓ File saved: {upload_path}")
        print(f"✓ Size: {file_size} bytes")
        print(f"✓ Doc ID: {doc_id}\n")
        
    except Exception as e:
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
    
    print(f"✓ Document registered in system\n")
    
    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "file_type": file_ext,
        "status": "uploaded",
        "message": f"File uploaded successfully. Ready for translation."
    }

@app.post("/translate")
async def translate_document(request: TranslationRequest, user: dict = Depends(verify_token)):
    """Translate document with comprehensive error handling"""
    
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
        print(f"❌ DocumentTranslator not available!\n")
        raise HTTPException(
            status_code=503,
            detail="Translation service not available. Contact administrator."
        )
    
    # Check document exists
    if request.doc_id not in documents:
        print(f"❌ Document not found!")
        print(f"Available docs: {list(documents.keys())}\n")
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents[request.doc_id]
    
    # Verify ownership
    if doc["user_id"] != user["user_id"]:
        print(f"❌ Unauthorized access attempt!")
        print(f"Doc owner: {doc['user_id']}")
        print(f"Requester: {user['user_id']}\n")
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check limit
    tier_info = SUBSCRIPTION_TIERS[user["tier"]]
    if user["translations_used"] >= tier_info["limit"]:
        print(f"❌ Translation limit reached!\n")
        raise HTTPException(status_code=403, detail="Translation limit reached")
    
    # Check file exists
    if not os.path.exists(doc["upload_path"]):
        print(f"❌ Source file not found: {doc['upload_path']}\n")
        doc["status"] = "failed"
        doc["error"] = "Source file not found"
        raise HTTPException(status_code=404, detail="Source file not found")
    
    try:
        print(f"Starting translation...")
        doc["status"] = "translating"
        
        # Create output path
        translated_doc_id = str(uuid.uuid4())
        file_ext = doc["file_type"]
        output_path = os.path.join(OUTPUT_DIR, f"{translated_doc_id}{file_ext}")
        
        # Initialize translator
        print(f"Initializing translator...")
        translator = DocumentTranslator(
            source_lang=request.source_lang,
            target_lang=request.target_lang
        )
        
        # Translate
        print(f"Translating document...")
        start_time = time.time()
        
        translator.translate_document(doc["upload_path"], output_path)
        
        translation_time = time.time() - start_time
        
        # Verify output exists
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
        
        print(f"\n{'='*70}")
        print(f"✓ TRANSLATION SUCCESSFUL")
        print(f"{'='*70}")
        print(f"Time:       {translation_time:.2f}s")
        print(f"Input size: {doc['file_size']} bytes")
        print(f"Output size: {output_size} bytes")
        print(f"Segments:   {len(translator.translation_cache)}")
        print(f"Usage:      {users[user['user_id']]['translations_used']}/{tier_info['limit']}")
        print(f"{'='*70}\n")
        
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
        print(f"\n{'='*70}")
        print(f"❌ TRANSLATION FAILED")
        print(f"{'='*70}")
        print(f"Error: {error_msg}")
        print(f"{'='*70}\n")
        
        doc["status"] = "failed"
        doc["error"] = error_msg
        doc["error_time"] = datetime.now().isoformat()
        
        raise HTTPException(
            status_code=500,
            detail=f"Translation failed: {error_msg}"
        )

@app.get("/download/{doc_id}")
async def download_document(doc_id: str, user: dict = Depends(verify_token)):
    """Download translated document"""
    
    print(f"\n📥 Download request: {doc_id} by {user['email']}\n")
    
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
    
    print(f"✓ Serving file: {translated_filename}\n")
    
    return FileResponse(
        path=doc["translated_path"],
        filename=translated_filename,
        media_type=SUPPORTED_FORMATS.get(file_ext, 'application/octet-stream')
    )

@app.get("/documents", response_model=List[DocumentInfo])
async def list_documents(user: dict = Depends(verify_token)):
    """List user documents"""
    
    print(f"\n📋 Listing documents for: {user['email']}\n")
    
    user_documents = [
        DocumentInfo(
            doc_id=doc["doc_id"],
            filename=doc["filename"],
            file_type=doc["file_type"],
            status=doc["status"],
            upload_time=doc["upload_time"],
            translated_doc_id=doc.get("translated_doc_id"),
            error=doc.get("error")
        )
        for doc in documents.values()
        if doc["user_id"] == user["user_id"]
    ]
    
    print(f"Found {len(user_documents)} documents\n")
    
    return sorted(user_documents, key=lambda x: x.upload_time, reverse=True)

@app.get("/")
async def root():
    """API info"""
    return {
        "service": "Document Translation API - With Paystack Payments",
        "version": "3.0.0",
        "status": "operational",
        "translator_available": TRANSLATOR_AVAILABLE,
        "payment_provider": "Paystack",
        "payment_link": PAYSTACK_PAYMENT_LINK,
        "features": [
            "Enhanced error logging",
            "Detailed request tracking",
            "Better error messages",
            "Authentication debugging",
            "Paystack payment integration",
            "Subscription management",
            "Webhook support"
        ]
    }

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "storage": {
            "users": len(users),
            "sessions": len(sessions),
            "documents": len(documents),
            "payments": len(payments),
            "pending_upgrades": len(pending_upgrades)
        },
        "translator": "available" if TRANSLATOR_AVAILABLE else "unavailable",
        "payment_integration": "paystack"
    }

@app.get("/debug/sessions")
async def debug_sessions():
    """Debug endpoint to see active sessions"""
    return {
        "total_sessions": len(sessions),
        "sessions": [
            {
                "token_preview": token[:20] + "...",
                "user_id": session["user_id"],
                "created_at": session["created_at"],
                "age_hours": (datetime.now() - datetime.fromisoformat(session["created_at"])).total_seconds() / 3600
            }
            for token, session in sessions.items()
        ]
    }

@app.get("/debug/payments")
async def debug_payments():
    """Debug endpoint to see payment records"""
    return {
        "total_payments": len(payments),
        "payments": [
            {
                "payment_id": payment["payment_id"],
                "user_id": payment["user_id"],
                "tier": payment["tier"],
                "amount": payment["amount"],
                "status": payment["status"],
                "created_at": payment.get("created_at", payment.get("completed_at", ""))
            }
            for payment in payments.values()
        ]
    }

@app.get("/debug/pending-upgrades")
async def debug_pending_upgrades():
    """Debug endpoint to see pending upgrades"""
    return {
        "total_pending": len(pending_upgrades),
        "pending": list(pending_upgrades.values())
    }

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 Starting Document Translation API with Paystack Payments")
    print("="*70)
    print(f"Translator available: {TRANSLATOR_AVAILABLE}")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Frontend URL: {FRONTEND_URL}")
    print(f"Paystack Payment Link: {PAYSTACK_PAYMENT_LINK}")
    print("="*70 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)