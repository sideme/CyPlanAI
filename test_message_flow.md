# Message Flow Test Guide

## Test Steps

### 1. Start the backend server
```bash
cd backend
source venv/bin/activate
python langgraph_server.py
```

### 2. Start the frontend dev server
```bash
cd frontend-LangChain
pnpm dev
```

### 3. Send a test message
1. Open a browser and visit http://localhost:3000
2. Open Developer Tools (F12)
3. Switch to the **Console** tab
4. Send the message "hi"

### 4. Inspect backend logs
On the backend terminal you should see entries such as:
- `📤 Sending SSE event with X messages` – indicates how many messages were sent
- `Message 0: type=human, id=..., content_length=...`
- `Message 1: type=ai, id=..., content_length=...`

### 5. Inspect frontend logs
In the browser console you should see:
- `📡 Stream Value Update:` – raw stream data received from the server
- `📨 Messages from values.messages:` – messages parsed from `values.messages`
- `📊 Messages Sources:` – comparison of the different message sources
- `✅ Final Messages Decision:` – final list chosen for rendering
- `🎨 Rendering Messages:` – messages actually rendered to the UI

### 6. Key checkpoints

#### Backend validation
- [ ] Did the backend send two messages (human + ai)?
- [ ] Is the ai message formatted correctly (`type: "ai", content: [{type: "text", text: "..."}]`)?

#### Frontend validation
- [ ] Is `valuesMessagesCount` equal to 2?
- [ ] Does `valuesMessagesTypes` contain `["human", "ai"]`?
- [ ] Is `finalMessages.length` equal to 2?
- [ ] Is `hasAI: true` set to `true`?
- [ ] Does `messagesToRender` contain exactly two messages?

### 7. If the issue persists

Please collect and share the following information:
1. The `📤 Sending SSE event` output from backend logs
2. The `📡 Stream Value Update` entry in the frontend console
3. The `✅ Final Messages Decision` entry in the frontend console
4. The `🎨 Rendering Messages` entry in the frontend console

