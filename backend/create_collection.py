import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.config import Configure, Property, DataType
import os 
from dotenv import load_dotenv

load_dotenv()

# Best practice: store your credentials in environment variables
weaviate_url = os.environ["WEAVIATE_URL"]
weaviate_api_key = os.environ["WEAVIATE_API_KEY"]

client = weaviate.connect_to_weaviate_cloud(
    cluster_url=weaviate_url,  # Replace with your Weaviate Cloud URL
    auth_credentials=Auth.api_key(weaviate_api_key),  # Replace with your Weaviate Cloud key
)

questions = client.collections.create(
    name="Investigations",
    vector_config=Configure.Vectors.text2vec_weaviate(),  # Configure the Weaviate Embeddings integration
    properties=[
        Property(name="requirement_text", data_type=DataType.TEXT),
        Property(name="status", data_type=DataType.TEXT),
        Property(name="suppliers", data_type=DataType.TEXT),
        Property(name="created_at", data_type=DataType.TEXT),
        Property(name="message", data_type=DataType.TEXT),
    ]
)

client.close()  # Free up resources