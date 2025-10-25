# Tacto Track Backend (FastAPI)

This is the backend service for the Tacto Track supplier sourcing automation platform.

## Setup

1. **Install Python 3.11+**

2. **Create virtual environment:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your actual API keys
```

5. **Set up Weaviate schema:**
```bash
python setup_weaviate.py
```

## Running the Backend

```bash
# Development mode with auto-reload
uvicorn main:app --reload --port 8000

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000
```

API will be available at: `http://localhost:8000`
API docs available at: `http://localhost:8000/docs`

## API Endpoints

### POST /api/v1/requirements
Submit a buyer requirement and get supplier matches.

**Request Body:**
```json
{
  "companyName": "Acme Corp",
  "contactName": "John Doe",
  "email": "john@acme.com",
  "phone": "+1234567890",
  "productDescription": "Industrial sensors",
  "quantity": "1000 units",
  "budgetRange": "$10,000 - $20,000",
  "timeline": "3 months",
  "specifications": "Optional technical specs"
}
```

**Response:**
```json
{
  "investigation_id": "inv_1234567890",
  "cached": false,
  "suppliers": [
    {
      "company_name": "Sensor Inc",
      "contact_email": "sales@sensor.com",
      "contact_name": "Jane Smith",
      "pricing": "$15 per unit",
      "lead_time": "6 weeks",
      "capabilities": "ISO certified, 20 years experience",
      "confidence_score": 0.92,
      "conversation_log": [...]
    }
  ],
  "timestamp": "2025-10-25T12:00:00Z"
}
```

### GET /health
Health check endpoint

## Required API Keys

1. **OpenAI API Key**: https://platform.openai.com/api-keys
2. **Weaviate Cloud**: https://console.weaviate.cloud/
3. **Exa API Key**: https://exa.ai/
4. **Resend API Key**: https://resend.com/

## Architecture

```
main.py
├── create_embedding()          # Step 2: Convert text to vector
├── check_similarity()          # Step 3-4: Search cached investigations
├── search_suppliers()          # Step 5: Find suppliers via Exa
├── extract_contacts()          # Step 6: Parse contact info with GPT-4o-mini
├── simulate_conversation()     # Steps 7-8: Mock email exchange
├── store_investigation()       # Step 9: Save to Weaviate
└── send_results_email()        # Step 10: Email results to buyer
```

## Deployment

### Railway
```bash
railway init
railway add
railway up
```

### Render
```bash
# Add render.yaml and deploy via dashboard
```

### Docker
```bash
docker build -t tacto-track-backend .
docker run -p 8000:8000 --env-file .env tacto-track-backend
```

## Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test requirements endpoint
curl -X POST http://localhost:8000/api/v1/requirements \
  -H "Content-Type: application/json" \
  -d @test_request.json
```

## Troubleshooting

- **Weaviate connection errors**: Verify WEAVIATE_URL and WEAVIATE_API_KEY
- **OpenAI rate limits**: Add retry logic or upgrade plan
- **No suppliers found**: Check Exa API key and query format
- **Email not sending**: Verify Resend API key and sender domain
