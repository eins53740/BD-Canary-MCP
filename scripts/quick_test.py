import asyncio
from src.canary_mcp.server import search_tags

async def main():
    result = await search_tags("300 - Raw Meal Production.321 - Raw Mill.Normalised.Quality.Raw Meal.ALBITE.Value")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())