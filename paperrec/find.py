import arxiv
from datetime import datetime, timedelta
from prisma import Prisma


class PaperFinder:
    def __init__(self):
        self.db = Prisma()

    async def connect_db(self):
        await self.db.connect()

    async def disconnect_db(self):
        await self.db.disconnect()

    async def find_recent_ai_papers(self):
        """Find and store recent AI papers from arXiv in the cs.AI category"""
        # Get today's date and last week's date
        today = datetime.today()
        last_week = today - timedelta(days=7)
        print(f"Searching for papers published since {last_week.date()}")

        # Search for papers in cs.AI category published since last week
        client = arxiv.Client()
        print("Connected to arXiv API")
        search = arxiv.Search(
            query=f"cat:cs.AI AND submittedDate:[{last_week.strftime('%Y%m%d')} TO {today.strftime('%Y%m%d')}]",
            # max_results=100,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        # Store papers in database
        for result in client.results(search):
            print(f"Found paper: {result.title}")
            # Check if paper already exists
            existing_paper = await self.db.paper.find_first(
                where={"title": result.title}
            )
            if not existing_paper:
                try:
                    await self.db.paper.create(
                        {
                            "title": result.title,
                            "authors": [a.name for a in result.authors],
                            "summary": result.summary,
                            "published": result.published,
                            "pdf_url": result.pdf_url,
                        }
                    )
                    print(f"Successfully stored paper: {result.title}")
                except Exception as e:
                    print(f"Failed to store paper {result.title}: {str(e)}")
            else:
                print(f"Paper already exists: {result.title}")


async def main():
    finder = PaperFinder()
    await finder.connect_db()
    try:
        await finder.find_recent_ai_papers()
    finally:
        await finder.disconnect_db()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
