import asyncio
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from .find import PaperFinder
from .recommend import DeepSeekPaperRecommender

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_daily():
    while True:
        try:
            logger.info("Starting daily paper search and recommendation")

            # Find new papers
            finder = PaperFinder()
            await finder.connect_db()
            try:
                await finder.find_recent_ai_papers()
            finally:
                await finder.disconnect_db()

            # Recommend papers
            recommender = DeepSeekPaperRecommender()
            await recommender.connect_db()
            try:
                recommended_papers = await recommender.recommend_papers()
                logger.info(f"Recommended {len(recommended_papers)} papers")
            finally:
                await recommender.disconnect_db()

            logger.info("Daily paper search and recommendation completed")
        except Exception as e:
            logger.error(f"Error during daily process: {str(e)}")

        # Calculate time until next day
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        next_run = datetime(tomorrow.year, tomorrow.month, tomorrow.day, hour=8)
        sleep_seconds = (next_run - now).total_seconds()

        logger.info(f"Sleeping for {sleep_seconds} seconds until next run")
        await asyncio.sleep(sleep_seconds)


def main():
    asyncio.run(run_daily())


if __name__ == "__main__":
    main()
