# Tacto Track Backend

FastAPI backend with intelligent investigation caching using Weaviate vector search and OpenAI embeddings. Automatically detects similar past investigations (>85% similarity) to return cached results instantly.

## Quick Start

### 1. Setup Python Environment

```bash
cd backend
python -m venv venv

# Activate virtual environment:
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
```

**Required for similarity matching:**
- `WEAVIATE_URL`: Your Weaviate cluster URL (get free cluster at https://console.weaviate.cloud)
- `WEAVIATE_API_KEY`: Your Weaviate API key
- `OPENAI_API_KEY`: OpenAI API key for embeddings (https://platform.openai.com)

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize Weaviate Schema

Run this once after setting up your Weaviate cluster:

```bash
python init_weaviate.py
```

### 5. Run the Server

```bash
# Development mode (with auto-reload)
uvicorn main:app --reload --port 8000

# Or simply:
python main.py
```

The API will be available at `http://localhost:8000`

## Features

### 🔍 Intelligent Investigation Caching

The backend automatically:
1. **Generates embeddings** from buyer requirements using OpenAI's `text-embedding-3-small`
2. **Searches Weaviate** for similar past investigations (cosine similarity)
3. **Returns cached results** if similarity > 85% (instant response!)
4. **Stores new investigations** in Weaviate for future reuse

This dramatically reduces API costs and response times for similar requirements.

### 📊 Similarity Matching

Requirements are compared based on:
- Product description
- Quantity
- Budget range
- Timeline
- Technical specifications

The system calculates semantic similarity, not just keyword matching.

## API Endpoints

### POST `/api/v1/requirements`

Submit buyer requirements and receive supplier matches.

**Request Body:**
```json
{
  "companyName": "Acme Manufacturing",
  "contactName": "John Smith",
  "email": "john.smith@acme.com",
  "phone": "+1-555-0123",
  "productDescription": "Industrial temperature sensors with digital output",
  "quantity": "1000 units",
  "budgetRange": "$10,000 - $25,000",
  "timeline": "3 months",
  "specifications": "Operating range: -40°C to 125°C, Digital I2C interface, IP67 rated housing"
}
```

**Response (200 OK) - New Investigation:**
```json
{
  "investigation_id": "INV-1234567",
  "status": "processing",
  "cached": false,
  "message": "Investigation started. Poll /api/v1/investigations/{id}/status for updates."
}
```

**Response (200 OK) - Cached Investigation:**
```json
{
  "investigation_id": "INV-7654321",
  "status": "completed",
  "cached": true,
  "similarity": 92.3,
  "message": "Found similar investigation with 92.3% match. Returning cached results.",
  "suppliers": [...]
}
```

### GET `/api/v1/investigations/{investigation_id}/status`

Poll for investigation progress and results.

**Response:**
```json
{
  "investigation_id": "INV-1234567",
  "status": "completed",
  "progress": 100,
  "message": "Investigation complete!",
  "cached": false,
  "suppliers": [
    {
      "name": "TechSupply Manufacturing Ltd.",
      "contact_email": "sales@techsupply.com",
      "contact_phone": "+1-555-0123",
      "website": "https://techsupply.com",
      "location": "San Jose, CA, USA",
      "match_score": 92,
      "capabilities": ["ISO 9001:2015 certified", "15+ years in industrial sensors"],
      "conversation_log": [...]
    }
  ]
}
```

### GET `/health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-25T14:30:22.123456"
}
```

## Testing

Use the included test file:

```bash
curl -X POST http://localhost:8000/api/v1/requirements \
  -H "Content-Type: application/json" \
  -d @test_request.json
```

Or visit the interactive API docs:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
backend/
├── main.py              # FastAPI app with Weaviate integration
├── init_weaviate.py     # Weaviate schema initialization
├── requirements.txt     # Python dependencies (includes weaviate-client, openai)
├── .env.example         # Environment variables template
├── test_request.json    # Sample request for testing
└── README.md           # This file
```

## How It Works

1. **Buyer submits requirements** → POST `/api/v1/requirements`
2. **System generates embedding** from requirement text
3. **Weaviate searches** for similar past investigations
4. **If match found (>85%)** → Return cached results instantly ⚡
5. **If no match** → Start new investigation, poll for updates
6. **Investigation completes** → Results stored in Weaviate for future reuse

## Configuration

### Weaviate Setup

1. Create free cluster at https://console.weaviate.cloud
2. Copy cluster URL and API key to `.env`
3. Run `python init_weaviate.py` to create schema

### Similarity Threshold

Adjust similarity threshold in `main.py`:

```python
# Default: 85% similarity required for cache hit
if similarity > 0.85:  # Change this value
    return cached_result
```

## Next Steps

To implement real supplier discovery:

1. **Replace mock suppliers** with actual search APIs (Exa, Google, etc.)
2. **Add real outreach** using Resend or other email services
3. **Store conversations** in a database (PostgreSQL, Supabase)
4. **Add background tasks** using Celery/Redis for async processing

## CORS Configuration

CORS is pre-configured for:
- `http://localhost:5173` (Vite dev server)
- `http://localhost:3000` (alternative frontend port)
- `http://localhost:8080` (alternative port)

Update `main.py` to add production origins when deploying.

## Deployment

### Option 1: Railway
```bash
railway login
railway init
railway up
```

### Option 2: Render
1. Connect your GitHub repo
2. Create new Web Service
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Option 3: Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```
