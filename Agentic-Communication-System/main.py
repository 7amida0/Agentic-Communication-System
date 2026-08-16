import asyncio

from services.llm_service import LLMService


async def main() -> None:
    llm = LLMService()

    try:
        response = await llm.ask(
            system_prompt=(
                "You are a manufacturing assistant."
            ),
            user_prompt=(
                "Reply with exactly: LLM connection successful."
            ),
        )

        print(response)

    finally:
        await llm.close()


if __name__ == "__main__":
    asyncio.run(main())