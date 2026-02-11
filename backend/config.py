"""
Configuration management
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Export configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
