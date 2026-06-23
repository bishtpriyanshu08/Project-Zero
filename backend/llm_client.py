# =============================================================================
# llm_client.py — LLM Abstraction Layer
# =============================================================================
# Provides a unified interface for calling LLMs (Gemini or OpenAI) with
# structured output. The key function is `generate_structured()` which takes
# a prompt and a Pydantic model, and returns a validated instance of that model.
#
# Supports:
#   - Google Gemini API (primary) — uses native response_schema
#   - OpenAI API (fallback) — uses response_format with JSON schema
#
# Both providers guarantee JSON conformance through their respective APIs.
# =============================================================================

import json
import time
import logging
from typing import Type, TypeVar

# pyrefly: ignore [missing-import]
from pydantic import BaseModel

# Type variable for generic Pydantic model returns
T = TypeVar("T", bound=BaseModel)

# Configure logging
logger = logging.getLogger(__name__)


class LLMClient:
    """
    Unified LLM client that supports both Gemini and OpenAI APIs.
    
    Usage:
        client = LLMClient(provider="gemini", api_key="your-key")
        result = client.generate_structured(
            prompt="Build a CRM system",
            response_model=IntentResult,
            system_prompt="Extract the application intent..."
        )
    """
    
    def __init__(self, provider: str = "gemini", api_key: str = "", model_name: str = ""):
        """
        Initialize the LLM client.
        
        Args:
            provider: "gemini" or "openai"
            api_key: API key for the chosen provider
            model_name: Optional model override (defaults to best available)
        """
        self.provider = provider.lower()
        self.api_key = api_key
        self.max_retries = 3           # Number of retry attempts on failure
        self.retry_delay = 2           # Seconds between retries (doubles each attempt)
        self.temperature = 0.2         # Low temperature for deterministic outputs
        
        # Set default model names if not provided
        if model_name:
            self.model_name = model_name
        elif self.provider == "gemini":
            self.model_name = "gemini-2.5-flash"
        else:
            self.model_name = "gpt-4o-mini"
        
        # Initialize the appropriate client
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """
        Initialize the provider-specific client.
        Deferred import so users only need the SDK for their chosen provider.
        """
        if self.provider == "gemini":
            try:
                # pyrefly: ignore [missing-import]
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info(f"Gemini client initialized with model: {self.model_name}")
            except ImportError:
                raise ImportError(
                    "Google GenAI SDK not installed. Run: pip install google-genai"
                )
        elif self.provider == "openai":
            try:
                # pyrefly: ignore [missing-import]
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
                logger.info(f"OpenAI client initialized with model: {self.model_name}")
            except ImportError:
                raise ImportError(
                    "OpenAI SDK not installed. Run: pip install openai"
                )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}. Use 'gemini' or 'openai'.")
    
    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: str = ""
    ) -> T:
        """
        Call the LLM and return a validated Pydantic model instance.
        
        This is the main entry point for all LLM interactions in the pipeline.
        It handles retries, error handling, and response parsing.
        
        Args:
            prompt: The user prompt to send to the LLM
            response_model: The Pydantic model class to validate the response against
            system_prompt: Optional system-level instructions for the LLM
            
        Returns:
            A validated instance of the response_model
            
        Raises:
            RuntimeError: If all retry attempts fail
        """
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"LLM call attempt {attempt}/{self.max_retries} "
                    f"(model={self.model_name}, schema={response_model.__name__})"
                )
                
                if self.provider == "gemini":
                    result = self._call_gemini(prompt, response_model, system_prompt)
                else:
                    result = self._call_openai(prompt, response_model, system_prompt)
                
                logger.info(f"LLM call succeeded on attempt {attempt}")
                return result
                
            except Exception as e:
                last_error = e
                logger.warning(f"LLM call attempt {attempt} failed: {str(e)}")
                
                if attempt < self.max_retries:
                    sleep_time = self.retry_delay * (2 ** (attempt - 1))
                    logger.info(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
        
        # All retries exhausted
        raise RuntimeError(
            f"LLM call failed after {self.max_retries} attempts. "
            f"Last error: {str(last_error)}"
        )
    
    def _call_gemini(self, prompt: str, response_model: Type[T], system_prompt: str) -> T:
        """
        Call the Gemini API with structured output.
        
        Uses the native response_schema parameter which guarantees
        the response conforms to our Pydantic model.
        """
        # pyrefly: ignore [missing-import]
        from google import genai
        # pyrefly: ignore [missing-import]
        from google.genai import types
        
        # Build the configuration with structured output
        config = types.GenerateContentConfig(
            temperature=self.temperature,
            response_mime_type="application/json",
            response_schema=response_model,
        )
        
        # Add system instruction if provided
        if system_prompt:
            config.system_instruction = system_prompt
        
        # Make the API call
        response = self._client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )
        
        # Parse the response — Gemini returns a parsed Pydantic object
        # when response_schema is set, but we also handle raw JSON fallback
        if hasattr(response, 'parsed') and response.parsed is not None:
            return response.parsed
        
        # Fallback: parse the text response as JSON
        raw_text = response.text
        data = json.loads(raw_text)
        return response_model.model_validate(data)
    
    def _call_openai(self, prompt: str, response_model: Type[T], system_prompt: str) -> T:
        """
        Call the OpenAI API with structured output.
        
        Uses response_format with JSON schema to ensure conformance.
        """
        # Build messages list
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Generate JSON schema from the Pydantic model
        json_schema = response_model.model_json_schema()
        
        # Make the API call with JSON mode
        response = self._client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "schema": json_schema,
                    "strict": True
                }
            }
        )
        
        # Parse the response
        raw_text = response.choices[0].message.content
        data = json.loads(raw_text)
        return response_model.model_validate(data)
