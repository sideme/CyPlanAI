import os
import tempfile
import time
from typing import Optional

from openai import OpenAI
from openai.types.file_object import FileObject


class QwenFileService:
    """
    Service for uploading files to DashScope for use with Qwen-Long.
    
    Based on official documentation:
    https://www.alibabacloud.com/help/en/model-studio/long-context-qwen-long
    """
    
    _client: Optional[OpenAI] = None

    @classmethod
    def _get_client(cls) -> OpenAI:
        """Get or create the OpenAI client for DashScope."""
        if cls._client is None:
            api_key = os.environ.get("DASHSCOPE_API_KEY")
            if not api_key:
                raise ValueError("DASHSCOPE_API_KEY not found in environment")
            cls._client = OpenAI(
                api_key=api_key,
                base_url=os.getenv(
                    "DASHSCOPE_BASE_URL",
                    "https://dashscope.aliyuncs.com/compatible-mode/v1",
                ),
            )
        return cls._client

    @staticmethod
    def upload_file(file_data: bytes, filename: str) -> Optional[str]:
        """
        Upload a file to DashScope and wait for processing to complete.
        
        Per official docs:
        1. Upload file with purpose="file-extract"
        2. Poll status until it becomes "processed"
        3. Return the file_id for use in chat messages
        
        The model will automatically read file content when you reference it as:
        {"role": "system", "content": "fileid://<file_id>"}
        
        NO manual text extraction is needed!
        
        Args:
            file_data: The file bytes
            filename: The original filename
            
        Returns:
            The file_id if successful (status="processed"), None otherwise
        """
        client = QwenFileService._get_client()
        temp_path = None
        
        try:
            # Step 1: Write to temporary file
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=os.path.splitext(filename)[1]
            ) as temp_file:
                temp_file.write(file_data)
                temp_path = temp_file.name

            # Step 2: Upload to DashScope
            print(f"📤 Uploading {filename} to DashScope...")
            with open(temp_path, "rb") as f:
                file_obj = client.files.create(file=f, purpose="file-extract")

            file_id = getattr(file_obj, "id", None)
            if not file_id:
                print(f"❌ Unexpected DashScope response: {file_obj}")
                return None

            # Step 3: Poll for processing status
            # Per docs: "Longer documents may take more time to parse"
            print(f"⏳ Waiting for DashScope to process {filename}...")
            start_time = time.time()
            timeout = 120  # 2 minutes timeout
            
            while True:
                current_file_status: FileObject = client.files.retrieve(file_id)
                status = current_file_status.status
                
                if status == "processed":
                    elapsed = time.time() - start_time
                    print(f"✅ File {filename} successfully processed in {elapsed:.1f}s (ID: {file_id})")
                    return file_id
                    
                elif status == "error":
                    error_details = getattr(current_file_status, "status_details", "Unknown error")
                    print(f"❌ DashScope processing failed for {file_id}: {error_details}")
                    return None
                    
                elif time.time() - start_time > timeout:
                    print(f"⏱️  DashScope processing timed out for {file_id} after {timeout}s")
                    return None
                
                # Still processing (status might be "uploaded", "processing", "pending", etc.)
                time.sleep(2)  # Check every 2 seconds

        except Exception as e:
            print(f"❌ DashScope file upload failed: {e}")
            import traceback
            traceback.print_exc()
            return None
            
        finally:
            # Clean up temporary file
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
