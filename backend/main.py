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

@app.post("/api/v1/requirements", response_model=InvestigationResult)
async def process_requirement(requirement: BuyerRequirement):
    """
    Process buyer requirements and return mock supplier matches.
    This is a placeholder API - add your functionality here.
    """
    # Generate mock investigation ID
    investigation_id = f"inv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Mock supplier data
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
    
    return InvestigationResult(
        investigation_id=investigation_id,
        cached=False,
        suppliers=mock_suppliers,
        timestamp=datetime.now().isoformat()
    )


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
