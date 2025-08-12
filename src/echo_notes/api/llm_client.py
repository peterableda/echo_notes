"""LLM client for hosted language model interactions."""

import logging
from typing import Iterator, List, Dict, Any
from openai import OpenAI
from ..config.settings import Settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with hosted language models."""

    def __init__(self, settings: Settings):
        """Initialize the LLM client.

        Args:
            settings: Application settings containing API configuration
        """
        self.settings = settings
        self.client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.api_key
        )
        logger.info(f"LLM client initialized with model: {settings.llm_model_id}")

    def chat_with_context(
        self,
        messages: List[Dict[str, str]],
        context: str = "",
        temperature: float = 0.2,
        top_p: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = True
    ) -> Iterator[str]:
        """Chat with the LLM using provided context.

        Args:
            messages: List of chat messages in OpenAI format
            context: Additional context to inject (e.g., transcription content)
            temperature: Sampling temperature (0.0 to 2.0)
            top_p: Nucleus sampling parameter
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response

        Yields:
            Response chunks if streaming, otherwise single response
        """
        try:
            # Prepare messages with context if provided
            processed_messages = messages.copy()

            if context:
                # Add context as system message if not already present
                if not processed_messages or processed_messages[0]["role"] != "system":
                    context_message = {
                        "role": "system",
                        "content": f"You are an AI assistant helping to analyze and discuss a transcribed conversation. Here is the transcription for reference:\n\n{context}\n\nPlease answer questions about this transcription and help analyze its content. Be helpful and accurate."
                    }
                    processed_messages.insert(0, context_message)
                else:
                    # Append context to existing system message
                    processed_messages[0]["content"] += f"\n\nTranscription content:\n{context}"

            logger.info(f"Sending chat request with {len(processed_messages)} messages")

            completion = self.client.chat.completions.create(
                model=self.settings.llm_model_id,
                messages=processed_messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stream=stream
            )

            if stream:
                for chunk in completion:
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
            else:
                yield completion.choices[0].message.content

        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            yield f"Error: Unable to get response from LLM. {str(e)}"


