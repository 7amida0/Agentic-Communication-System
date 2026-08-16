import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

class LLMService:
    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        model_name = os.getenv(
            "GEMINI_MODEL",
            "gemini-2.5-flash",
        )

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY was not found. "
                "Make sure the .env file is beside main.py."
            )

        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    async def ask(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.2,
                ),
            )

            if response.text:
                return response.text

            return "Gemini did not generate a response."

        except Exception as error:
            return f"Gemini API error: {error}"

    async def close(self) -> None:
        await self.client.aio.aclose()
        self.client.close()
