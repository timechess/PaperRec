import feedparser
import re
from datetime import datetime, timedelta, timezone
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
        today = datetime.now(timezone.utc)
        yesterday = today - timedelta(days=1)
        print(f"Searching for papers published since {yesterday.date()}")

        # Get papers from arXiv RSS feed
        feed_url = "https://rss.arxiv.org/atom/cs.AI"
        print("Fetching papers from arXiv RSS feed")
        feed = feedparser.parse(feed_url)
        for i in feed.entries:
            if i.arxiv_announce_type != "new":
                continue
            published = datetime.fromisoformat(i.published)
            if published < yesterday:
                continue
            authors = i.authors[0]["name"].split(",")
            match = re.search(r'Abstract:\s*(.*)', i.summary)

            if match:
                abstract_content = match.group(1)
            else:
                print("No abstract found.")
            print(f"Found paper: {i.title}")
            # Check if paper already exists
            existing_paper = await self.db.paper.find_first(
                where={"title": i.title}
            )
            arxiv_id = i.id.removeprefix("oai:arXiv.org:")
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
            if not existing_paper:
                try:
                    await self.db.paper.create(
                        {
                            "title": i.title,
                            "authors": [author.strip() for author in authors],
                            "summary": abstract_content,
                            "published": published,
                            "pdf_url": pdf_url,
                        }
                    )
                    print(f"Successfully stored paper: {i.title}")
                except Exception as e:
                    print(f"Failed to store paper {i.title}: {str(e)}")
            else:
                print(f"Paper already exists: {i.title}")


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
