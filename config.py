from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import os
import psycopg2.pool

# Загружаем переменные окружения
load_dotenv()

# Инициализируем aiogram
bot = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher(storage=MemoryStorage())

# Получаем DSN из .env
dsn = os.getenv('DSN')

# Создание пула соединений
try:
    connection_pool = psycopg2.pool.SimpleConnectionPool(
        1,  # минимальное количество соединений
        10, # максимальное количество соединений
        dsn=dsn
    )
    print("Connection pool created successfully")
except psycopg2.OperationalError as e:
    print(f"Failed to connect to database: {e}")
    raise