from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from misc.pgSQL import SaveAns_UpdateQuest
from config import bot
from aiogram.fsm.context import FSMContext

#ans:<ответ>:<opinion_id>:<question_id>
#ans:П р о г р а м м и р о в а н и е :5000:40
#################################################################
#         ^         ^         ^         ^         ^         ^

# Функция для парсинга вопроса
def ParseQuestion(opinion_id, question_id, question, selected=None):
    try:
        question_type = question["type"]
        text = question["question"]
        row = []

        # Инициализируем клавиатуру
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])

        if question_type == "text":
            # Для текстовых вопросов добавляем только кнопку паузы
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text="⏸ Пауза", callback_data=f"pause:{opinion_id}:{question_id}")
            ])
            return text, keyboard, None, None

        elif question_type == "single_choice":
            options = question.get("options", [])
            for option in options:
                button = InlineKeyboardButton(text=option, callback_data=f"ans:{option}:{opinion_id}:{question_id}")
                row.append(button)
                if len(row) == 2:
                    keyboard.inline_keyboard.append(row)
                    row = []
            if row:
                keyboard.inline_keyboard.append(row)

        elif question_type == "multiple_choice":
            options = question.get("options", [])
            max_choices = question.get("max_choices")
            if selected is None:
                selected = []
            for option in options:
                button_text = f"✅ {option}" if option in selected else option
                button = InlineKeyboardButton(text=button_text, callback_data=f"mans:{option}:{opinion_id}:{question_id}")
                row.append(button)
                if len(row) == 2:
                    keyboard.inline_keyboard.append(row)
                    row = []
            if row:
                keyboard.inline_keyboard.append(row)

        elif question_type == "scale":
            keyboard.inline_keyboard.extend([
                [
                    InlineKeyboardButton(
                        text=f"⭐️{i}", callback_data=f"ans:{i}:{opinion_id}:{question_id}"
                    ) for i in range(1, 6)
                ],
                [
                    InlineKeyboardButton(
                        text=f"⭐️{i}", callback_data=f"ans:{i}:{opinion_id}:{question_id}"
                    ) for i in range(6, 11)
                ]
            ])

        else:
            return "", None, None, f"Unknown question type: {question_type}"

        # Добавляем кнопку паузы для всех типов вопросов, кроме текстовых
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="⏸ Пауза", callback_data=f"pause:{opinion_id}:{question_id}")
        ])

        return text, keyboard, max_choices if question_type == "multiple_choice" else None, None

    except KeyError as e:
        return "", None, None, f"Missing required field: {e}"
    
# Функция для генерации клавиатуры с опросами
def GenerateKeyboard(page, callback_prefix, items):
    # Рассчитываем количество страниц (по 5 опросов на страницу)
    total_pages = (len(items) + 5 - 1) // 5
    # Вычисляем индексы элементов на текущей странице
    current_items = items[page * 5:(page * 5) + 5]
    # Создаем клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    # Добавляем кнопки с опросами
    for theme, id_opinion in current_items:
        # Обрезаем название до 16 символов для кнопки
        #display_name = theme[:20] + "..." if len(theme) > 12 else theme
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=f"{theme}",callback_data=f"{callback_prefix}:{id_opinion}")])

    # Кнопки навигации
    nav_buttons = [
        InlineKeyboardButton(text="⬅️", callback_data=f"{callback_prefix}_page:{page-1}") if page > 0 else None,
        InlineKeyboardButton(text=f"{page+1} / {total_pages}", callback_data="ignore"),
        InlineKeyboardButton(text="➡️", callback_data=f"{callback_prefix}_page:{page+1}") if page < total_pages - 1 else None
    ]
    # Фильтруем None и добавляем кнопки
    nav_buttons = [btn for btn in nav_buttons if btn is not None]

    if nav_buttons:
        keyboard.inline_keyboard.append(nav_buttons)

    return keyboard


# Функция для отправки следующего вопроса
async def SendNextQuestion(user_id: int, state: FSMContext):
    data = await state.get_data()
    current_question_id = data.get("current_question_id")
    questions = data.get("questions", [])
    opinion_id = data.get("opinion_id", 0)
    prev_message_id = data.get("message_id")

    # Находим следующий вопрос
    next_question = get_next_question(current_question_id, questions)
    if not next_question:
        await complete_survey(user_id, opinion_id, current_question_id, prev_message_id, state)
        return

    # Парсим вопрос
    question_id = next_question["id"]
    question_text = next_question["question"]
    text, keyboard, max_choices, err = ParseQuestion(opinion_id, question_id, question_text)
    if err:
        print(f"Ошибка парсинга вопроса: \n{err}")
        await state.update_data(current_question_id=question_id)
        await SendNextQuestion(user_id, state)
        return

    # Обновляем состояние и базу данных
    await state.update_data(current_question_id=question_id, max_choices=max_choices)
    SaveAns_UpdateQuest(user_id, opinion_id, question_id, None, question_id)

    # Отправляем или редактируем сообщение
    new_message_id = await send_or_edit_message(user_id, text, keyboard, prev_message_id)
    if not new_message_id:
        await bot.send_message(user_id, "Произошла ошибка при загрузке вопроса. Переходим к следующему.")
        await state.update_data(current_question_id=question_id)
        await SendNextQuestion(user_id, state)
        return

    # Сохраняем ID нового сообщения
    await state.update_data(message_id=new_message_id)


'''
Вспомогательные функции для функции SendNextQuestion
'''
# Получение следующего вопроса
def get_next_question(current_question_id: int, questions: list) -> dict | None:
    if not questions:
        return None
    if not current_question_id:  # Первый вопрос
        return questions[0]
    for i, q in enumerate(questions):
        if q["id"] == current_question_id and i + 1 < len(questions):
            return questions[i + 1]
    return None

# Завершение опроса
async def complete_survey(user_id: int, opinion_id: int, current_question_id: int, prev_message_id: int | None, state: FSMContext):
    SaveAns_UpdateQuest(user_id, opinion_id, current_question_id, None, None)
    completion_text = "🎉 Вы успешно прошли опрос! Спасибо за участие!"
    
    try:
        if prev_message_id:
            await bot.edit_message_text(
                text=completion_text,
                chat_id=user_id,
                message_id=prev_message_id,
                reply_markup=None
            )
        else:
            await bot.send_message(user_id, completion_text)
    except Exception as e:
        print(f"Ошибка при завершении опроса: \n{e}")
        await bot.send_message(user_id, completion_text)
    
    await state.clear()

# Отправка или редактирование сообщения с вопросом
async def send_or_edit_message(user_id: int, text: str, keyboard: InlineKeyboardMarkup | None, prev_message_id: int | None) -> int | None:
    try:
        if prev_message_id:
            await bot.edit_message_text(
                text=text,
                chat_id=user_id,
                message_id=prev_message_id,
                reply_markup=keyboard
            )
            return prev_message_id
        message = await bot.send_message(user_id, text, reply_markup=keyboard)
        return message.message_id
    except Exception as e:
        print(f"Ошибка при отправке/редактировании сообщения: \n{e}")
        return None


