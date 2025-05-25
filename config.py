import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import psycopg2.pool

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,                                          
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]                              
)
logger = logging.getLogger(__name__)
logging.getLogger('aiogram.event').setLevel(logging.WARNING) 

load_dotenv()

bot = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher(storage=MemoryStorage())

dsn = os.getenv('DSN')

# Создание пула соединений
try:
    connection_pool = psycopg2.pool.SimpleConnectionPool(1, 10, dsn=dsn)
    logger.info("Connection pool created successfully")
except psycopg2.OperationalError as e:
    logger.error(f"Failed to connect to database: {e}")
    raise

# Список рангов и их пороговых значений
ranks = {
    0:   {"name": "Котёнок", "pack": "soc_bot_rank_cat"},
    50:  {"name": "Лисёнок", "pack": "soc_bot_rank_fox"},
    100: {"name": "Волк",    "pack": "soc_bot_rank_wolf"},
    150: {"name": "Тигр",    "pack": ""},
    200: {"name": "Дракон",  "pack": ""},
    250: {"name": "Феникс",  "pack": ""}
}