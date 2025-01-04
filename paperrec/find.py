import feedparser
import arxiv
from datetime import datetime, timedelta
from prisma import Prisma
from typing import TypedDict, List

class Paper(TypedDict):
    id: int
    title: str
    authors: List[str]
    summary: str
    published: datetime
    pdf_url: str
    relevanceScore: float


class PaperFinder:
    def __init__(self):
        self.db = Prisma()

    async def connect_db(self):
        await self.db.connect()

    async def disconnect_db(self):
        await self.db.disconnect()

    async def find_recent_ai_papers(self):
        """Find and store recent AI papers from arXiv in the cs.AI category"""
        # Get today's date and last three days date
        today = datetime.today()
        yesterday = today - timedelta(days=1)
        print(f"Searching for papers published since {yesterday.date()}")

        # Get papers from arXiv RSS feed
        feed_url = "https://rss.arxiv.org/atom/cs.AI"
        print("Fetching papers from arXiv RSS feed")
        feed = feedparser.parse(feed_url)
        all_paper_ids = [
            i.id.removeprefix("oai:arXiv.org:")
            for i in feed.entries
            if i.arxiv_announce_type == "new"
        ]
        client = arxiv.Client()
        for i in range(0, len(all_paper_ids), 50):
            search = arxiv.Search(id_list=all_paper_ids[i : i + 50])
            for result in client.results(search):
                if result.published.strftime("%Y%M%D") < yesterday.strftime("%Y%M%D"):
                    continue
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
