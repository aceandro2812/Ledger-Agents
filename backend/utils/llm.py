import os
import json
from typing import Type, TypeVar, Optional, Any, Dict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from pydantic import BaseModel
import litellm
from dotenv import load_dotenv
from backend.utils.config import get_llm_settings

# Load environment variables (.env file for dev mode)
load_dotenv()

# Configure LiteLLM
litellm.drop_params = True
litellm.telemetry = False

# Hard wall-clock timeout for any single LLM call.
# Free-tier reasoning models hold the HTTP connection alive while generating
# chain-of-thought, which defeats httpx read timeouts.  A threading timeout
# guarantees we never hang for more than this many seconds.
_LLM_HARD_TIMEOUT_SECS = 30


def _call_with_timeout(fn, timeout_secs: int = _LLM_HARD_TIMEOUT_SECS):
    """Run fn() in a worker thread and raise RuntimeError if it takes too long."""
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="llm_req") as ex:
        fut = ex.submit(fn)
        try:
            return fut.result(timeout=timeout_secs)
        except FutureTimeout:
            raise RuntimeError(
                f"LLM API call exceeded the hard timeout of {timeout_secs}s. "
                "Check your model/API key, or switch to a faster model."
            )

T = TypeVar("T", bound=BaseModel)

class LLMClient:
    def __init__(self):
        settings = get_llm_settings()
        self.api_key = settings["api_key"]
        self.base_url = settings["base_url"]
        self.model = settings["model"]

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def call_chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        timeout_secs: int = _LLM_HARD_TIMEOUT_SECS,
    ) -> str:
        """
        Sends a chat request to the LLM and returns the text response.
        Use timeout_secs to override the default hard timeout (e.g. pass a larger
        value for long-form generation tasks like audit memo writing).
        """
        if not self.is_configured():
            raise ValueError(
                "LLM client is not configured. Please set LLM_API_KEY in the environment or .env file."
            )
        
        try:
            kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": temperature,
                "api_key": self.api_key,
                "timeout": timeout_secs,
            }
            if self.base_url:
                kwargs["base_url"] = self.base_url

            response = _call_with_timeout(lambda: litellm.completion(**kwargs), timeout_secs)
            return response.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"Error calling LLM provider via LiteLLM: {str(e)}")

    def call_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        temperature: float = 0.1,
        timeout_secs: int = _LLM_HARD_TIMEOUT_SECS,
    ) -> T:
        """
        Sends a request to the LLM and parses the response into a Pydantic model.
        Use timeout_secs to override the default hard timeout (e.g. pass a larger
        value for long-form generation tasks like audit memo writing).
        """
        if not self.is_configured():
            raise ValueError(
                "LLM client is not configured. Please set LLM_API_KEY in the environment or .env file."
            )
            
        try:
            prompt_with_instructions = (
                f"{user_prompt}\n\nIMPORTANT: Return ONLY a valid JSON object matching the schema below. "
                f"Do not wrap the JSON in ```json markdown formatting, and do not add any conversational text.\n"
                f"Schema:\n{json.dumps(response_model.model_json_schema(), indent=2)}"
            )
            
            kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt_with_instructions}
                ],
                "response_format": {"type": "json_object"},
                "temperature": temperature,
                "api_key": self.api_key,
                "timeout": timeout_secs,
            }
            if self.base_url:
                kwargs["base_url"] = self.base_url

            response = _call_with_timeout(lambda: litellm.completion(**kwargs), timeout_secs)
            content = response.choices[0].message.content or ""
            # Strip markdown code fences that some models add despite instructions
            cleaned = content.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned.strip())
            return response_model.model_validate(data)

        except Exception as e:
            raise RuntimeError(
                f"Failed to obtain structured output from LLM via LiteLLM: {str(e)}"
            )

