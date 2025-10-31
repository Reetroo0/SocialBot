from aiogram import run_polling
from config import bot, dp, logger
from misc.pgSQL import pgConnect
from misc.keyboards import main_menu
from handlers import start, survey, UnCompSurvey, profile, menu

# Подключаем роутеры
dp.include_routers(
    start.router,
    survey.router,
    UnCompSurvey.router,
    profile.router,
    menu.router
)

async def on_startup():
    pgConnect()
    await bot.send_message(618425933, 'Бот запущен', reply_markup=main_menu)
    logger.info("Бот запущен с workers!")

async def on_shutdown():
    await bot.send_message(618425933, 'Бот остановлен')
    await bot.session.close()
    logger.info("Бот остановлен — ресурсы освобождены")


if __name__ == '__main__':
    run_polling(
        bot,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        workers=4,
        polling_timeout=10,
        allowed_updates=dp.resolve_used_update_types()
    )