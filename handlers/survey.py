from aiogram import F
from aiogram import Router
from aiogram.types import Message, CallbackQuery
from misc.pgSQL import get_new_surveys, get_questions, set_survey_paused
import json
from misc.functions import GenerateKeyboard, SendNextQuestion, ParseQuestion, SaveAns_UpdateQuest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

router = Router()

# Определяем состояние FSM
class OpinionState(StatesGroup):
    opinion = State()



# Обработка коллбеков для смены страницы опросов
@router.callback_query(lambda c: c.data.startswith("opinion_page:"))
async def changePageOpinion(callback_query: CallbackQuery):
    page = int(callback_query.data.split(":")[1])
    keyboard = GenerateKeyboard(page, "opinion", get_new_surveys(callback_query.from_user.id))
    await callback_query.message.edit_reply_markup(reply_markup=keyboard)


# Обработка команды "Опросы"
@router.message(F.text == "Опросы")
async def showOpinions(message: Message):
    await message.delete()
    keyboard = GenerateKeyboard(0, "opinion", get_new_surveys(message.from_user.id))
    if not keyboard:
        await message.answer("Нет доступных опросов.")
        return
    await message.answer("Выберите опрос:", reply_markup=keyboard)


# Обработка выбора опроса
@router.callback_query(lambda c: c.data.startswith("opinion:"))
async def handleSelectOpinion(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.delete()
    
    opinion_id = int(callback_query.data.split(":")[1])
    questions = json.loads(get_questions(opinion_id))

    # Устанавливаем начальное состояние FSM
    await state.set_state(OpinionState.opinion)
    await state.update_data(
        opinion_id=opinion_id, 
        questions=questions, 
        current_question_id=None, 
        multi_choices=[], 
        message_id=None)

    # Отправляем первый вопрос
    await SendNextQuestion(callback_query.from_user.id, state)



# Обработка multiple_choice
@router.callback_query(OpinionState.opinion, lambda c: c.data.startswith("mans:"))
async def handleMultipleChoice(callback_query: CallbackQuery, state: FSMContext):
    _, answer, opinion_id, question_id = callback_query.data.split(":")
    data = await state.get_data()
    opinion_id = int(opinion_id)
    question_id = int(question_id)
    multi_choices = data.get("multi_choices", [])
    max_choices = data.get("max_choices", 1)
    
    if answer in multi_choices:
        multi_choices.remove(answer)
    elif len(multi_choices) < max_choices:
        multi_choices.append(answer)

    await state.update_data(multi_choices=multi_choices)
    
    # Обновляем клавиатуру
    current_question = next(q for q in data["questions"] if q["id"] == question_id)
    text, keyboard, _, _ = ParseQuestion(opinion_id, question_id, current_question["question"], selected=multi_choices)
    
    # Редактируем текущее сообщение
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    
    # Если достигнуто максимальное количество выборов, сохраняем и переходим дальше
    if len(multi_choices) == max_choices:
        SaveAns_UpdateQuest(
            callback_query.from_user.id,
            opinion_id,
            question_id,
            multi_choices,
            question_id
        )
        await state.update_data(multi_choices=[])
        # Переходим к следующему вопросу
        await SendNextQuestion(callback_query.from_user.id, state)

# Обработка single_choice и scale
@router.callback_query(OpinionState.opinion, lambda c: c.data.startswith("ans:"))
async def handleSingleChoice(callback_query: CallbackQuery, state: FSMContext):
    _, answer, opinion_id, question_id = callback_query.data.split(":")
    opinion_id = int(opinion_id)
    question_id = int(question_id)
    
    # Сохраняем ответ
    SaveAns_UpdateQuest(
        callback_query.from_user.id,
        opinion_id,
        question_id,
        answer,
        question_id
    )
    
    # НЕ удаляем сообщение, а отправляем следующий вопрос
    await SendNextQuestion(callback_query.from_user.id, state)

# Обработка текстовых ответов
@router.message(OpinionState.opinion, F.text)
async def handleTextAnswer(message: Message, state: FSMContext):
    data = await state.get_data()
    opinion_id = data.get("opinion_id")
    question_id = data.get("current_question_id")
    
    if not question_id or not opinion_id:
        await message.answer("Произошла ошибка, начните опрос заново")
        await state.clear()
        return
    
    # Сохраняем текстовый ответ
    SaveAns_UpdateQuest(
        message.from_user.id,
        opinion_id,
        question_id,
        message.text,
        question_id
    )
    
    # Удаляем сообщение с ответом пользователя
    await message.delete()
    
    # Отправляем следующий вопрос (или редактируем текущее)
    await SendNextQuestion(message.from_user.id, state)


@router.callback_query(lambda c: c.data.startswith("pause:"))
async def handlePause(callback_query: CallbackQuery, state: FSMContext):
    # Извлекаем opinion_id и question_id из callback_data
    _, opinion_id, question_id = callback_query.data.split(":")
    opinion_id = int(opinion_id)
    question_id = int(question_id)
    user_id = callback_query.from_user.id

    # Сохраняем текущее состояние в базе данных
    try:
        SaveAns_UpdateQuest(
            user_id,
            opinion_id,
            question_id,
            None,  # Ответ не сохраняем, так как это пауза
            question_id  # Указываем текущий question_id как следующий
        )
        
        # Устанавливаем is_completed_survey = false
        set_survey_paused(user_id, opinion_id)
    except Exception as e:
        print(f"Ошибка при сохранении состояния паузы (handlePause): \n{e}")

    # Удаляем сообщение с вопросом
    await callback_query.message.delete()
    await callback_query.answer("Опрос приостановлен. Вы можете продолжить позже.")
    # Очищаем состояние
    await state.clear()