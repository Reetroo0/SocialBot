from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from misc.keyboards import main_menu, gender_inl_kb, confirm_inl_kb
from misc.pgSQL import add_user, check_user
from misc.functions import SendStikerByRank

router = Router()

# Состояния для регистрации
class Regist(StatesGroup):
    age = State()
    gender = State()
    confirm = State()



# Обработка команды /start
@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    if not check_user(message.from_user.id):
        await SendStikerByRank(message.from_user.id, 1)
        msg = await message.answer("Добро пожаловать! Для начала, пожалуйста, укажите ваш возраст (только число):")
        await state.update_data(msg_id=msg.message_id)  # Сохраняем message_id
        await state.set_state(Regist.age)

    else:
        await SendStikerByRank(message.from_user.id, 0)
        await message.answer("С возвращением!", reply_markup=main_menu)


# Обработка возраста
@router.message(Regist.age)
async def age(message: Message, state: FSMContext):
    
    user_data = await state.get_data()
    msg_id = user_data.get('msg_id')

    try:
        age = int(message.text)
        if 10 <= age <= 90:
            await message.delete()
            await state.update_data(age=age)

            await message.bot.edit_message_text(
                text="Теперь выберите ваш пол:", chat_id=message.chat.id,
                message_id=msg_id, reply_markup=gender_inl_kb)
            
            await state.set_state(Regist.gender)

        else:
            await message.bot.edit_message_text(
                text="Пожалуйста, введите корректный возраст (только число от 10 до 90):",
                chat_id=message.chat.id, message_id=msg_id, reply_markup=None)
            
    except ValueError:
        await message.bot.edit_message_text(
            text="Пожалуйста, введите корректный возраст (только число):",
            chat_id=message.chat.id, message_id=msg_id, reply_markup=None)
        


# Обработка выбора пола
@router.callback_query(Regist.gender)
async def gender(callback: CallbackQuery, state: FSMContext):
    age = (await state.get_data())['age']
    await state.update_data(gender=callback.data)

    await callback.message.edit_text(
        f"Пожалуйста, подтвердите данные:\nВозраст: {age}\nПол: {callback.data}", 
        reply_markup=confirm_inl_kb)
    
    await state.set_state(Regist.confirm)


# Обработка подтверждения
@router.callback_query(Regist.confirm)
async def confirm(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()

    if callback.data == "cfm_yes":
        add_user(callback.from_user.id, user_data['age'], user_data['gender'])
        
        await callback.message.delete()
        await callback.message.answer("Регистрация завершена!", reply_markup=main_menu)
        await state.clear()

    elif callback.data == "cfm_no":
        await callback.message.edit_text(
            "Пожалуйста, укажите ваш возраст (только число):", reply_markup=None)
        await state.set_state(Regist.age)