from aiogram import F
from aiogram import Router
from aiogram.types import Message, CallbackQuery
from misc.pgSQL import get_uncompleted_surveys, get_questions, get_current_question_id
import json
from misc.functions import GenerateKeyboard, SendNextQuestion, ParseQuestion, SaveAns_UpdateQuest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

router = Router()

# Определяем состояние FSM для возобновления опросов
class ResumeOpinionState(StatesGroup):
    opinion = State()

# Обработка коллбеков для смены страницы незавершенных опросов
@router.callback_query(F.data.startswith("res_opinion_page:"))
async def changePageResOpinion(callback_query: CallbackQuery):
    page = int(callback_query.data.split(":")[1])
    keyboard = GenerateKeyboard(page, "res_opinion", get_uncompleted_surveys(callback_query.from_user.id))
    await callback_query.message.edit_reply_markup(reply_markup=keyboard)

# Обработка команды "Непройденные опросы"
@router.message(F.text == "Непройденные опросы")
async def showUncompOpinions(message: Message):
    await message.delete()
    uncompSurveys = get_uncompleted_surveys(message.from_user.id)
    keyboard = GenerateKeyboard(0, "res_opinion", uncompSurveys)
    if len(uncompSurveys) == 0:
        await message.answer("У вас нет незавершенных опросов.")
        return
    await message.answer("Выберите опрос для продолжения:", reply_markup=keyboard)

# Обработка выбора незавершенного опроса
@router.callback_query(F.data.startswith("res_opinion:"))
async def handleSelectResumeOpinion(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.delete()
    
    opinion_id = int(callback_query.data.split(":")[1])
    questions = json.loads(get_questions(opinion_id))
    
    # Получаем текущий вопрос из базы данных
    current_question_id = get_current_question_id(callback_query.from_user.id, opinion_id)
    if current_question_id is None:
        print("Ошибка: текущий вопрос не найден в базе данных.")
        await callback_query.message.answer("Произошла ошибка, попробуйте снова.")
        return

    # Устанавливаем состояние FSM
    await state.set_state(ResumeOpinionState.opinion)
    await state.update_data(
        opinion_id=opinion_id,
        questions=questions,
        current_question_id=current_question_id,
        multi_choices=[],
        message_id=None
    )

    # Отправляем текущий вопрос с resume=True
    await SendNextQuestion(callback_query.from_user.id, state, resume=True)

# Обработка multiple_choice для возобновленного опроса
@router.callback_query(ResumeOpinionState.opinion, F.data.startswith("mans:"))
async def handleResumeMultipleChoice(callback_query: CallbackQuery, state: FSMContext):
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
        await SendNextQuestion(callback_query.from_user.id, state)  # resume=False по умолчанию

# Обработка single_choice и scale для возобновленного опроса
@router.callback_query(ResumeOpinionState.opinion, F.data.startswith("ans:"))
async def handleResumeSingleChoice(callback_query: CallbackQuery, state: FSMContext):
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
    
    # Отправляем следующий вопрос
    await SendNextQuestion(callback_query.from_user.id, state)  # resume=False по умолчанию

# Обработка текстовых ответов для возобновленного опроса
@router.message(ResumeOpinionState.opinion, F.text)
async def handleResumeTextAnswer(message: Message, state: FSMContext):
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
    
    # Отправляем следующий вопрос
    await SendNextQuestion(message.from_user.id, state)  # resume=False по умолчанию