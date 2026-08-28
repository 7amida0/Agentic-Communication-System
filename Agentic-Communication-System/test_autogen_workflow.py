import asyncio
from workflow_runner import run_simulation

async def main():
    try:
        await run_simulation(number_of_orders=10,order_interval_seconds=5)
    except KeyboardInterrupt:
        print("\n[SYSTEM] Simulation stopped by user.")

if __name__=="__main__":
    asyncio.run(main())
