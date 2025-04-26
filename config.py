from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import os
from urllib.parse import urlparse, parse_qs

load_dotenv()

bot = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher(storage=MemoryStorage())


base = None
cur = None

db_conf = os.getenv('DSN')
prs_db_conf = urlparse(db_conf.replace(' ', '&'))
db_config = {
    'host': prs_db_conf.hostname,
    'user': prs_db_conf.username,
    'password': prs_db_conf.password,
    'dbname': prs_db_conf.path.lstrip('/'),
    'port': prs_db_conf.port or 5432,
    'sslmode': parse_qs(prs_db_conf.query).get('sslmode', ['disable'])[0]
}
