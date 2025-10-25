import os
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv

load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Tacto Track API", version="1.0.0")

# CORS middleware - Allow Lovable preview and local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=r"https://.*\.lovable\.app",  # Support all Lovable subdomains
)


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class BuyerRequirement(BaseModel):
    companyName: str
    contactName: str
    email: EmailStr
    phone: str
    productDescription: str
    quantity: str
    budgetRange: str
    timeline: str
    specifications: Optional[str] = None


class SupplierMatch(BaseModel):
    name: str
    contact_email: str
    contact_phone: str
    website: str
    location: str
    match_score: int
    capabilities: List[str]
    conversation_log: List[dict]


class InvestigationResult(BaseModel):
    investigation_id: str
    cached: bool
    suppliers: List[SupplierMatch]
    timestamp: str


# ============================================================================
# API ENDPOINTS
# ============================================================================

# In-memory storage for demo (in production, use a database)
investigations = {}

@app.post("/api/v1/requirements")
async def process_requirements(requirement: BuyerRequirement):
    """
    Process buyer requirements and initiate async investigation.
    Returns immediately with investigation_id and processing status.
    """
    investigation_id = f"INV-{abs(hash(requirement.email + str(requirement.companyName))) % 10000000}"
    
    # Store investigation status
    investigations[investigation_id] = {
        "status": "processing",
        "progress": 0,
        "message": "Initializing AI agents...",
        "requirement": requirement,
        "created_at": datetime.now()
    }
    
    return {
        "investigation_id": investigation_id,
        "status": "processing",
        "message": "Investigation started. Poll /api/v1/investigations/{id}/status for updates."
    }


@app.get("/api/v1/investigations/{investigation_id}/status")
async def get_investigation_status(investigation_id: str):
    """
    Get the current status of an investigation.
    Simulates progressive status updates until completion.
    """
    if investigation_id not in investigations:
        return {
            "investigation_id": investigation_id,
            "status": "error",
            "progress": 0,
            "message": "Investigation not found"
        }
    
    investigation = investigations[investigation_id]
    requirement = investigation["requirement"]
    
    # Calculate elapsed time to determine status
    elapsed = (datetime.now() - investigation["created_at"]).total_seconds()
    
    # Progressive status simulation
    if elapsed < 5:
        status = "processing"
        progress = 15
        message = "Analyzing your requirements with AI..."
    elif elapsed < 10:
        status = "searching"
        progress = 35
        message = "Searching database of 247,000+ suppliers worldwide..."
    elif elapsed < 15:
        status = "searching"
        progress = 55
        message = "Found 1,247 potential matches. Filtering by capabilities..."
    elif elapsed < 20:
        status = "contacting"
        progress = 75
        message = "AI agents reaching out to top 10 suppliers..."
    elif elapsed < 25:
        status = "contacting"
        progress = 90
        message = "Collecting responses and verifying credentials..."
    else:
        status = "completed"
        progress = 100
        message = "Investigation complete!"
    
    # If completed, return suppliers
    if status == "completed":
        mock_suppliers = [
            SupplierMatch(
                name="TechSupply Manufacturing Ltd.",
                contact_email="sales@techsupply.com",
                contact_phone="+1-555-0123",
                website="https://techsupply.com",
                location="San Jose, CA, USA",
                match_score=92,
                capabilities=["ISO 9001:2015 certified", "15+ years in industrial sensors", "Digital I2C expertise", "IP67 housing production"],
                conversation_log=[
                    {
                        "role": "assistant",
                        "content": f"Sent inquiry to sales@techsupply.com for {requirement.quantity} temperature sensors",
                        "timestamp": "2024-01-15 10:30:00"
                    },
                    {
                        "role": "assistant",
                        "content": "Received positive response. Company can meet requirements with 8-10 week lead time.",
                        "timestamp": "2024-01-15 14:45:00"
                    }
                ]
            ),
            SupplierMatch(
                name="GlobalSensor Industries",
                contact_email="info@globalsensor.com",
                contact_phone="+1-555-0456",
                website="https://globalsensor.com",
                location="Shenzhen, China",
                match_score=87,
                capabilities=["Specialized in temperature sensors", "I2C interfaces", "Automotive-grade components"],
                conversation_log=[
                    {
                        "role": "assistant",
                        "content": "Contacted GlobalSensor Industries regarding temperature sensor requirements",
                        "timestamp": "2024-01-15 11:00:00"
                    }
                ]
            ),
            SupplierMatch(
                name="Precision Components Co.",
                contact_email="quotes@precisioncomp.com",
                contact_phone="+1-555-0789",
                website="https://precisioncomp.com",
                location="Munich, Germany",
                match_score=83,
                capabilities=["Custom sensor solutions", "IP67/IP68 rated housings", "-40°C to 150°C range"],
                conversation_log=[
                    {
                        "role": "assistant",
                        "content": "Sent quote request to Precision Components Co.",
                        "timestamp": "2024-01-15 11:30:00"
                    }
                ]
            )
        ]
        
        return {
            "investigation_id": investigation_id,
            "status": status,
            "progress": progress,
            "message": message,
            "suppliers": [s.model_dump() for s in mock_suppliers]
        }
    
    # Still processing
    return {
        "investigation_id": investigation_id,
        "status": status,
        "progress": progress,
        "message": message
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
