import os
from dotenv import load_dotenv

load_dotenv()

# Default frontend origins for local development
DEFAULT_CORS_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///cyplanai.db'
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = False  # Set to appropriate time in production
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    ANTHROPIC_MODEL = os.environ.get('ANTHROPIC_MODEL', 'claude-3-5-haiku-latest')
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.1')
    # DeepSeek configuration (compatible with OpenAI API format)
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
    DEEPSEEK_API_BASE = os.environ.get('DEEPSEEK_API_BASE', 'https://api.deepseek.com')
    DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')
    # Qwen configuration
    DASHSCOPE_API_KEY = os.environ.get('DASHSCOPE_API_KEY')
    DASHSCOPE_BASE_URL = os.environ.get('DASHSCOPE_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
    QWEN_MODEL = os.environ.get('QWEN_MODEL', 'qwen-long')
    
    LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'openai')  # openai|anthropic|ollama|deepseek|qwen
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', ",".join(DEFAULT_CORS_ORIGINS)).split(',')
    # Vector database configuration
    VECTOR_DB_PATH = os.environ.get('VECTOR_DB_PATH', './vector_db')
    CHUNK_SIZE = int(os.environ.get('CHUNK_SIZE', '1000'))
    CHUNK_OVERLAP = int(os.environ.get('CHUNK_OVERLAP', '200'))

