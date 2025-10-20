from aiogram.fsm.state import State, StatesGroup

# Состояния для регистрации
class Regist(StatesGroup):
    age = State()
    gender = State()
    confirm = State()


# Определяем состояние FSM
class OpinionState(StatesGroup):
    opinion = State()


# Определяем состояние FSM для возобновления опросов
class ResumeOpinionState(StatesGroup):
    opinion = State()