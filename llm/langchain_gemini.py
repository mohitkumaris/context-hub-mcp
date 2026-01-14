
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from typing import Optional
from config import config

logger = logging.getLogger(__name__)

class LangChainGeminiClient:
    """
    Client for interacting with Google's Gemini models via LangChain.
    """

    def __init__(self) -> None:
        """
        Initialize the LangChain Gemini client.
        Raises ValueError if API key is missing.
        """
        self.api_key = config.llm.gemini_api_key
        if not self.api_key:
            logger.error("GEMINI_API_KEY not found in configuration")
            raise ValueError("GEMINI_API_KEY is required")

        self.model_name = config.llm.gemini_model
        
        # Initialize the LangChain chat model
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=self.api_key,
            temperature=0.3,
            max_output_tokens=512,
            convert_system_message_to_human=True # Gemini sometimes needs this
        )
        
        logger.info(f"Initialized LangChain Gemini client with model: {self.model_name}")

    def generate(self, prompt: str) -> str:
        """
        Generate a response using LangChain.

        Args:
            prompt: Input text prompt

        Returns:
            Generated text response
        """
        try:
            messages = [HumanMessage(content=prompt)]
            response = self.llm.invoke(messages)
            
            # Handle different response formats from LangChain
            content = response.content
            
            # If content is a list (new format), extract text from parts
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and 'text' in part:
                        text_parts.append(part['text'])
                    elif isinstance(part, str):
                        text_parts.append(part)
                return ''.join(text_parts)
            
            # If content is already a string, return it directly
            return str(content)
        except Exception as e:
            logger.error(f"LangChain Gemini generation failed: {e}")
            return f"Error generating response: {str(e)}"
