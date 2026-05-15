"""Run once to initialize the Qdrant collection before first start."""
import asyncio
import sys
sys.path.insert(0, "../backend")

from agent.memory import MemoryManager


async def main():
    m = MemoryManager()
    await m.init_collection()
    print("✅ Qdrant collection ready.")


asyncio.run(main())
