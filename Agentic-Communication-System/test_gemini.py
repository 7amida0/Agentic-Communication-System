import asyncio

from services.llm_service import LLMService


async def main() -> None:
    llm = LLMService()

    response = await llm.ask(
        system_prompt=(
            "You are a manufacturing expert. "
            "Use simple English."
        ),
        user_prompt=(
            "Explain in one sentence why a machine "
            "with a critical warning should be blocked."
        ),
    )

    print("\nGEMINI RESPONSE:")
    print(response)

    await llm.close()


if __name__ == "__main__":
    asyncio.run(main())