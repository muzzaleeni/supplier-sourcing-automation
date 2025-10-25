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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tacto")

load_dotenv()

# Connect to Weaviate
weaviate_url = os.environ["WEAVIATE_URL"]
weaviate_api_key = os.environ["WEAVIATE_API_KEY"]

client = weaviate.connect_to_weaviate_cloud(
    cluster_url=weaviate_url,
    auth_credentials=Auth.api_key(weaviate_api_key),
)

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


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post("/api/v1/requirements")
async def process_requirements(requirement: BuyerRequirement):
    """
    Checks if similar investigation exists in Weaviate.
    If similarity >= 0.85, return cached results.
    Otherwise, create a new investigation entry as TODO.
    """
    query_text = f"{requirement.productDescription}{requirement.specifications or ''}"

    # Search for similar investigations in Weaviate
    response = investigations_collection.query.near_text(
        query=query_text,
        limit=3,
        return_metadata=wq.MetadataQuery(distance=True)
    )

    for obj in response.objects:
        similarity = obj.metadata.distance
        logger.info(similarity)
        if similarity is not None and similarity >= 0.50:
            properties = obj.properties
            if "suppliers" in properties:
                suppliers_field = properties["suppliers"]
                if isinstance(suppliers_field, (str, bytes, bytearray)):
                    suppliers = json.loads(suppliers_field)
                else:
                    suppliers = suppliers_field
                return {
                    "investigation_id": obj.uuid,
                    "cached": True,
                    "status": "completed",
                    "message": "Similar investigation found. Returning cached results.",
                    "suppliers": suppliers,
                    "timestamp": properties.get("timestamp", datetime.now().isoformat())
                }
    # TODO: new investigation

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
