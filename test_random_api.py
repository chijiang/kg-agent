import asyncio
import httpx


async def test_random_instances():
    # We need a token, but let's see if we can at least hit the endpoint and get a 401/403
    # or if we can find a way to bypass for local testing.
    # Actually, it's better to just run the backend tests if they exist.
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(
                "http://localhost:8000/api/graph/instances/random?limit=10"
            )
            print(f"Status: {res.status_code}")
            print(f"Data: {res.json()}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_random_instances())
