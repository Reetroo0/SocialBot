from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton
from misc.keyboards import main_menu
from misc.pgSQL import get_new_surveys, get_uncompleted_surveys, get_profile_info
from misc.functions import GenerateKeyboard, CalculateRank, SendStikerByRank

router = Router()

# Обработчики главного меню (inline-кнопки)
@router.callback_query(F.data == "menu:opinions")
async def menu_opinions(callback: CallbackQuery):
    # Редактируем текущее сообщение: показываем список опросов и кнопку Назад
    keyboard = GenerateKeyboard(0, "opinion", get_new_surveys(callback.from_user.id))
    # Добавим кнопку Назад внизу
    if keyboard is None:
        # Пустой список — отредактируем сообщение с информацией
        back_kb = InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:back")
        try:
            await callback.message.edit_text("Нет доступных опросов.", reply_markup=InlineKeyboardButton.inline_keyboard if False else None)
        except Exception:
            # fallback — отправить отдельное сообщение
            await callback.message.answer("Нет доступных опросов.")
        return

    # append back button row
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:back")])
    try:
        await callback.message.edit_text("Выберите опрос:", reply_markup=keyboard)
    except Exception:
        # Если не получится редактировать (например, удалено), отправим новое сообщение
        await callback.message.answer("Выберите опрос:", reply_markup=keyboard)


@router.callback_query(F.data == "menu:uncompleted")
async def menu_uncompleted(callback: CallbackQuery):
    uncomp = get_uncompleted_surveys(callback.from_user.id)
    keyboard = GenerateKeyboard(0, "res_opinion", uncomp)
    if not uncomp:
        # редактируем сообщение с текстом и кнопкой назад
        try:
            await callback.message.edit_text("У вас нет незавершенных опросов.", reply_markup=InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:back"))
        except Exception:
            await callback.message.answer("У вас нет незавершенных опросов.")
        return

    keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:back")])
    try:
        await callback.message.edit_text("Выберите опрос для продолжения:", reply_markup=keyboard)
    except Exception:
        await callback.message.answer("Выберите опрос для продолжения:", reply_markup=keyboard)


@router.callback_query(F.data == "menu:profile")
async def menu_profile(callback: CallbackQuery):
    # Редактируем текущее сообщение: показываем профиль и кнопку Назад
    statistics = get_profile_info(callback.from_user.id)
    if not statistics:
        try:
            await callback.message.edit_text("Не удалось получить информацию о профиле.", reply_markup=InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:back"))
        except Exception:
            await callback.message.answer("Не удалось получить информацию о профиле.")
        return

    rank, next_rank = CalculateRank(statistics["surveys_count"])
    profile_message = (
        f"📊 Твой профиль:\n\n"
        f"📈 Ранг: {rank}\n"
        f"📝 Прошёл опросов: {statistics['surveys_count']}\n"
        f"📚 Число ответов: {statistics['answers_count']}\n"
    )
    if next_rank > 0:
        profile_message += f"✳️ Опросов до следующего ранга: {next_rank}\n"
    else:
        profile_message += "🎉 Поздравляем! Ты достиг максимального ранга!\n"

    # Кнопка назад
    kb = InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:back")
    try:
        await SendStikerByRank(callback.from_user.id, 1)
    except Exception:
        pass
    try:
        await callback.message.edit_text(profile_message, reply_markup=InlineKeyboardButton.inline_keyboard if False else None)
        # build proper keyboard to include back button
        from aiogram.types import InlineKeyboardMarkup
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:back")]])
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except Exception:
        # fallback: send new message
        from aiogram.types import InlineKeyboardMarkup
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:back")]])
        await callback.message.answer(profile_message, reply_markup=keyboard)


@router.callback_query(F.data == "menu:back")
async def menu_back(callback: CallbackQuery):
    # Редактируем сообщение обратно в главное меню
    try:
        await callback.message.edit_text("Главное меню:", reply_markup=main_menu)
    except Exception:
        # fallback: отправим основное меню отдельно
        await callback.message.answer("Главное меню:", reply_markup=main_menu)
