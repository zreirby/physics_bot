# handlers/user_handlers.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from database import database as db
from keyboards.user_keyboards import (
    main_menu_keyboard,
    back_to_menu_keyboard,
    get_sections_keyboard,
    get_task_keyboard,
    next_task_keyboard
)
# Убедитесь, что в файле states/admin_states.py класс называется именно SolveTask
from states.admin_states import Registration, SolveTasks

router = Router()

# --- Блок регистрации и главного меню ---

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if user:
        await message.answer(f"С возвращением, {user[2]}!", reply_markup=main_menu_keyboard)
    else:
        await message.answer("Добро пожаловать в 'Физика-Ассистент'! 👋\n\n"
                             "Для начала, пожалуйста, введите ваше имя и фамилию.")
        await state.set_state(Registration.waiting_for_name)

@router.message(Registration.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    full_name = message.text
    await db.add_user(message.from_user.id, full_name)
    await message.answer(f"Отлично, {full_name}! Регистрация завершена. ✅\n\n"
                         "Теперь вы можете пользоваться ботом.", reply_markup=main_menu_keyboard)
    await state.clear()

@router.callback_query(F.data == "contact_tutor")
async def contact_tutor(callback: CallbackQuery):
    await callback.message.answer("Вы можете задать свой вопрос репетитору напрямую: @tutor_username")
    await callback.answer()

@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    await callback.message.edit_text(f"С возвращением, {user[2]}!", reply_markup=main_menu_keyboard)
    await callback.answer()

# --- Блок решения задач ---

async def send_new_task(callback: CallbackQuery, state: FSMContext, section_id: int):
    """Универсальная функция для отправки новой задачи."""
    task = await db.get_random_task_by_section(section_id)

    if not task:
        await callback.message.edit_text("В этом разделе пока нет задач. Выберите другой.")
        await callback.answer()
        return

    task_id, task_type, photo_file_id = task

    if task_type == 'multiple_choice':
        choices = await db.get_task_choices(task_id)
        keyboard = get_task_keyboard(task_type, task_id, choices)
        await callback.message.answer_photo(photo=photo_file_id, reply_markup=keyboard)

    elif task_type == 'text_input':
        keyboard = get_task_keyboard(task_type, task_id)
        await callback.message.answer_photo(
            photo=photo_file_id,
            caption="Введите ваш числовой ответ в сообщении.",
            reply_markup=keyboard
        )
        await state.set_state(SolveTasks.waiting_for_text_answer)
        await state.update_data(current_task_id=task_id)

    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data == "solve_tasks")
async def solve_tasks(callback: CallbackQuery):
    sections = await db.get_sections()
    if not sections:
        await callback.message.answer("Извините, пока нет доступных разделов с задачами.")
        await callback.answer()
        return

    keyboard = get_sections_keyboard(sections)
    await callback.message.edit_text("Выберите раздел физики:", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("section_"))
async def process_section_choice(callback: CallbackQuery, state: FSMContext):
    section_id = int(callback.data.split("_")[1])
    await state.update_data(current_section_id=section_id)
    await send_new_task(callback, state, section_id)

@router.callback_query(F.data == "next_task")
async def give_next_task(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    section_id = user_data.get('current_section_id')

    if section_id:
        await send_new_task(callback, state, section_id)
    else:
        await solve_tasks(callback)

# !!! ВОТ ЭТОТ БЛОК ПОЛНОСТЬЮ ОТСУТСТВОВАЛ !!!
@router.callback_query(F.data.startswith("choice_"))
async def process_choice_answer(callback: CallbackQuery):
    _, task_id, choice_id, is_correct_str = callback.data.split("_")
    task_id, choice_id = int(task_id), int(choice_id)
    is_correct = is_correct_str == '1'

    await db.log_user_action(callback.from_user.id, task_id, 'answered', answer_given=choice_id, is_correct=is_correct)

    if is_correct:
        original_keyboard = callback.message.reply_markup.inline_keyboard
        new_keyboard_rows = []
        for row in original_keyboard:
            new_row = []
            for button in row:
                if button.callback_data == callback.data:
                    new_row.append(InlineKeyboardButton(text=f"✅ {button.text}", callback_data="do_nothing"))
                else:
                    new_row.append(InlineKeyboardButton(text=button.text, callback_data="do_nothing"))
            new_keyboard_rows.append(new_row)

        await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=new_keyboard_rows))
        await callback.answer("Верно! ✅")
        await callback.message.answer("Отличная работа!", reply_markup=next_task_keyboard)
    else:
        original_keyboard = callback.message.reply_markup.inline_keyboard
        new_keyboard_rows = []
        for row in original_keyboard:
            new_row = []
            for button in row:
                if button.callback_data == callback.data:
                    new_row.append(InlineKeyboardButton(text=f"❌ {button.text}", callback_data="do_nothing"))
                else:
                    new_row.append(button)
            new_keyboard_rows.append(new_row)

        await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=new_keyboard_rows))
        await callback.answer("Неверно, попробуйте еще раз.", show_alert=True)

@router.message(SolveTasks.waiting_for_text_answer)
async def process_text_answer(message: Message, state: FSMContext):
    user_answer_str = message.text.strip().replace(',', '.')
    try:
        user_answer_float = float(user_answer_str)
    except ValueError:
        await message.answer("❌ Ответ должен быть числом. Попробуйте еще раз.")
        return

    user_data = await state.get_data()
    task_id = user_data.get('current_task_id')
    correct_answer_tuple = await db.get_task_text_answer(task_id)
    correct_answer = correct_answer_tuple[0]
    is_correct = abs(user_answer_float - correct_answer) <= abs(correct_answer * 0.005)

    await db.log_user_action(message.from_user.id, task_id, 'answered', answer_given=user_answer_str, is_correct=is_correct)

    if is_correct:
        await message.answer("Верно! ✅\n\nОтличная работа!", reply_markup=next_task_keyboard)
    else:
        await message.answer(f"Неверно. ❌\nПравильный ответ: {correct_answer}.\n\nНичего страшного, попробуем другую задачу!", reply_markup=next_task_keyboard)

    # Сбрасываем только состояние ожидания ответа, а не все данные
    await state.set_state(None)

# --- Блок подсказок и решений ---

@router.callback_query(F.data.startswith("hint_"))
async def process_hint_request(callback: CallbackQuery):
    task_id = int(callback.data.split("_")[1])
    hint_tuple = await db.get_task_hint(task_id)

    if hint_tuple and hint_tuple[0]:
        await db.log_user_action(callback.from_user.id, task_id, 'hint_used')
        await callback.answer(text=hint_tuple[0], show_alert=True)
    else:
        await callback.answer(text="К этой задаче нет подсказки.", show_alert=True)

@router.callback_query(F.data.startswith("solution_"))
async def process_solution_request(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    task_id = int(callback.data.split("_")[1])
    solution_tuple = await db.get_task_solution(task_id)

    if solution_tuple:
        await db.log_user_action(callback.from_user.id, task_id, 'viewed_solution', is_correct=False)
        solution_data, solution_type = solution_tuple

        if solution_type == 'text':
            await callback.message.answer(f"Решение:\n\n{solution_data}", reply_markup=next_task_keyboard)
        elif solution_type == 'photo':
            await callback.message.answer_photo(photo=solution_data, caption="Решение задачи:", reply_markup=next_task_keyboard)

        await callback.message.edit_reply_markup(reply_markup=None)
    else:
        await callback.message.answer("К этой задаче нет решения.", reply_markup=next_task_keyboard)

    await callback.answer()

# --- Блок статистики ---

@router.callback_query(F.data == "my_stats")
async def my_statistics(callback: CallbackQuery):
    stats = await db.get_user_statistics(callback.from_user.id)

    if not stats or stats['total'] == 0:
        await callback.message.edit_text("Вы еще не решили ни одной задачи. Самое время начать!", reply_markup=back_to_menu_keyboard)
        await callback.answer()
        return

    total = stats['total']
    correct = stats['correct']
    percentage = (correct / total * 100) if total > 0 else 0

    report = f"📊 *Ваша статистика*\n\n"
    report += f"Всего решено задач: *{total}*\n"
    report += f"Правильных ответов: *{correct}* ({percentage:.1f}%)\n\n"
    report += "📈 *По разделам:*\n"

    for section_name, sec_total, sec_correct in stats['sections']:
        sec_correct = sec_correct or 0
        sec_percentage = (sec_correct / sec_total * 100) if sec_total > 0 else 0
        report += f"  - {section_name}: решено *{sec_total}*, правильно *{sec_correct}* ({sec_percentage:.1f}%)\n"

    await callback.message.edit_text(report, parse_mode='Markdown', reply_markup=back_to_menu_keyboard)
    await callback.answer()