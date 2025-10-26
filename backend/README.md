# Tacto Track Backend

A production-ready FastAPI backend for intelligent supplier sourcing automation. Uses vector search, web enrichment, and AI-powered conversations to match buyers with suppliers.

## Features

- **Smart Caching**: Vector similarity search finds existing investigations (distance ≤ 0.5)
- **Web Enrichment**: EXA API discovers suppliers with contact information
- **AI Conversations**: OpenAI simulates buyer-supplier email exchanges
- **Persistent Storage**: Weaviate stores and retrieves investigation results
- **Status Tracking**: Real-time progress monitoring for investigations

## Quick Start

### 1. Environment Variables

Create a `.env` file in the backend directory:

```bash
WEAVIATE_URL=your_weaviate_cluster_url
WEAVIATE_API_KEY=your_weaviate_api_key
EXA_API_KEY=your_exa_api_key
OPENAI_API_KEY=your_openai_api_key
```

### 2. Setup Python Environment

```bash
cd backend
python -m venv venv

# Activate virtual environment:
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Server

```bash
# Development mode (with auto-reload)
uvicorn main:app --reload --port 8000

# Or simply:
python main.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### POST `/api/v1/requirements`

Submit buyer requirements and receive supplier matches. The system first checks for similar investigations in the vector database. If found (similarity distance ≤ 0.5), returns cached results instantly. Otherwise, initiates a new investigation using EXA web enrichment and AI conversations.

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

**Response (200 OK - Cached):**
```json
{
  "investigation_id": "uuid-here",
  "cached": true,
  "status": "completed",
  "message": "Similar investigation found. Returning cached results.",
  "suppliers": [...],
  "timestamp": "2025-10-25T14:30:22.123456"
}
```

**Response (200 OK - New Investigation):**
```json
{
  "investigation_id": "uuid-here",
  "cached": false,
  "status": "processing",
  "message": "New investigation started. Use /status endpoint to track progress.",
  "suppliers": [...],
  "timestamp": "2025-10-25T14:30:22.123456"
}
```

### GET `/api/v1/investigations/{investigation_id}/status`

Check the status of an ongoing or completed investigation.

**Response:**
```json
{
  "investigation_id": "uuid-here",
  "status": "processing" | "completed" | "failed",
  "progress": 65,
  "message": "Analyzing supplier responses...",
  "suppliers": [...],
  "timestamp": "2025-10-25T14:30:22.123456"
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
├── main.py              # FastAPI app with Weaviate, EXA, OpenAI integration
├── requirements.txt     # Python dependencies (FastAPI, Weaviate, EXA, OpenAI)
├── create_collection.py # Weaviate collection initialization script
├── .env                 # Environment variables (not tracked in git)
├── test_request.json    # Sample request for testing
└── README.md           # This file
```

## How It Works

1. **Request Processing**: Buyer submits requirements via POST endpoint
2. **Similarity Search**: Checks Weaviate for similar investigations (vector distance ≤ 0.5)
3. **Cache Hit**: Returns existing suppliers instantly if match found
4. **Cache Miss**: Initiates new investigation:
   - EXA API searches web for supplier contacts (~60 seconds)
   - OpenAI simulates email conversations with suppliers
   - Results stored in Weaviate for future caching
5. **Status Tracking**: Frontend polls status endpoint for progress updates

## Performance Notes

- **Cached Results**: ~500ms response time
- **New Investigations**: ~60-90 seconds (EXA enrichment + AI processing)
- **Similarity Threshold**: Distance ≤ 0.5 triggers cache hit (adjustable in code)

## Future Enhancements

1. **Email Integration**: Real SMTP for actual supplier outreach
2. **Advanced Enrichment**: Additional data sources beyond EXA
3. **ML Scoring**: Train models on successful matches to improve ranking
4. **Rate Limiting**: Add request throttling for production
5. **WebSocket Support**: Real-time progress updates instead of polling

## CORS Configuration

CORS is pre-configured for:
- `http://localhost:5173` (Vite dev server)
- `http://localhost:3000` (alternative frontend port)
- `http://localhost:8080` (alternative port)

Update `main.py` to add production origins when deploying.
