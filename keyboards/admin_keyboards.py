# keyboards/admin_keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

admin_main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="👥 Мои ученики и их статистика", callback_data="view_students")],
    [InlineKeyboardButton(text="➕ Добавить задачу", callback_data="add_task")],
    [InlineKeyboardButton(text="📤 Создать рассылку", callback_data="create_broadcast")]
])

task_type_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="📝 Тест (выбор ответа)", callback_data="type_multiple_choice"),
        InlineKeyboardButton(text="🔢 Ввод числа", callback_data="type_text_input")
    ]
])

# Эта функция будет похожа на пользовательскую
def get_sections_keyboard_admin(sections):
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"admin_section_{section_id}")]
        for section_id, name in sections
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="✅ Подтвердить и сохранить", callback_data="confirm_add_task"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_add_task")
    ]
])