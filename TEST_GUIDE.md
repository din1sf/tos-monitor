# Bosch LLM Farm - Complete Testing Guide

## Prerequisites Check

Before testing, verify you have:
- ✅ Python 3.11+ installed
- ✅ Dependencies installed (`pip install -r requirements.txt`)
- ✅ Bosch LLM Farm authentication token
- ✅ Access to Bosch network/VPN (if required)

---

## Step 1: Environment Setup

```bash
# Navigate to project directory
cd /Users/din1sf/d/develop-bosch/tos-monitor

# Check your .env file
cat .env | grep -E "AI_PROVIDER|ANTHROPIC_AUTH_TOKEN|BOSCH_LLM_MODEL"
```

**Expected output:**
```
AI_PROVIDER=bosch-llm-farm
ANTHROPIC_AUTH_TOKEN=18c96e253336449b9664da6dbc4edabf
BOSCH_LLM_MODEL=claude-sonnet-4-5@20250929
```

---

## Step 2: Test Environment Variables Loading

```bash
python3 -c "
import os
from dotenv import load_dotenv

load_dotenv()

print('=== Environment Check ===')
print(f'✓ AI_PROVIDER: {os.getenv(\"AI_PROVIDER\")}')
print(f'✓ BOSCH_LLM_MODEL: {os.getenv(\"BOSCH_LLM_MODEL\")}')
print(f'✓ ANTHROPIC_AUTH_TOKEN: {os.getenv(\"ANTHROPIC_AUTH_TOKEN\")[:20]}...')
print(f'✓ BOSCH_LLM_BASE_URL: {os.getenv(\"BOSCH_LLM_BASE_URL\", \"(using default)\")}')
print(f'✓ STORAGE_MODE: {os.getenv(\"STORAGE_MODE\")}')
print()
print('All variables loaded successfully!')
"
```

---

## Step 3: Test Client Initialization

```bash
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()

from app.llm_client import get_llm_client

print('=== Testing Client Initialization ===')
client = get_llm_client('bosch-llm-farm')

print(f'✓ Client Type: {client.__class__.__name__}')
print(f'✓ Provider: {client.provider}')
print(f'✓ Model: {client.model}')
print(f'✓ Base URL: {client.base_url}')
print(f'✓ Anthropic Version: {client.anthropic_version}')
print()
print(f'Full Endpoint:')
print(f'{client.base_url}/publishers/anthropic/models/{client.model}:rawPredict')
print()
print('Client initialized successfully!')
"
```

---

## Step 4: Test API Connection

```bash
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()

from app.llm_client import get_llm_client
import asyncio

async def test_connection():
    print('=== Testing Bosch LLM Farm Connection ===')
    client = get_llm_client('bosch-llm-farm')
    
    print('Sending test request...')
    result = await client.test_connection()
    
    if result:
        print('✅ SUCCESS: Connection to Bosch LLM Farm working!')
        print()
        print('You can now use the service for document analysis.')
        return True
    else:
        print('❌ FAILED: Could not connect to Bosch LLM Farm')
        print()
        print('Troubleshooting:')
        print('1. Check your ANTHROPIC_AUTH_TOKEN')
        print('2. Verify you are on Bosch network/VPN')
        print('3. Confirm the model name is correct')
        return False

asyncio.run(test_connection())
"
```

---

## Step 5: Test Document Analysis (Simple)

```bash
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()

from app.llm_client import get_llm_client
import asyncio

async def test_analysis():
    print('=== Testing Document Analysis ===')
    client = get_llm_client('bosch-llm-farm')
    
    # Simple test documents
    old_doc = 'Terms: You must be 13 years old. We collect your email.'
    new_doc = 'Terms: You must be 18 years old. We collect your email and location.'
    
    prompt = '''
Compare these documents and list the key changes:

Old: {previous_content}
New: {current_content}

Provide a brief summary.
'''
    
    print('Analyzing document changes...')
    result = await client.compare_documents(
        previous_content=old_doc,
        current_content=new_doc,
        document_name='Test Terms',
        prompt_template=prompt,
        metadata={}
    )
    
    if result:
        print('✅ Analysis completed successfully!')
        print()
        print('=== RESULT ===')
        print(result)
        print()
        return True
    else:
        print('❌ Analysis failed')
        return False

asyncio.run(test_analysis())
"
```

---

## Step 6: Start the Application

```bash
# Terminal 1: Start the server
python3 -m uvicorn app.main:app --reload --port 8080
```

**Expected output:**
```
INFO - Initialized Bosch LLM Farm client with model: claude-sonnet-4-5@20250929
INFO - Using storage mode: local
INFO - ToS Monitor application started successfully
INFO:     Uvicorn running on http://0.0.0.0:8080
```

---

## Step 7: Test Health Endpoint

```bash
# Terminal 2: Test health check
curl http://localhost:8080/health | jq
```

**Expected response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-03-15T10:30:00Z",
  "checks": {
    "storage": {
      "status": "healthy",
      "message": "Cloud Storage connection successful"
    },
    "llm": {
      "status": "healthy",
      "message": "LLM service connection successful",
      "model": "claude-sonnet-4-5@20250929"
    },
    "environment": {
      "status": "healthy",
      "message": "All required environment variables present"
    }
  }
}
```

**Check:**
- ✅ `status` should be `"healthy"`
- ✅ `checks.llm.status` should be `"healthy"`
- ✅ `checks.llm.model` should show your model

---

## Step 8: Test Document Sync

```bash
# Sync a single document
curl -X POST "http://localhost:8080/sync?document_ids=anthropic"
```

**Expected response:**
```json
{
  "success": true,
  "documents_synced": 1,
  "results": {
    "anthropic": {
      "success": true,
      "changes_detected": true,
      "message": "Document synced successfully"
    }
  }
}
```

---

## Step 9: Test Document Analysis (Full Workflow)

```bash
# Analyze with Bosch LLM Farm (plain text)
curl -X POST http://localhost:8080/tos/anthropic \
  -H "Content-Type: application/json" \
  -d '{
    "ai_provider": "bosch-llm-farm"
  }'
```

**Expected:** Plain text analysis output from Claude

```bash
# Analyze with HTML formatting
curl -X POST "http://localhost:8080/tos/anthropic?html=true" \
  -H "Content-Type: application/json" \
  -d '{
    "ai_provider": "bosch-llm-farm"
  }'
```

**Expected:** HTML formatted analysis

---

## Step 10: Test with Specific Versions

```bash
# List available versions
curl http://localhost:8080/tos/anthropic | jq
```

```bash
# Compare specific dates
curl -X POST http://localhost:8080/tos/anthropic \
  -H "Content-Type: application/json" \
  -d '{
    "ai_provider": "bosch-llm-farm",
    "prev": "2024-11-25",
    "last": "2024-12-11"
  }'
```

---

## Step 11: Test Error Handling

### Test with invalid token:
```bash
# Temporarily set wrong token
export ANTHROPIC_AUTH_TOKEN=invalid-token

python3 -c "
import os
from dotenv import load_dotenv
from app.llm_client import get_llm_client
import asyncio

async def test():
    client = get_llm_client('bosch-llm-farm')
    result = await client.test_connection()
    print('Should fail with 401/403:', result)

asyncio.run(test())
"
```

### Test with invalid model:
```bash
export BOSCH_LLM_MODEL=invalid-model

# Restart the app and check error message
```

---

## Quick Test Script (All-in-One)

```bash
#!/bin/bash
# save as test_bosch_llm.sh

echo "🧪 Bosch LLM Farm Integration Test Suite"
echo "=========================================="
echo ""

# Test 1: Environment
echo "Test 1: Environment Variables"
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
assert os.getenv('AI_PROVIDER') == 'bosch-llm-farm', 'Wrong provider'
assert os.getenv('ANTHROPIC_AUTH_TOKEN'), 'Missing token'
assert os.getenv('BOSCH_LLM_MODEL'), 'Missing model'
print('✅ PASS')
"

# Test 2: Client Init
echo "Test 2: Client Initialization"
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
from app.llm_client import get_llm_client
client = get_llm_client('bosch-llm-farm')
assert client.provider == 'bosch-llm-farm'
print('✅ PASS')
"

# Test 3: Connection
echo "Test 3: API Connection"
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
from app.llm_client import get_llm_client
import asyncio
async def test():
    client = get_llm_client('bosch-llm-farm')
    result = await client.test_connection()
    assert result, 'Connection failed'
    print('✅ PASS')
asyncio.run(test())
"

# Test 4: Analysis
echo "Test 4: Document Analysis"
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
from app.llm_client import get_llm_client
import asyncio
async def test():
    client = get_llm_client('bosch-llm-farm')
    result = await client.compare_documents(
        'Old text',
        'New text',
        'Test',
        'Compare: {previous_content} vs {current_content}',
        {}
    )
    assert result, 'Analysis failed'
    assert len(result) > 10, 'Response too short'
    print('✅ PASS')
asyncio.run(test())
"

echo ""
echo "🎉 All tests passed!"
echo "Bosch LLM Farm integration is working correctly."
```

**Run it:**
```bash
chmod +x test_bosch_llm.sh
./test_bosch_llm.sh
```

---

## Troubleshooting Common Issues

### Issue: "Connection failed" 
**Solution:**
```bash
# Test manually with curl
curl -X POST "https://aoai-farm.bosch-temp.com/api/google/v1/publishers/anthropic/models/claude-sonnet-4-5@20250929:rawPredict" \
  -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"anthropic_version":"vertex-2023-10-16","messages":[{"role":"user","content":"Hi"}],"max_tokens":10}'
```

### Issue: "Model not found (404)"
**Solution:**
```bash
# Check available models
echo "Available models:"
echo "- claude-sonnet-4-5@20250929"
echo "- claude-haiku-4-5@20251001"
echo ""
echo "Current model: $BOSCH_LLM_MODEL"
```

### Issue: "Authentication failed (401)"
**Solution:**
```bash
# Verify token
echo "Token length: ${#ANTHROPIC_AUTH_TOKEN}"
echo "Token starts with: ${ANTHROPIC_AUTH_TOKEN:0:10}..."
```

---

## Success Criteria

✅ Environment variables load correctly  
✅ Client initializes without errors  
✅ Connection test passes  
✅ Simple analysis completes successfully  
✅ Application starts without errors  
✅ Health endpoint shows all services healthy  
✅ Document sync works  
✅ Full analysis produces results  
✅ Error handling works correctly  

---

## Next Steps

Once all tests pass:
1. ✅ Test with real ToS documents
2. ✅ Test with multiple documents
3. ✅ Test scheduled monitoring
4. ✅ Deploy to Cloud Run (if needed)
5. ✅ Set up monitoring/alerting

