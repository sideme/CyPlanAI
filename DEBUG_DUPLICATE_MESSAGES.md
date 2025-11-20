# Debugging Duplicate Messages Issue

## Current Status

After restarting the server, uploading a PDF file still displays two user messages.

## Diagnostic Steps

### 1. Check Backend Logs

Restart the backend, upload a file, and look for these logs:

```bash
cd backend
python langgraph_server.py
```

Key logs:
- `📤 Uploading Document.pdf to DashScope...`
- `✅ File uploaded successfully: file-fe-xxx`
- `🔍 Formatting human message: id=xxx has_client_id=True/False`

**Key Checks**:
1. Are there two `🔍 Formatting human message` logs?
2. Are the two `id` values the same?
3. Is `has_client_id` `True`?

### 2. Check Frontend Console

Open browser DevTools Console, look for:
- Message structure being sent
- SSE events received
- Deduplication logic execution

### 3. Possible Causes

#### Cause A: Backend Returns User Message Twice

**Symptoms**: Backend logs show two `🔍 Formatting human message` entries

**Reason**: LangGraph state updates may contain the same message twice (once in "values", once in "updates")

**Solution**: Deduplicate in backend

#### Cause B: Frontend Deduplication Failed

**Symptoms**:
- Backend only returns once
- Frontend displays twice
- ID mismatch

**Reason**:
1. `client_message_id` not correctly passed
2. Different content generates different hash IDs
3. Deduplication logic has a bug

**Solution**: Ensure ID is passed correctly

#### Cause C: Optimistic Message Not Replaced

**Symptoms**:
- Frontend first displays optimistic message (with file preview)
- Then adds backend-returned message (without file preview)
- Both messages coexist

**Reason**: Deduplication logic didn't recognize these as the same message

**Solution**: Improve deduplication logic, or ensure content structure is consistent

## Next Steps

Please restart backend and frontend, then:

1. **Upload file and send message**
2. **Copy all `🔍 Formatting human message` lines** from backend logs
3. **Screenshot the two messages** displayed in frontend
4. **Tell me**:
   - Did backend print human message twice?
   - What are the two `id` values?
   - Is `has_client_id` True or False?

This will help me accurately locate the issue.
