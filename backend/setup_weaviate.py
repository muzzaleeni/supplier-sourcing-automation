"""
Setup script to create Weaviate schema for Tacto Track
Run this once before starting the backend service
"""
import weaviate
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Weaviate client
client = weaviate.Client(
    url=os.getenv("WEAVIATE_URL"),
    auth_client_secret=weaviate.AuthApiKey(api_key=os.getenv("WEAVIATE_API_KEY"))
)

# Define Investigation schema
investigation_schema = {
    "class": "Investigation",
    "description": "Stores supplier investigation results with vector embeddings",
    "vectorizer": "none",  # We're providing our own vectors from OpenAI
    "properties": [
        {
            "name": "investigationId",
            "dataType": ["string"],
            "description": "Unique identifier for the investigation"
        },
        {
            "name": "buyerEmail",
            "dataType": ["string"],
            "description": "Email of the buyer who submitted the requirement"
        },
        {
            "name": "suppliers",
            "dataType": ["text"],
            "description": "JSON string containing supplier match results"
        },
        {
            "name": "timestamp",
            "dataType": ["date"],
            "description": "When the investigation was created"
        }
    ]
}

def setup_schema():
    """Create or update Weaviate schema"""
    try:
        # Check if class already exists
        existing_schema = client.schema.get()
        class_names = [cls["class"] for cls in existing_schema.get("classes", [])]
        
        if "Investigation" in class_names:
            print("Investigation class already exists. Skipping creation.")
            response = input("Do you want to delete and recreate it? (yes/no): ")
            if response.lower() == "yes":
                client.schema.delete_class("Investigation")
                print("Deleted existing Investigation class")
            else:
                print("Keeping existing schema")
                return
        
        # Create the schema
        client.schema.create_class(investigation_schema)
        print("✓ Successfully created Investigation schema in Weaviate")
        print(f"  - Vector dimension: 1536 (text-embedding-3-small)")
        print(f"  - Properties: investigationId, buyerEmail, suppliers, timestamp")
        
    except Exception as e:
        print(f"✗ Error setting up schema: {e}")
        raise

def verify_connection():
    """Verify Weaviate connection"""
    try:
        meta = client.get_meta()
        print(f"✓ Connected to Weaviate v{meta['version']}")
        return True
    except Exception as e:
        print(f"✗ Failed to connect to Weaviate: {e}")
        return False

if __name__ == "__main__":
    print("Setting up Weaviate schema for Tacto Track...")
    print("-" * 50)
    
    if verify_connection():
        setup_schema()
        print("-" * 50)
        print("Setup complete! You can now start the backend service.")
    else:
        print("Please check your WEAVIATE_URL and WEAVIATE_API_KEY in .env file")
