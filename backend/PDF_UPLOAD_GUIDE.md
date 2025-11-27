# PDF File Upload Feature Guide

## Overview

Based on the official Alibaba Cloud documentation [Long context (Qwen-Long)](https://www.alibabacloud.com/help/en/model-studio/long-context-qwen-long), PDF file upload functionality has been successfully implemented.

## How It Works

### 1. File Upload Flow

```
Frontend uploads PDF → Backend receives → Uploads to DashScope → Waits for processing → Gets file_id
```

### 2. Conversation Reference Flow

```
User message + fileid://xxx → Qwen-Long automatically reads file content → Generates response
```

**Key Points**:
- ✅ **No need** to manually extract PDF text
- ✅ **No need** to call `files.content` API
- ✅ **No need** to use `responses` API
- ✅ Just upload the file and reference `fileid://...`, the model will automatically read it!

## Configuration Requirements

Configure the following environment variables in the `.env` file:

```bash
# Use Qwen as LLM provider
LLM_PROVIDER=qwen

# DashScope API Key (obtain from Alibaba Cloud)
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxx

# Use Qwen-Long model (supports long documents)
QWEN_MODEL=qwen-long

# DashScope API URL (default value, usually no need to modify)
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

## Code Implementation

### 1. `services/qwen_service.py`

Simplified file upload service:

```python
class QwenFileService:
    @staticmethod
    def upload_file(file_data: bytes, filename: str) -> Optional[str]:
        """
        Upload file to DashScope and wait for processing to complete
        Returns file_id for conversation reference
        """
        # 1. Create temporary file
        # 2. Call client.files.create(file=f, purpose="file-extract")
        # 3. Poll status until it becomes "processed"
        # 4. Return file_id
```

**Note**: All text extraction logic (`extract_file_text`, `_extract_via_responses`, etc.) has been removed, as these are unnecessary according to the official documentation.

### 2. `langgraph_server.py`

PDF processing logic:

```python
if llm_provider == 'qwen':
    file_id = QwenFileService.upload_file(pdf_bytes, filename)
    
    if file_id:
        # Add file reference to message
        processed_content.append({
            "type": "text",
            "text": f"[Uploaded file: {filename}]"
        })
        processed_content.append({
            "type": "text",
            "text": f"fileid://{file_id}"
        })
        # That's it! The model will automatically read the file content
```

### 3. `langgraph_agent.py`

Reference files in system prompt:

```python
def agent_node(state: AgentState):
    # Extract file_ids from message metadata
    file_ids = latest_user_msg.additional_kwargs.get("file_ids", [])
    
    if file_ids:
        # Add file references to system prompt
        system_text += (
            "\n\nREFERENCE FILES:\n"
            + "\n".join(f"- fileid://{fid}" for fid in file_ids)
            + "\nUse these uploaded documents when crafting your answer."
        )
    
    # Pass file_ids to LLM
    if file_ids:
        llm_to_use = llm.bind(extra_body={"file_ids": file_ids})
    
    response = llm_to_use.invoke(normalized_messages)
```

## Official Documentation Highlights

### Upload File

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# Upload file
file_object = client.files.create(
    file=Path("document.pdf"), 
    purpose="file-extract"
)
print(file_object.id)  # Get file_id
```

### Reference File in Conversation

```python
completion = client.chat.completions.create(
    model="qwen-long",
    messages=[
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'system', 'content': f'fileid://{FILE_ID}'},  # Key!
        {'role': 'user', 'content': 'What does this article talk about?'}
    ]
)
```

### Important Notes

1. **File Processing Time**:
   - Longer documents may take more time to parse
   - After upload, need to poll `status` until it becomes `"processed"`
   - If calling the model before parsing completes, will return 400 error: "File parsing in progress"

2. **File Limitations**:
   - Supported formats: TXT, DOCX, PDF, XLSX, EPUB, MOBI, MD, CSV, JSON, images, etc.
   - PDF file size limit: 150 MB
   - Image file size limit: 20 MB
   - Maximum 10,000 files per account, total size not exceeding 100 GB

3. **Billing Information**:
   - File upload, storage, and parsing: **Free**
   - When calling the model, referenced file content counts toward **Input Tokens**
   - Example: A 100-page PDF will consume tokens for that file in every conversation

## Usage

### Frontend Upload

Users click the "Upload files" button in the frontend interface to select a PDF or Word document. The frontend encodes the file as base64 and sends it to the backend.

### Backend Processing

1. Receive base64-encoded document data
2. Decode to binary data
3. Call `QwenFileService.upload_file()` to upload to DashScope
4. Wait for file processing to complete (status = "processed")
5. Add `file_id` to message's `additional_kwargs`
6. Add `fileid://xxx` reference to message content

### Agent Processing

1. Agent extracts `file_ids` from `HumanMessage.additional_kwargs`
2. Adds file references to system prompt
3. Passes to model using `llm.bind(extra_body={"file_ids": file_ids})`
4. Qwen-Long automatically reads file content and generates response

## Testing Steps

1. **Start Backend**:
   ```bash
   cd backend
   source venv/bin/activate
   python langgraph_server.py
   ```

2. **Start Frontend**:
   ```bash
   cd frontend-LangChain
   pnpm dev
   ```

3. **Test Upload**:
   - Open browser and visit http://localhost:3000
   - Click "Upload files" button
- Select a PDF or Word document
   - Enter a question, e.g., "What does this file talk about?"
   - Observe backend logs, should see:
     ```
    📤 Uploading sample.docx to DashScope...
    ⏳ Waiting for DashScope to process sample.docx...
    ✅ File sample.docx successfully processed in X.Xs (ID: file-fe-xxx)
    📄 File reference added. Model will read content automatically.
     ```

4. **Verify Response**:
- Qwen-Long should be able to read document content and answer questions
   - If it fails, check:
     - Is `DASHSCOPE_API_KEY` correct?
     - Is `LLM_PROVIDER` set to `qwen`?
     - Is `QWEN_MODEL` set to `qwen-long`?
     - Has the file been processed (status = "processed")?

## Troubleshooting

### Issue 1: File Upload Failed

**Symptoms**: Log shows "❌ DashScope file upload failed"

**Solution**:
- Check if `DASHSCOPE_API_KEY` is configured correctly
- Confirm API Key has sufficient quota
- Check if network connection is normal

### Issue 2: File Processing Timeout

**Symptoms**: Log shows "⏱️ DashScope processing timed out"

**Solution**:
- File may be too large, try reducing file size
- Increase `timeout` value (in `qwen_service.py`)
- Retry later

### Issue 3: Model Cannot Read File

**Symptoms**: Model responds "I cannot access this file"

**Solution**:
- Confirm file `status` is `"processed"`
- Check if message contains `fileid://...` reference
- Check if `file_ids` are correctly passed to LLM
- Review debug information in backend logs

### Issue 4: Unsupported File Format

**Symptoms**: Error returned after upload

**Solution**:
- Confirm file format is in the supported list
- PDF files cannot exceed 150 MB
- Try converting file format

## References

- [Alibaba Cloud Model Studio - Long context (Qwen-Long)](https://www.alibabacloud.com/help/en/model-studio/long-context-qwen-long)
- [Alibaba Cloud Model Studio - Long context (Qwen-Long) - Chinese](https://www.alibabacloud.com/help/zh/model-studio/long-context-qwen-long)
- [OpenAI Python SDK](https://github.com/openai/openai-python)

## Changelog

### 2025-11-20
- ✅ Simplified `QwenFileService`, removed all unnecessary text extraction logic
- ✅ Updated `langgraph_server.py` PDF processing logic
- ✅ Implemented file upload and reference mechanism according to official documentation
- ✅ Added detailed log output and error handling
- ✅ Created this document explaining implementation details
