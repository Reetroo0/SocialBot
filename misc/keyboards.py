from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Клавиатура главного меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text='Опросы'),
            KeyboardButton(text='Профиль'),
        ],
        [
            KeyboardButton(text='Непройденные опросы'),
        ]
    ],
    resize_keyboard=True
)

# Клавиатура для выбора пола
gender_inl_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="💁‍♂️Мужской", callback_data="male"),
            InlineKeyboardButton(text="💁‍♀️Женский", callback_data="female")
        ]
    ]
)

# Клавиатура для подтверждения данных
confirm_inl_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Да", callback_data="cfm_yes"),
            InlineKeyboardButton(text="Нет", callback_data="cfm_no")
        ]
    ]
)

