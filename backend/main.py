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
    If similarity >= 0.85, return cached results.
    Otherwise, start a new investigation using EXA enrichment workflow.
    """
    query_text = f"{requirement.productDescription}{requirement.specifications or ''}"

    # 1. Check Weaviate for similar investigation
    response = investigations_collection.query.near_text(
        query=query_text,
        limit=3,
        return_metadata=wq.MetadataQuery(distance=True)
    )

    for obj in response.objects:
        similarity = obj.metadata.distance
        logger.info(f"Similarity: {similarity}")
        if similarity is not None and similarity >= 0.50:
            properties = obj.properties
            if "suppliers" in properties:
                suppliers_field = properties["suppliers"]
                suppliers = json.loads(suppliers_field) if isinstance(suppliers_field, str) else suppliers_field
                return {
                    "cached": True,
                    "status": "completed",
                    "message": "Similar investigation found. Returning cached results.",
                    "suppliers": suppliers,
                    "timestamp": properties.get("created_at", datetime.now().isoformat())
                }

    # 2. No similar investigation → EXA enrichment
    prompt = requirement.productDescription
    webset = exa.websets.create(params={
        "search": {
            "query": f"Mail of company representatives for suppliers: {prompt}",
            "criteria": [{"description": prompt}],
            "count": 10
        },
        "enrichments": [{"description": "Work Email", "format": "text"}]
    })

    webset_id = dict(webset)["id"]
    logger.info(f"EXA webset created: {webset_id}")

    # 3. Poll for enrichment results
    max_wait = 60
    interval = 5
    waited = 0
    items = None
    while waited < max_wait:
        logger.info(f"Polling EXA webset (waited {waited}s)")
        items = exa.websets.items.list(webset_id=webset_id, limit=20)
        if items and items.data:
            logger.info(f"Items received from EXA: {len(items.data)}")
            break
        time.sleep(interval)
        waited += interval

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

    # ---------------------------
    # In your endpoint, after EXA parsing:
    # ---------------------------
    buyer_req_dict = {
        "company_name": requirement.companyName,
        "contact_name": requirement.contactName,
        "product_description": requirement.productDescription,
        "quantity": requirement.quantity,
        "budget": requirement.budgetRange,
        "timeline": requirement.timeline
    }

    processed_suppliers = []
    for sup in results:  # results from EXA enrichment
        sup_data = {
            "company_name": sup.get("name"),
            "contact_name": sup.get("name"),
            "email": sup.get("email")
        }
        simulation = simulate_conversation(sup_data, buyer_req_dict)
        # keep only the extracted contact_email if exists
        sup["extracted_contact_email"] = simulation["extracted_info"].get("contact_email")
        processed_suppliers.append(sup)

    # Insert into Weaviate
    investigations_collection.data.insert(properties={
        "status": "processing",
        "requirement_text": prompt,
        "suppliers": json.dumps(processed_suppliers),
        "created_at": datetime.now().isoformat(),
        "message": "Investigation started via EXA enrichment and email simulation."
    })

    return {
        "cached": False,
        "status": "processing",
        "message": "No cached results found. EXA enrichment and email simulation started.",
        "suppliers": processed_suppliers
    }

@app.get("/api/v1/investigations/{investigation_id}/status")
async def get_investigation_status(investigation_id: str):
    """
    Retrieve investigation status from Weaviate.
    """
    result = investigations_collection.query.fetch_object_by_id(investigation_id)
    if result is not None:
        return result.properties['suppliers']
    else:
        # TODO: start investigation
        # Return a placeholder response until investigation-start logic is implemented
        return {
            "investigation_id": investigation_id,
            "status": "not_found",
            "message": "Investigation not found; investigation will be started (TODO).",
            "timestamp": datetime.now().isoformat()
        }
    
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
