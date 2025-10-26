# Tacto Track Backend - API Scaffold

A minimal FastAPI backend that exposes endpoints for supplier sourcing automation. Currently returns mock data - implement your business logic here.

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

### 2. Install Dependencies

```bash
pip install -r requirements.txt
or
python -m pip install -r requirements.txt
```

### 3. Run the Server

```bash
# Development mode (with auto-reload)
uvicorn main:app --reload --port 8000

# Or simply:
python main.py
```

The API will be available at `http://localhost:8000`

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

**Response (200 OK):**
```json
{
  "investigation_id": "inv_20251025_143022",
  "cached": false,
  "suppliers": [
    {
      "company_name": "TechSupply Manufacturing Ltd.",
      "contact_email": "sales@techsupply.com",
      "contact_name": "Sarah Johnson",
      "pricing": "$15-22 per unit (volume discounts available)",
      "lead_time": "8-10 weeks for initial order",
      "capabilities": "ISO 9001:2015 certified, 15+ years in industrial sensors...",
      "confidence_score": 0.92,
      "conversation_log": [...]
    }
  ],
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
├── main.py              # FastAPI app with mock endpoints
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
├── test_request.json    # Sample request for testing
└── README.md           # This file
```

## Next Steps

This is a scaffold API that returns mock data. To implement real functionality:

1. **Add External Services:**
   - Uncomment dependencies in `requirements.txt`
   - Add API keys to `.env` file
   - Initialize clients in `main.py`

2. **Implement Business Logic:**
   - Replace mock responses with real data
   - Add helper functions for:
     - Vector embeddings
     - Similarity search
     - Supplier search
     - Email automation
     - Data storage

3. **Error Handling:**
   - Add proper validation
   - Implement retry logic
   - Add logging and monitoring

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
