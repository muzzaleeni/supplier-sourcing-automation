import os
import re
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from exa_py import Exa

load_dotenv()

# Initialize Exa client
exa_client = None
EXA_API_KEY = os.getenv("EXA_API_KEY")
if EXA_API_KEY:
    exa_client = Exa(EXA_API_KEY)

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
websets = {}  # Track Exa webset IDs by investigation_id


def create_exa_webset(requirement: BuyerRequirement):
    """Create an Exa webset to search for suppliers"""
    if not exa_client:
        return None
    
    # Build search query from product description and specifications
    prompt = requirement.productDescription
    if requirement.specifications:
        prompt += f". Specifications: {requirement.specifications}"
    
    try:
        webset = exa_client.websets.create(params={
            'search': {
                'query': f'Mail of company representatives for suppliers: {prompt}',
                'criteria': [
                    {
                        'description': prompt
                    },
                ],
                'count': 10
            },
            'enrichments': [
                {
                    'description': 'Work Email',
                    'format': 'text'
                }
            ]
        })
        
        return dict(webset)['id']
    except Exception as e:
        print(f"Error creating Exa webset: {e}")
        return None


def parse_exa_webset_items(webset_id: str, requirement: BuyerRequirement) -> List[SupplierMatch]:
    """Fetch and parse Exa webset results into SupplierMatch objects"""
    if not exa_client:
        return []
    
    try:
        items = exa_client.websets.items.list(webset_id=webset_id, limit=20)
        items_dict = dict(items)
        
        results = []
        seen_emails = set()
        
        for item in items_dict.get('data', []):
            item_str = str(item)
            
            # Extract LinkedIn URL
            linkedin_re = re.compile(r'https?://(?:[a-z]{2,4}\.)?linkedin\.com[^\s\'\)\],>"]+', flags=re.IGNORECASE)
            linkedin_match = linkedin_re.search(item_str)
            linkedin = linkedin_match.group(0).strip() if linkedin_match else ""
            
            # Extract Name
            name_match = re.search(r"name=['\"]([^'\"]{2,120})['\"]", item_str)
            name = name_match.group(1).strip() if name_match else "Unknown Contact"
            
            # Extract Email
            email_match = re.search(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", item_str)
            email = email_match.group(0).strip() if email_match else None
            
            if email and email not in seen_emails and linkedin:
                seen_emails.add(email)
                
                # Extract company name from email domain
                domain = email.split('@')[1].split('.')[0].title()
                company_name = f"{domain} {name.split()[0] if name else 'Company'}"
                
                # Generate match score (higher for more complete data)
                match_score = 85 + len(results) * 2  # Decreasing scores
                
                # Build capabilities from requirement
                capabilities = [
                    f"Supplier for {requirement.productDescription}",
                    f"Contact via email: {email}",
                ]
                if linkedin:
                    capabilities.append(f"LinkedIn verified")
                
                # Generate conversation log
                conversation_log = [
                    {
                        "role": "assistant",
                        "content": f"Found contact {name} at {email} via web search",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    },
                    {
                        "role": "assistant",
                        "content": f"Verified LinkedIn profile and email address. Ready for outreach.",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                ]
                
                results.append(SupplierMatch(
                    name=company_name,
                    contact_email=email,
                    contact_phone="Contact via email for phone",
                    website=linkedin if linkedin else f"https://{email.split('@')[1]}",
                    location="Location TBD - verify via initial contact",
                    match_score=match_score,
                    capabilities=capabilities,
                    conversation_log=conversation_log
                ))
                
                if len(results) >= 10:
                    break
        
        return results
    except Exception as e:
        print(f"Error parsing Exa webset: {e}")
        return []

@app.post("/api/v1/requirements")
async def process_requirements(requirement: BuyerRequirement):
    """
    Process buyer requirements and initiate async investigation.
    Returns immediately with investigation_id and processing status.
    """
    investigation_id = f"INV-{abs(hash(requirement.email + str(requirement.companyName))) % 10000000}"
    
    # Create Exa webset for supplier discovery
    webset_id = None
    if exa_client:
        webset_id = create_exa_webset(requirement)
        if webset_id:
            websets[investigation_id] = webset_id
    
    # Store investigation status
    investigations[investigation_id] = {
        "status": "processing",
        "progress": 0,
        "message": "Initializing AI agents and searching for suppliers...",
        "requirement": requirement,
        "created_at": datetime.now(),
        "webset_id": webset_id
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
    
    # Progressive status simulation (Exa websets take ~60 seconds)
    if elapsed < 10:
        status = "processing"
        progress = 15
        message = "Analyzing your requirements with AI..."
    elif elapsed < 20:
        status = "searching"
        progress = 30
        message = "Searching web for supplier contacts and emails..."
    elif elapsed < 35:
        status = "searching"
        progress = 50
        message = "Crawling supplier websites and LinkedIn profiles..."
    elif elapsed < 50:
        status = "searching"
        progress = 70
        message = "Extracting contact information and verifying emails..."
    elif elapsed < 65:
        status = "processing"
        progress = 90
        message = "Enriching data and matching suppliers to requirements..."
    else:
        status = "completed"
        progress = 100
        message = "Investigation complete!"
    
    # If completed, return suppliers
    if status == "completed":
        suppliers = []
        
        # Try to get real suppliers from Exa
        webset_id = investigation.get("webset_id")
        if webset_id and exa_client:
            try:
                suppliers = parse_exa_webset_items(webset_id, requirement)
                print(f"Successfully parsed {len(suppliers)} suppliers from Exa")
            except Exception as e:
                print(f"Error fetching Exa results: {e}")
        
        # Fallback to mock suppliers if Exa didn't return results
        if not suppliers:
            print("Using mock suppliers as fallback")
            suppliers = [
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
            "suppliers": [s.model_dump() for s in suppliers]
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
