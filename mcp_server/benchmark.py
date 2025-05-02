import time
import asyncio
from rag import fetch_all_pairs_async


async def benchmark():
    counts = [50, 100, 200, 300, 500, 800, 1000, 2000, 4000]
    concurrents = [1, 2, 4, 8, 16, 32, 64]
    results = []
    for count in counts:
        for max_concurrent in concurrents:
            start = time.perf_counter()
            try:
                await fetch_all_pairs_async(count=count, max_concurrent=max_concurrent)
                duration = time.perf_counter() - start
                results.append((count, max_concurrent, duration, "OK"))
            except Exception as e:
                duration = time.perf_counter() - start
                results.append((count, max_concurrent, duration, str(e)))
    for r in results:
        print(f"count={r[0]}, max_concurrent={r[1]}, time={r[2]:.2f}s, status={r[3]}")


if __name__ == "__main__":
    asyncio.run(benchmark())
