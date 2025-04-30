import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import psycopg2.pool

logging.basicConfig(
    level=logging.INFO,  # Минимальный уровень логов
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат логов
    handlers=[
        logging.StreamHandler()  # Вывод в консоль
    ]
)

logger = logging.getLogger(__name__)

load_dotenv()

# Инициализируем aiogram
bot = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher(storage=MemoryStorage())

# Получаем DSN из .env
dsn = os.getenv('DSN')

# Создание пула соединений
try:
    connection_pool = psycopg2.pool.SimpleConnectionPool(1, 10, dsn=dsn)
    logger.info("Connection pool created successfully")
except psycopg2.OperationalError as e:
    logger.error(f"Failed to connect to database: {e}")
    raise