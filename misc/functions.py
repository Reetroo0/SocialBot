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

        if question_type == "text":
            return text, None, None, None

        elif question_type == "single_choice":
            options = question.get("options", [])
            keyboard = InlineKeyboardMarkup(inline_keyboard=[])
            for option in options:
                button = InlineKeyboardButton(text=option, callback_data=f"ans:{option}:{opinion_id}:{question_id}")
                row.append(button)
                if len(row) == 2:
                    keyboard.inline_keyboard.append(row)
                    row = []
            if row:  
                keyboard.inline_keyboard.append(row)
            return text, keyboard, None, None

        elif question_type == "multiple_choice":
            options = question.get("options", [])
            max_choices = question.get("max_choices")
            keyboard = InlineKeyboardMarkup(inline_keyboard=[])
            
            # Если selected не передан, инициализируем пустым списком
            if selected is None:
                selected = []
                
            for option in options:
                # Добавляем маркер к выбранным опциям
                button_text = f"✅ {option}" if option in selected else option
                button = InlineKeyboardButton(text=button_text, callback_data=f"mans:{option}:{opinion_id}:{question_id}")
                row.append(button)
                if len(row) == 2:
                    keyboard.inline_keyboard.append(row)
                    row = []
            if row:
                keyboard.inline_keyboard.append(row)
            return text, keyboard, max_choices, None

        elif question_type == "scale":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
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
            return text, keyboard, None, None

        else:
            return "", None, None, f"Unknown question type: {question_type}"

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
    prev_message_id = data.get("message_id")  # Получаем ID предыдущего сообщения, если есть
    
    # Находим следующий вопрос
    next_question = None
    if not current_question_id:  # Первый вопрос
        next_question = questions[0] if questions else None
    else:
        # Ищем следующий вопрос после текущего
        for i, q in enumerate(questions):
            if q["id"] == current_question_id:
                if i + 1 < len(questions):
                    next_question = questions[i + 1]
                break
    
    # Если нет следующего вопроса
    if not next_question:
        # Отмечаем опрос как завершенный
        SaveAns_UpdateQuest(user_id, opinion_id, current_question_id, None, None)
        # Текст завершения опроса
        completion_text = "🎉 Вы успешно прошли опрос! Спасибо за участие!"
        
        try:
            if prev_message_id:
                # Пытаемся отредактировать последнее сообщение
                await bot.edit_message_text(
                    text=completion_text,
                    chat_id=user_id,
                    message_id=prev_message_id,
                    reply_markup=None  # Удаляем клавиатуру
                )
            else:
                # Если нет message_id, отправляем новое сообщение
                await bot.send_message(user_id, completion_text)
        except Exception as e:
            print(f"Ошибка при редактировании/отправке сообщения о завершении (SendNextQuestion 148): \n{e}")
            # В случае ошибки отправляем новое сообщение
            await bot.send_message(user_id, completion_text)
        
        # Очищаем состояние
        await state.clear()
        return

    question_id = next_question["id"]
    question_text = next_question["question"]

    # Парсим вопрос
    text, keyboard, max_choices, err = ParseQuestion(opinion_id, question_id, question_text)
    if err:
        await bot.send_message(user_id, "Ошибка парсинга вопроса")
        print("Ошибка парсинга вопроса")
        # Переходим к следующему вопросу
        await state.update_data(current_question_id=question_id)
        await SendNextQuestion(user_id, state)
        return

    # Обновляем состояние и CurrentUserQuestion
    await state.update_data(current_question_id=question_id, max_choices=max_choices)
    SaveAns_UpdateQuest(user_id, opinion_id, question_id, None, question_id)

    # Отправляем или редактируем вопрос
    try:
        if prev_message_id:
            # Пытаемся отредактировать предыдущее сообщение
            try:
                await bot.edit_message_text(text=text, chat_id=user_id, message_id=prev_message_id, reply_markup=keyboard)
                return  # Сообщение отредактировано, выходим
            except Exception as e:
                print(f"Ошибка редактирования сообщения: {e}")
                # Если редактирование не удалось, отправляем новое сообщение

        # Отправляем новое сообщение
        message = await bot.send_message(user_id, text, reply_markup=keyboard)
        # Сохраняем ID нового сообщения в состоянии
        await state.update_data(message_id=message.message_id)
    except Exception as e:
        print(f"Ошибка при отправке вопроса (SendNextQuestion 189): \n{e}")
        await bot.send_message(user_id, "Произошла ошибка при загрузке вопроса. Переходим к следующему.")
        await state.update_data(current_question_id=question_id)
        await SendNextQuestion(user_id, state)

