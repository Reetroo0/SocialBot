from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Инлайновая клавиатура главного меню (заменяет прежнюю ReplyKeyboard)
main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text='Опросы', callback_data='menu:opinions'),
        InlineKeyboardButton(text='Профиль', callback_data='menu:profile'),
    ],
    [
        InlineKeyboardButton(text='Непройденные опросы', callback_data='menu:uncompleted'),
    ]
])

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

