from datetime import datetime, timedelta
from typing import List, Dict, TypedDict
import logging
import yagmail
from prisma import Prisma
import os
from openai import OpenAI
import json


class Paper(TypedDict):
    id: int
    title: str
    authors: List[str]
    summary: str
    published: datetime
    pdf_url: str
    relevanceScore: float


class Config:
    def __init__(self):
        self.deepseek_api = os.getenv("DEEPSEEK_API_KEY")
        self.keywords = os.getenv("USER_KEYWORDS")
        self.email_address = os.getenv("EMAIL_ADDRESS")
        self.email_password = os.getenv("EMAIL_PASSWORD")
        self.receive_email_address = os.getenv("RECEIVE_EMAIL")
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))

        if not self.deepseek_api:
            raise ValueError("DEEPSEEK_API environment variable is required")
        if not self.keywords:
            raise ValueError("USER_KEYWORDS environment variable is required")
        if not self.email_address or not self.email_password:
            raise ValueError("Email credentials are required")


class PaperRecommender:
    def __init__(self):
        self.db = Prisma()
        self.logger = logging.getLogger(__name__)

    async def connect_db(self) -> None:
        await self.db.connect()
        self.logger.info("Database connected")

    async def disconnect_db(self) -> None:
        await self.db.disconnect()
        self.logger.info("Database disconnected")

    async def find_papers_today(self) -> List[Paper]:
        """Find papers published today, handling month boundaries"""
        today = datetime.today().date()

        # Handle month boundaries
        if today.day == 1:
            # First day of month, look at last day of previous month
            prev_month = today.replace(day=1) - timedelta(days=1)
            start_date = datetime(prev_month.year, prev_month.month, prev_month.day - 2)
        else:
            start_date = datetime(today.year, today.month, today.day - 1)

        end_date = datetime(today.year, today.month, today.day)

        papers = await self.db.paper.find_many(
            where={"published": {"gte": start_date, "lt": end_date}}
        )
        return [dict(paper) for paper in papers]

    async def recommend_papers(self) -> List[Paper]:
        """Recommend papers based on user preferences"""
        raise NotImplementedError()


class DeepSeekPaperRecommender(PaperRecommender):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.client = OpenAI(
            api_key=self.config.deepseek_api, base_url="https://api.deepseek.com"
        )

    def _generate_markdown(self, papers: List[Paper]) -> str:
        """Generate markdown content from recommended papers"""
        markdown = "# Daily Recommended Papers\n\n"
        for paper in papers:
            markdown += f"## {paper['title']}\n\n"
            markdown += f"{paper['summary']}\n\n"
            markdown += f"**Published:** {paper['published'].strftime('%Y-%m-%d')}\n\n"
            markdown += "---\n\n"
        return markdown

    async def _send_email(self, markdown: str) -> None:
        """Send markdown content via email"""
        yag = yagmail.SMTP(
            host="smtp.qq.com",
            user=self.config.email_address,
            password=self.config.email_password,
            smtp_ssl=True,
        )
        try:
            yag.send(
                self.config.receive_email_address, "Daily Recommendation", markdown
            )
            self.logger.info("Successfully send email.")
        except Exception as e:
            self.logger.error(f"Error sending email {e}")

    async def store_recommendation(self, paper_id: int, relevance: float):
        """Store recommendation in database"""
        await self.db.paper.update(
            where={"id": paper_id},
            data={"relevanceScore": relevance}
        )

    def prompt(self, abstract: str) -> List[Dict[str, str]]:
        """Generate prompt for DeepSeek API"""
        system_prompt = """You are an expert in assessing research paper relevance.
The user will provide an abstract and keywords. Evaluate the relevance between the paper and keywords.
Return a JSON object with a relevance score between 0 and 1, where 1 is highly relevant.

Example Output:
{
    "relevance": 0.9
}"""
        user_prompt = f"""Abstract: {abstract}

Keywords: {self.config.keywords}"""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    async def recommend_papers(self) -> List[Paper]:
        """Recommend papers using DeepSeek API"""
        papers: List[Paper] = await self.find_papers_today()
        recommended: List[Paper] = []

        for paper in papers:
            paper_id = paper.get("id")
            if not paper_id:
                continue

            # Check relevance score in database
            db_paper = await self.db.paper.find_unique(where={"id": paper_id})
            if db_paper and db_paper.relevanceScore > 0.5:
                recommended.append(paper)
                continue

            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=self.prompt(paper["summary"]),
                    response_format={"type": "json_object"},
                    timeout=10,
                )

                result = json.loads(response.choices[0].message.content)
                relevance = result.get("relevance", 0)

                if relevance > 0.5:
                    recommended.append(paper)
                    self.logger.info(f"Recommended paper: {paper['title']}")
                    await self.store_recommendation(paper_id, relevance)

            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error for paper {paper_id}: {e}")
            except Exception as e:
                self.logger.error(f"Error processing paper {paper_id}: {e}")

        if recommended:
            # Generate and send markdown report
            markdown = self._generate_markdown(recommended)
            await self._send_email(markdown)

        return recommended
