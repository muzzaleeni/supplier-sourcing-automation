import os
import json
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
import weaviate
from weaviate.classes.init import Auth
import logging
import weaviate.classes.query as wq
import time
import re
from exa_py import Exa
from openai import OpenAI
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tacto")

load_dotenv()

# Connect to Weaviate
weaviate_url = os.environ["WEAVIATE_URL"]
weaviate_api_key = os.environ["WEAVIATE_API_KEY"]
EXA_API_KEY = os.environ.get("EXA_API_KEY")
exa = Exa(EXA_API_KEY)

client = weaviate.connect_to_weaviate_cloud(
    cluster_url=weaviate_url,
    auth_credentials=Auth.api_key(weaviate_api_key),
)

openai_client = OpenAI()

investigations_collection = client.collections.use("Investigations")
# ============================================================================
# FASTAPI SETUP
# ============================================================================

app = FastAPI(title="Tacto Track API", version="1.0.0")

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

def simulate_conversation(supplier: dict, buyer_requirements: dict) -> dict:
    conversation = []

    # 1. Generate initial outreach
    outreach = f"""
Subject: Inquiry: {buyer_requirements.get('product_description', '')[:50]}

Hi {supplier.get('contact_name', '')},

I'm reaching out from {buyer_requirements.get('company_name', '')} regarding our need for {buyer_requirements.get('product_description', '')}.

Quick question: are you the right person to speak with about this request? If not, could you please forward me the email of the correct contact or reply with their contact email?

Brief requirements:
- Quantity: {buyer_requirements.get('quantity', '')}
- Budget: {buyer_requirements.get('budget', '')}
- Timeline: {buyer_requirements.get('timeline', '')}

Best regards,
{buyer_requirements.get('contact_name', '')}
"""
    conversation.append({"role": "buyer", "message": outreach})

    # 2. Simulate supplier reply
    simulated_reply = (
        f"Subject: RE: Inquiry: {buyer_requirements.get('product_description', '')}\n\n"
        f"Hello {buyer_requirements.get('contact_name', '')},\n\n"
        "Thank you for reaching out. No, I'm not the right person to handle this request. "
        "Please contact: nomenuovo@techsupply.com for further details.\n\n"
        "Best regards,\n"
        f"{supplier.get('contact_name', '')}\n{supplier.get('company_name', '')}"
    )
    conversation.append({"role": "supplier", "message": simulated_reply})

    # 3. Extract decision maker info
    extraction_prompt = f"""
You are an assistant that reads a single supplier reply and extracts two pieces of information as JSON.
Input conversation:
{json.dumps(conversation)}

Return a JSON object ONLY (no other text) with these fields:
- is_decision_maker: boolean
- contact_email: string|null
- reason: string
"""
    extraction = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": extraction_prompt + "\nRespond ONLY with valid JSON."}]
    )

    content = extraction.choices[0].message.content or "{}"
    extracted = json.loads(content)

    next_action = None
    if not extracted.get("is_decision_maker") and extracted.get("contact_email"):
        next_action = {"action": "contact_new_email", "email": extracted["contact_email"]}

    return {"supplier": supplier, "conversation": conversation, "extracted_info": extracted, "next_action": next_action}


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post("/api/v1/requirements")
async def process_requirements(requirement: BuyerRequirement):
    """
    Checks if similar investigation exists in Weaviate.
    If similarity >= 0.50, return cached results.
    Otherwise, start a new investigation using EXA enrichment workflow.
    """
    logger.info(f"Processing requirement from {requirement.companyName}: {requirement.productDescription}")
    query_text = f"{requirement.productDescription} {requirement.specifications or ''}"

    # 1. Check Weaviate for similar investigation
    try:
        response = investigations_collection.query.near_text(
            query=query_text,
            limit=3,
            return_metadata=wq.MetadataQuery(distance=True)
        )

        for obj in response.objects:
            similarity = obj.metadata.distance
            logger.info(f"Found similar investigation with similarity: {similarity}")
            if similarity is not None and -0.05<similarity<0.05:
                properties = obj.properties
                if "suppliers" in properties:
                    suppliers_field = properties["suppliers"]
                    suppliers = json.loads(suppliers_field) if isinstance(suppliers_field, str) else suppliers_field
                    
                    # Format suppliers for frontend
                    formatted_suppliers = []
                    for sup in suppliers:
                        formatted_suppliers.append({
                            "name": sup.get("name", "Unknown Company"),
                            "contact_email": sup.get("extracted_contact_email") or sup.get("email", ""),
                            "contact_phone": "+1 (555) 000-0000",  # Mock data
                            "website": sup.get("linkedin", "https://example.com"),
                            "location": "United States",  # Mock data
                            "match_score": 95,
                            "capabilities": ["Manufacturing", "Global Shipping", "ISO Certified"],
                            "conversation_log": [
                                {
                                    "role": "system",
                                    "content": f"Initial contact made with {sup.get('name')}",
                                    "timestamp": datetime.now().isoformat()
                                }
                            ]
                        })
                    
                    logger.info(f"Returning {len(formatted_suppliers)} cached suppliers")
                    return {
                        "investigation_id": str(obj.uuid),
                        "cached": True,
                        "status": "completed",
                        "message": "Similar investigation found. Returning cached results.",
                        "suppliers": formatted_suppliers,
                        "timestamp": properties.get("created_at", datetime.now().isoformat())
                    }
    except Exception as e:
        logger.error(f"Error checking Weaviate cache: {e}")
        # Continue with new investigation

    # 2. No similar investigation → EXA enrichment
    logger.info("No cached results found. Starting new investigation with EXA enrichment.")
    prompt = requirement.productDescription
    
    try:
        webset = exa.websets.create(params={
            "search": {
                "query": f"Company contact emails for suppliers of: {prompt}",
                "criteria": [{"description": prompt}],
                "count": 10
            },
            "enrichments": [{"description": "Work Email", "format": "text"}]
        })

        webset_id = dict(webset)["id"]
        logger.info(f"EXA webset created: {webset_id}")

        # 3. Poll for enrichment results
        max_wait = 60
        await asyncio.sleep(max_wait)
        logger.info(f"Polling EXA webset (waited {max_wait}s)")
        items = exa.websets.items.list(webset_id=webset_id, limit=20)
        if items and items.data:
            logger.info(f"Items received from EXA: {len(items.data)}")

        if not items or not items.data:
            logger.warning("No items returned from EXA after polling")
            results = []
        else:
            # 4. Parse results
            results = []
            items_dict = dict(items)
            for item in items_dict.get("data", []):
                item_str = str(item)
                linkedin = re.search(r"https?://(?:[a-z]{2,4}\.)?linkedin\.com[^\s\'\)\],\"]+", item_str)
                name = re.search(r"name=['\"]([^'\"]{2,120})['\"]", item_str)
                email = re.search(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", item_str)
                if linkedin and name and email:
                    results.append({
                        "name": name.group(1).strip(),
                        "email": email.group(0).strip(),
                        "linkedin": linkedin.group(0).strip()
                    })

            logger.info(f"Parsed {len(results)} enriched supplier results from EXA")
    except Exception as e:
        logger.error(f"Error with EXA enrichment: {e}")
        results = []

    # 5. Email simulation
    buyer_req_dict = {
        "company_name": requirement.companyName,
        "contact_name": requirement.contactName,
        "product_description": requirement.productDescription,
        "quantity": requirement.quantity,
        "budget": requirement.budgetRange,
        "timeline": requirement.timeline
    }

    processed_suppliers = []
    for sup in results:
        try:
            sup_data = {
                "company_name": sup.get("name"),
                "contact_name": sup.get("name"),
                "email": sup.get("email")
            }
            logger.info(f"Simulating conversation with {sup.get('name')}")
            simulation = simulate_conversation(sup_data, buyer_req_dict)
            
            # Format for frontend with conversation log
            conversation_log = []
            for conv in simulation.get("conversation", []):
                conversation_log.append({
                    "role": conv.get("role"),
                    "content": conv.get("message", ""),
                    "timestamp": datetime.now().isoformat()
                })
            
            processed_suppliers.append({
                "name": sup.get("name"),
                "contact_email": simulation["extracted_info"].get("contact_email") or sup.get("email"),
                "contact_phone": "+1 (555) 000-0000",  # Mock data
                "website": sup.get("linkedin", "https://example.com"),
                "location": "United States",  # Mock data
                "match_score": 92,
                "capabilities": ["Manufacturing", "Global Shipping", "Quality Assurance"],
                "conversation_log": conversation_log
            })
        except Exception as e:
            logger.error(f"Error processing supplier {sup.get('name')}: {e}")
            continue

    # 6. Insert into Weaviate
    try:
        investigation_uuid = investigations_collection.data.insert(properties={
            "status": "completed",
            "requirement_text": prompt,
            "suppliers": json.dumps(processed_suppliers),
            "created_at": datetime.now().isoformat(),
            "message": "Investigation completed via EXA enrichment and email simulation."
        })
        logger.info(f"Investigation saved to Weaviate with UUID: {investigation_uuid}")
        investigation_id = str(investigation_uuid)
    except Exception as e:
        logger.error(f"Error saving to Weaviate: {e}")
        investigation_id = f"inv_{datetime.now().timestamp()}"

    return {
        "investigation_id": investigation_id,
        "cached": False,
        "status": "completed",
        "message": "Investigation completed with EXA enrichment and email simulation.",
        "suppliers": processed_suppliers,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/investigations/{investigation_id}/status")
async def get_investigation_status(investigation_id: str):
    """
    Retrieve investigation status from Weaviate.
    """
    logger.info(f"Checking status for investigation: {investigation_id}")
    
    try:
        result = investigations_collection.query.fetch_object_by_id(investigation_id)
        
        if result is not None:
            properties = result.properties
            status_value = properties.get("status", "completed")
            suppliers_field = properties.get("suppliers", "[]")
            suppliers = json.loads(suppliers_field) if isinstance(suppliers_field, str) else suppliers_field
            
            # Map internal status to frontend status
            if status_value == "completed":
                frontend_status = "completed"
                progress = 100
            elif status_value == "contacting":
                frontend_status = "contacting"
                progress = 75
            elif status_value == "searching":
                frontend_status = "searching"
                progress = 50
            else:
                frontend_status = "processing"
                progress = 25
            
            logger.info(f"Investigation {investigation_id} status: {frontend_status} ({progress}%)")
            
            return {
                "investigation_id": investigation_id,
                "status": frontend_status,
                "progress": progress,
                "message": properties.get("message", "Processing your request..."),
                "suppliers": suppliers if status_value == "completed" else None,
                "timestamp": properties.get("created_at", datetime.now().isoformat())
            }
        else:
            logger.warning(f"Investigation {investigation_id} not found")
            return {
                "investigation_id": investigation_id,
                "status": "processing",
                "progress": 10,
                "message": "Investigation not found in database.",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Error fetching investigation status: {e}")
        return {
            "investigation_id": investigation_id,
            "status": "processing",
            "progress": 10,
            "message": f"Error retrieving status: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
    
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
