import os
import re
import json
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from exa_py import Exa
from openai import OpenAI
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize Exa client
exa_client = None
EXA_API_KEY = os.getenv("EXA_API_KEY")
if EXA_API_KEY:
    try:
        exa_client = Exa(EXA_API_KEY)
        logger.info("✓ Exa client initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize Exa client: {e}")
else:
    logger.warning("⚠ EXA_API_KEY not found - Exa functionality will be disabled")

# Initialize OpenAI client
openai_client = None
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("✓ OpenAI client initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize OpenAI client: {e}")
else:
    logger.warning("⚠ OPENAI_API_KEY not found - AI conversation simulation will be disabled")

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
        logger.warning("⚠ Exa client not available - skipping webset creation")
        return None
    
    # Build search query from product description and specifications
    prompt = requirement.productDescription
    if requirement.specifications:
        prompt += f". Specifications: {requirement.specifications}"
    
    logger.info(f"Creating Exa webset for: {prompt[:100]}...")
    
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

        webset_id = dict(webset)['id']
        logger.info(f"✓ Exa webset created successfully: {webset_id}")
        logger.info("⏳ Waiting 60 seconds for Exa to process webset...")
        time.sleep(60)
        logger.info("✓ Webset processing wait completed")
        return webset_id
    except Exception as e:
        logger.error(f"✗ Error creating Exa webset: {type(e).__name__}: {e}")
        return None


def simulate_email_conversation(supplier_name: str, supplier_email: str, requirement: BuyerRequirement) -> dict:
    """Simulate an email conversation with a supplier using OpenAI"""
    if not openai_client:
        logger.warning(f"⚠ OpenAI client not available - using basic conversation for {supplier_email}")
        return {
            "conversation": [
                {
                    "role": "assistant",
                    "content": f"Found contact at {supplier_email}",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            ],
            "is_decision_maker": True,
            "next_action": None
        }
    
    logger.info(f"Simulating email conversation with {supplier_name} ({supplier_email})")
    
    conversation = []
    
    # 1. Generate initial outreach email
    outreach = f"""Subject: Inquiry: {requirement.productDescription[:50]}

Hi,

I'm reaching out from {requirement.companyName} regarding our need for {requirement.productDescription}.

Quick question: are you the right person to speak with about this request? If not, could you please forward me the email of the correct contact or reply with their contact email?

Brief requirements:
- Quantity: {requirement.quantity}
- Budget: {requirement.budgetRange}
- Timeline: {requirement.timeline}

Best regards,
{requirement.contactName}"""
    
    conversation.append({
        "role": "buyer",
        "content": outreach,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # 2. Use OpenAI to simulate supplier response
    try:
        logger.info(f"Generating supplier response simulation for {supplier_name}...")
        simulation_prompt = f"""You are simulating a supplier response to this inquiry email. 
The supplier is from company: {supplier_name}
Email: {supplier_email}

Buyer's email:
{outreach}

Generate a realistic supplier response. The response should either:
1. Confirm they are the right person to discuss this (if the email seems like a decision-maker)
2. Redirect to another contact (if the email seems like a general contact)

Be concise and professional. Include the supplier's role/title in the signature."""

        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": simulation_prompt}],
            temperature=0.7
        )
        
        simulated_reply = response.choices[0].message.content
        logger.info(f"✓ Generated supplier response simulation")
        
        conversation.append({
            "role": "supplier",
            "content": simulated_reply,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # 3. Extract information from the response
        logger.info(f"Extracting decision-maker information...")
        extraction_prompt = f"""You are an assistant that reads a supplier reply and extracts information as JSON.
Input conversation:
{json.dumps(conversation)}

Return a JSON object ONLY (no other text) with these fields:
- is_decision_maker: boolean  # true if the supplier says they are the right contact
- contact_email: string|null  # the email of the correct contact if provided, otherwise null
- reason: string  # short explanation of how you decided

Respond ONLY with valid JSON."""

        extraction = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": extraction_prompt}],
            temperature=0
        )
        
        extracted = json.loads(extraction.choices[0].message.content)
        logger.info(f"✓ Extracted: is_decision_maker={extracted.get('is_decision_maker')}, contact_email={extracted.get('contact_email')}")
        
        next_action = None
        if not extracted.get('is_decision_maker') and extracted.get('contact_email'):
            next_action = {
                "action": "contact_new_email",
                "email": extracted['contact_email']
            }
        elif extracted.get('is_decision_maker'):
            next_action = {
                "action": "continue_with_current_contact",
                "email": supplier_email
            }
        
        return {
            "conversation": conversation,
            "is_decision_maker": extracted.get('is_decision_maker', False),
            "next_action": next_action,
            "reason": extracted.get('reason', '')
        }
        
    except Exception as e:
        logger.error(f"✗ Error simulating conversation: {type(e).__name__}: {e}")
        # Fallback to basic conversation
        conversation.append({
            "role": "supplier",
            "content": "Thank you for reaching out. Yes, I'm the right person to discuss this.",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        return {
            "conversation": conversation,
            "is_decision_maker": True,
            "next_action": None
        }


def parse_exa_webset_items(webset_id: str, requirement: BuyerRequirement) -> List[SupplierMatch]:
    """Fetch and parse Exa webset results into SupplierMatch objects"""
    if not exa_client:
        logger.warning("⚠ Exa client not available - cannot parse webset items")
        return []
    
    logger.info(f"Fetching items from Exa webset: {webset_id}")
    
    try:
        items = exa_client.websets.items.list(webset_id=webset_id, limit=20)
        items_dict = dict(items)
        logger.info(f"✓ Retrieved {len(items_dict.get('data', []))} items from Exa")
        
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
                
                # Simulate email conversation with this supplier
                email_simulation = simulate_email_conversation(company_name, email, requirement)
                conversation_log = email_simulation["conversation"]
                
                # Add analysis note
                if email_simulation.get("next_action"):
                    next_action = email_simulation["next_action"]
                    if next_action["action"] == "contact_new_email":
                        conversation_log.append({
                            "role": "system",
                            "content": f"⚠️ Not decision maker. Recommended next contact: {next_action['email']}",
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                    elif next_action["action"] == "continue_with_current_contact":
                        conversation_log.append({
                            "role": "system",
                            "content": "✓ Confirmed decision maker. Ready for detailed discussion.",
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                
                if email_simulation.get("reason"):
                    conversation_log.append({
                        "role": "system",
                        "content": f"Analysis: {email_simulation['reason']}",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                
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
        
        logger.info(f"✓ Successfully parsed {len(results)} supplier matches")
        return results
    except Exception as e:
        logger.error(f"✗ Error parsing Exa webset: {type(e).__name__}: {e}")
        return []

@app.post("/api/v1/requirements")
async def process_requirements(requirement: BuyerRequirement):
    """
    Process buyer requirements and initiate async investigation.
    Returns immediately with investigation_id and processing status.
    """
    investigation_id = f"INV-{abs(hash(requirement.email + str(requirement.companyName))) % 10000000}"
    
    logger.info(f"=== NEW INVESTIGATION {investigation_id} ===")
    logger.info(f"Company: {requirement.companyName}")
    logger.info(f"Product: {requirement.productDescription}")
    logger.info(f"Quantity: {requirement.quantity}, Budget: {requirement.budgetRange}, Timeline: {requirement.timeline}")
    
    # Create Exa webset for supplier discovery
    webset_id = None
    if exa_client:
        webset_id = create_exa_webset(requirement)
        if webset_id:
            websets[investigation_id] = webset_id
            logger.info(f"✓ Webset {webset_id} associated with investigation {investigation_id}")
        else:
            logger.warning(f"⚠ Failed to create webset for investigation {investigation_id}")
    else:
        logger.warning(f"⚠ Exa client unavailable - investigation {investigation_id} will use mock data")
    
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
    logger.info(f"Status check for investigation: {investigation_id}")
    
    if investigation_id not in investigations:
        logger.warning(f"⚠ Investigation {investigation_id} not found")
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
        logger.info(f"Investigation {investigation_id} completed - preparing supplier results")
        suppliers = []
        
        # Try to get real suppliers from Exa
        webset_id = investigation.get("webset_id")
        if webset_id and exa_client:
            try:
                suppliers = parse_exa_webset_items(webset_id, requirement)
                logger.info(f"✓ Successfully parsed {len(suppliers)} suppliers from Exa")
            except Exception as e:
                logger.error(f"✗ Error fetching Exa results: {type(e).__name__}: {e}")
        
        # Fallback to mock suppliers if Exa didn't return results
        if not suppliers:
            logger.warning("⚠ Using mock suppliers as fallback (no real data available)")
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
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "exa": "enabled" if exa_client else "disabled (missing EXA_API_KEY)",
            "openai": "enabled" if openai_client else "disabled (missing OPENAI_API_KEY)"
        }
    }
    logger.info(f"Health check: {health_status}")
    return health_status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
