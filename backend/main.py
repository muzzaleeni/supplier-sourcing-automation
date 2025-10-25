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
        "https://*.lovable.app",  # Lovable preview
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
    company_name: str
    contact_email: str
    contact_name: str
    pricing: str
    lead_time: str
    capabilities: str
    confidence_score: float
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
            company_name="TechSupply Manufacturing Ltd.",
            contact_email="sales@techsupply.com",
            contact_name="Sarah Johnson",
            pricing="$15-22 per unit (volume discounts available)",
            lead_time="8-10 weeks for initial order",
            capabilities="ISO 9001:2015 certified, 15+ years in industrial sensors, digital I2C expertise, IP67 housing production",
            confidence_score=0.92,
            conversation_log=[
                {
                    "from": "buyer",
                    "to": "sales@techsupply.com",
                    "subject": "RFQ: Industrial Temperature Sensors",
                    "message": f"Hello, we're interested in sourcing {requirement.quantity} of temperature sensors..."
                },
                {
                    "from": "sales@techsupply.com",
                    "to": requirement.email,
                    "subject": "Re: RFQ: Industrial Temperature Sensors",
                    "message": "Thank you for your inquiry. We can definitely help with your requirements..."
                }
            ]
        ),
        SupplierMatch(
            company_name="GlobalSensor Industries",
            contact_email="info@globalsensor.com",
            contact_name="Michael Chen",
            pricing="$18-25 per unit",
            lead_time="6-8 weeks",
            capabilities="Specialized in temperature sensors, I2C interfaces, automotive-grade components",
            confidence_score=0.87,
            conversation_log=[
                {
                    "from": "buyer",
                    "to": "info@globalsensor.com",
                    "subject": "Product Inquiry",
                    "message": "We need industrial temperature sensors with digital output..."
                }
            ]
        ),
        SupplierMatch(
            company_name="Precision Components Co.",
            contact_email="quotes@precisioncomp.com",
            contact_name="Emily Rodriguez",
            pricing="$20-28 per unit",
            lead_time="10-12 weeks",
            capabilities="Custom sensor solutions, IP67/IP68 rated housings, -40°C to 150°C range",
            confidence_score=0.83,
            conversation_log=[
                {
                    "from": "buyer",
                    "to": "quotes@precisioncomp.com",
                    "subject": "Temperature Sensor Quote Request",
                    "message": "Looking for a quote on industrial temperature sensors..."
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
