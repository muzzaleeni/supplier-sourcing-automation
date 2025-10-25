"""
Initialize Weaviate schema for Tacto Track investigations.
Run this once after setting up your Weaviate cluster.
"""

import os
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.config import Configure, Property, DataType
from dotenv import load_dotenv

load_dotenv()

def init_weaviate_schema():
    """Create the Investigation collection in Weaviate"""
    
    # Connect to Weaviate
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=os.getenv("WEAVIATE_URL"),
        auth_credentials=Auth.api_key(os.getenv("WEAVIATE_API_KEY"))
    )
    
    try:
        # Check if collection already exists
        if client.collections.exists("Investigation"):
            print("Investigation collection already exists. Deleting and recreating...")
            client.collections.delete("Investigation")
        
        # Create Investigation collection
        client.collections.create(
            name="Investigation",
            description="Stores buyer requirement investigations for similarity matching",
            vectorizer_config=Configure.Vectorizer.none(),  # We provide our own embeddings
            properties=[
                Property(
                    name="investigation_id",
                    data_type=DataType.TEXT,
                    description="Unique investigation identifier"
                ),
                Property(
                    name="requirement_text",
                    data_type=DataType.TEXT,
                    description="Combined text representation of the requirement"
                ),
                Property(
                    name="company_name",
                    data_type=DataType.TEXT,
                    description="Buyer company name"
                ),
                Property(
                    name="product_description",
                    data_type=DataType.TEXT,
                    description="Product description from buyer"
                ),
                Property(
                    name="quantity",
                    data_type=DataType.TEXT,
                    description="Quantity requested"
                ),
                Property(
                    name="suppliers",
                    data_type=DataType.OBJECT_ARRAY,
                    description="Array of matched suppliers"
                ),
                Property(
                    name="created_at",
                    data_type=DataType.TEXT,
                    description="Investigation creation timestamp"
                )
            ]
        )
        
        print("✅ Investigation collection created successfully!")
        
    finally:
        client.close()

if __name__ == "__main__":
    if not os.getenv("WEAVIATE_URL") or not os.getenv("WEAVIATE_API_KEY"):
        print("❌ Error: WEAVIATE_URL and WEAVIATE_API_KEY must be set in .env file")
        exit(1)
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY must be set in .env file")
        exit(1)
    
    init_weaviate_schema()
