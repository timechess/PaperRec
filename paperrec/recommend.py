from datetime import datetime, timedelta, timezone
from typing import List, Dict
import logging
from email.header import Header
from email.mime.text import MIMEText
import smtplib
from prisma import Prisma
import os
from openai import OpenAI
import json
import markdown
from .find import Paper
from .email import render_email


class Config:
    def __init__(self):
        self.deepseek_api = os.getenv("DEEPSEEK_API_KEY")
        self.keywords = os.getenv("USER_KEYWORDS")
        self.email_address = os.getenv("EMAIL_ADDRESS")
        self.email_password = os.getenv("EMAIL_PASSWORD")
        self.receive_email_address = os.getenv("RECEIVE_EMAIL").split(",")
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
        today = datetime.now(timezone.utc)

        start_date = today - timedelta(days=1)


        papers = await self.db.paper.find_many(
            where={"published": {"gte": start_date, "lte": today}}
        )
        return [Paper(paper) for paper in papers]

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

    def _generate_summary(self, papers: List[Paper]) -> str:
        """Generate Chinese summary for all papers using DeepSeek API"""
        combined_summaries = "\n\n".join(
            [p["title"] + "\n" + p["summary"] for p in papers]
        )
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的学术论文助手，请根据以下多篇论文的摘要，生成一份综合性的中文总结报告",
                },
                {"role": "user", "content": combined_summaries},
            ],
        )
        return response.choices[0].message.content

    def _generate_html(self, papers: List[Paper]) -> str:
        """Generate HTML content from recommended papers"""
        if papers:
            summary = markdown.markdown(self._generate_summary(papers))
        else:
            summary = ""
        html = render_email(papers, summary)

        return html

    async def _send_email(self, html: str) -> None:
        """Send HTML content via email"""

        msg = MIMEText(html, 'html', 'utf-8')
        msg['From'] = self.config.email_address
        msg['To'] = ",".join(self.config.receive_email_address)
        today = datetime.now().strftime('%Y/%m/%d')
        msg['Subject'] = Header(f'Daily arXiv {today}', 'utf-8').encode()

        try:
            server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
            server.starttls()
        except smtplib.SMTPServerDisconnected:
            server = smtplib.SMTP_SSL(self.config.smtp_server, self.config.smtp_port)

        server.login(self.config.email_address, self.config.email_password)
        server.sendmail(self.config.email_address, self.config.receive_email_address, msg.as_string())
        server.quit()

    async def store_recommendation(self, paper_id: int, relevance: float):
        """Store recommendation in database"""
        await self.db.paper.update(
            where={"id": paper_id}, data={"relevanceScore": relevance}
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
            if db_paper.relevanceScore != -1:
                if db_paper.relevanceScore > 0.5:
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
                paper["relevanceScore"] = relevance
                if relevance > 0.5:
                    recommended.append(paper)
                    self.logger.info(f"Recommended paper: {paper['title']}")
                await self.store_recommendation(paper_id, relevance)

            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error for paper {paper_id}: {e}")
            except Exception as e:
                self.logger.error(f"Error processing paper {paper_id}: {e}")

        # Generate and send markdown report
        html = self._generate_html(recommended)
        await self._send_email(html)

        return recommended
