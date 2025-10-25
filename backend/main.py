from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import openai
import weaviate
from exa_py import Exa
import resend
import os
from typing import List, Dict, Optional
import json
from datetime import datetime

app = FastAPI(title="Tacto Track API", version="1.0.0")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "https://*.lovable.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
weaviate_client = weaviate.Client(
    url=os.getenv("WEAVIATE_URL"),
    auth_client_secret=weaviate.AuthApiKey(api_key=os.getenv("WEAVIATE_API_KEY"))
)
exa_client = Exa(api_key=os.getenv("EXA_API_KEY"))
resend.api_key = os.getenv("RESEND_API_KEY")


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
    conversation_log: List[Dict[str, str]]


class InvestigationResult(BaseModel):
    investigation_id: str
    cached: bool
    suppliers: List[SupplierMatch]
    timestamp: str


def create_embedding(requirement: BuyerRequirement) -> List[float]:
    """Step 2: Create embedding from buyer requirement"""
    text = f"{requirement.productDescription} {requirement.quantity} {requirement.budgetRange} {requirement.timeline}"
    if requirement.specifications:
        text += f" {requirement.specifications}"
    
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def check_similarity(vector: List[float], threshold: float = 0.85) -> Optional[Dict]:
    """Step 3: Check Weaviate for similar investigations"""
    try:
        result = weaviate_client.query.get(
            "Investigation",
            ["investigationId", "suppliers", "timestamp"]
        ).with_near_vector({
            "vector": vector,
            "certainty": threshold
        }).with_limit(1).do()
        
        if result["data"]["Get"]["Investigation"]:
            return result["data"]["Get"]["Investigation"][0]
        return None
    except Exception as e:
        print(f"Similarity check error: {e}")
        return None


def search_suppliers(query: str) -> List[Dict]:
    """Step 5: Call Exa API to find suppliers"""
    search_query = f"supplier manufacturer {query}"
    results = exa_client.search(
        search_query,
        num_results=10,
        use_autoprompt=True
    )
    return results.results


def extract_contacts(exa_results: List, requirement: BuyerRequirement) -> List[Dict]:
    """Step 6: Extract contact info using GPT-4o-mini"""
    contacts = []
    
    for result in exa_results[:10]:
        prompt = f"""Extract contact information from this supplier website:
        
Company URL: {result.url}
Company Title: {result.title}
Snippet: {result.text if hasattr(result, 'text') else ''}

Looking for: {requirement.productDescription}

Extract and return JSON with:
- company_name
- contact_email (must be present)
- contact_name (or "Sales Team" if not found)
- relevance_score (0-1, how well they match the requirement)
"""
        
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            data = json.loads(response.choices[0].message.content)
            if data.get("contact_email"):
                contacts.append(data)
        except Exception as e:
            print(f"Contact extraction error: {e}")
            continue
    
    # Sort by relevance and return top 3
    contacts.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    return contacts[:3]


def simulate_conversation(supplier: Dict, requirement: BuyerRequirement) -> Dict:
    """Steps 7-8: Simulate email conversation with supplier"""
    conversation_log = []
    
    # Initial outreach
    outreach_prompt = f"""Generate a professional outreach email to {supplier['company_name']} requesting:
    
Product: {requirement.productDescription}
Quantity: {requirement.quantity}
Budget: {requirement.budgetRange}
Timeline: {requirement.timeline}

Keep it concise and professional."""
    
    outreach = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": outreach_prompt}]
    ).choices[0].message.content
    
    conversation_log.append({
        "from": "buyer",
        "to": supplier["contact_email"],
        "subject": f"Inquiry: {requirement.productDescription}",
        "message": outreach
    })
    
    # Simulate supplier response
    response_prompt = f"""You are {supplier['company_name']} responding to this inquiry:

{outreach}

Provide a realistic response including:
- Pricing estimate
- Lead time
- Brief capabilities/certifications
- Whether you're a decision maker (yes/no)

Keep it concise and realistic."""
    
    supplier_response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": response_prompt}]
    ).choices[0].message.content
    
    conversation_log.append({
        "from": supplier["contact_email"],
        "to": requirement.email,
        "subject": f"Re: Inquiry: {requirement.productDescription}",
        "message": supplier_response
    })
    
    # Extract key info from conversation
    extract_prompt = f"""Extract key information from this supplier response:

{supplier_response}

Return JSON with:
- pricing (string)
- lead_time (string)
- is_decision_maker (boolean)
- capabilities (string)
- confidence_score (0-1, how confident we are this is a good match)
"""
    
    extracted = json.loads(
        openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": extract_prompt}],
            response_format={"type": "json_object"}
        ).choices[0].message.content
    )
    
    return {
        **supplier,
        **extracted,
        "conversation_log": conversation_log
    }


def store_investigation(investigation_id: str, buyer_email: str, suppliers: List[Dict], vector: List[float]):
    """Step 9: Store investigation in Weaviate"""
    try:
        weaviate_client.data_object.create(
            {
                "investigationId": investigation_id,
                "buyerEmail": buyer_email,
                "suppliers": json.dumps(suppliers),
                "timestamp": datetime.utcnow().isoformat()
            },
            "Investigation",
            vector=vector
        )
    except Exception as e:
        print(f"Storage error: {e}")


def send_results_email(buyer_email: str, suppliers: List[Dict], requirement: BuyerRequirement):
    """Step 10: Send results email to buyer"""
    html_content = f"""
    <h1>Your Supplier Matches</h1>
    <p>Hi {requirement.contactName},</p>
    <p>We found {len(suppliers)} qualified suppliers for your request:</p>
    """
    
    for i, supplier in enumerate(suppliers, 1):
        html_content += f"""
        <div style="border: 1px solid #ccc; padding: 15px; margin: 10px 0;">
            <h2>{i}. {supplier['company_name']}</h2>
            <p><strong>Contact:</strong> {supplier['contact_name']} ({supplier['contact_email']})</p>
            <p><strong>Pricing:</strong> {supplier.get('pricing', 'Contact for quote')}</p>
            <p><strong>Lead Time:</strong> {supplier.get('lead_time', 'To be confirmed')}</p>
            <p><strong>Capabilities:</strong> {supplier.get('capabilities', 'See conversation')}</p>
            <p><strong>Confidence Score:</strong> {supplier.get('confidence_score', 0):.0%}</p>
        </div>
        """
    
    try:
        resend.Emails.send({
            "from": "noreply@tactotrack.com",
            "to": buyer_email,
            "subject": f"Your Supplier Matches for {requirement.productDescription}",
            "html": html_content
        })
    except Exception as e:
        print(f"Email send error: {e}")


@app.post("/api/v1/requirements", response_model=InvestigationResult)
async def submit_requirement(requirement: BuyerRequirement):
    """Main endpoint: Process buyer requirement"""
    investigation_id = f"inv_{datetime.utcnow().timestamp()}"
    
    try:
        # Step 2: Create embedding
        vector = create_embedding(requirement)
        
        # Step 3-4: Check similarity
        cached_result = check_similarity(vector, threshold=0.85)
        
        if cached_result:
            # Return cached investigation
            return InvestigationResult(
                investigation_id=cached_result["investigationId"],
                cached=True,
                suppliers=json.loads(cached_result["suppliers"]),
                timestamp=cached_result["timestamp"]
            )
        
        # Step 5: Search suppliers
        exa_results = search_suppliers(requirement.productDescription)
        
        # Step 6: Extract contacts
        suppliers = extract_contacts(exa_results, requirement)
        
        if not suppliers:
            raise HTTPException(status_code=404, detail="No suppliers found with contact information")
        
        # Steps 7-8: Simulate conversations
        enriched_suppliers = [simulate_conversation(s, requirement) for s in suppliers]
        
        # Step 9: Store investigation
        store_investigation(investigation_id, requirement.email, enriched_suppliers, vector)
        
        # Step 10: Send email
        send_results_email(requirement.email, enriched_suppliers, requirement)
        
        return InvestigationResult(
            investigation_id=investigation_id,
            cached=False,
            suppliers=enriched_suppliers,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "tacto-track-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
