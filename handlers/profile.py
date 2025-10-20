from aiogram import Router, F
from aiogram.types import Message
from misc.keyboards import main_menu
from misc.pgSQL import get_profile_info
from misc.functions import CalculateRank, SendStikerByRank


router = Router()

@router.message(F.text == "Профиль") # , F.state.is_null()
async def start(message: Message):

    statistics = get_profile_info(message.from_user.id)

    if not statistics:
        await message.answer("Не удалось получить информацию о профиле.", reply_markup=main_menu)
        return
    # Считаем текущий ранг и прогресс до следующего ранга
    rank, next_rank = CalculateRank(statistics["surveys_count"])
    
    profile_message = (
        f"📊 Твой профиль:\n\n"
        f"📈 Ранг: {rank}\n"
        f"📝 Прошёл опросов: {statistics['surveys_count']}\n"
        f"📚 Число ответов: {statistics['answers_count']}\n"
    )
    await SendStikerByRank(message.from_user.id, 1)
    if next_rank > 0:
        profile_message += f"✳️ Опросов до следующего ранга: {next_rank}\n"
    else:
        profile_message += "🎉 Поздравляем! Ты достиг максимального ранга!\n"
    
    await message.answer(profile_message, reply_markup=main_menu)