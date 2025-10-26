# handlers/admin_handlers.py
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from config import ADMIN_ID
from database import database as db
from keyboards.admin_keyboards import (
    admin_main_keyboard,
    task_type_keyboard,
    get_sections_keyboard_admin,
    confirm_keyboard,
    get_students_keyboard,  # Нужно будет добавить
    confirm_broadcast_keyboard  # Нужно будет добавить
)
from states.admin_states import AddTask, Broadcast  # Нужно будет добавить Broadcast

router = Router()

# Универсальный фильтр для всех обработчиков в этом роутере
router.message.filter(F.from_user.id == ADMIN_ID)
router.callback_query.filter(F.from_user.id == ADMIN_ID)

# --- Главное меню админа ---

@router.message(Command("admin"))
async def admin_panel(message: Message):
    await message.answer(
        "Добро пожаловать в панель администратора!",
        reply_markup=admin_main_keyboard
    )

# Обработчик для возврата в главное меню админа
@router.callback_query(F.data == "admin_main_menu")
async def back_to_admin_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "Добро пожаловать в панель администратора!",
        reply_markup=admin_main_keyboard
    )
    await callback.answer()

# --- Блок FSM для добавления задачи ---

@router.callback_query(F.data == "add_task")
async def start_add_task(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Шаг 1: Выберите тип новой задачи.", reply_markup=task_type_keyboard)
    await state.set_state(AddTask.waiting_for_type)
    await callback.answer()

@router.callback_query(AddTask.waiting_for_type)
async def process_task_type(callback: CallbackQuery, state: FSMContext):
    # Исправлено: корректно получаем 'multiple_choice' или 'text_input'
    task_type = '_'.join(callback.data.split('_')[1:])
    await state.update_data(type=task_type)

    sections = await db.get_sections()
    await callback.message.edit_text(
        "Шаг 2: Выберите раздел для задачи.",
        reply_markup=get_sections_keyboard_admin(sections)
    )
    await state.set_state(AddTask.waiting_for_section)
    await callback.answer()

@router.callback_query(AddTask.waiting_for_section)
async def process_task_section(callback: CallbackQuery, state: FSMContext):
    section_id = int(callback.data.split('_')[2])
    await state.update_data(section_id=section_id)

    await callback.message.edit_text("Шаг 3: Отправьте фотографию с условием задачи.")
    await state.set_state(AddTask.waiting_for_photo)
    await callback.answer()

@router.message(AddTask.waiting_for_photo, F.photo)
async def process_task_photo(message: Message, state: FSMContext):
    photo_file_id = message.photo[-1].file_id
    await state.update_data(photo=photo_file_id)

    user_data = await state.get_data()
    task_type = user_data.get('type')

    if task_type == 'multiple_choice':
        await message.answer("Шаг 4: Введите *правильный* вариант ответа.", parse_mode="Markdown")
        await state.set_state(AddTask.waiting_for_correct_choice)
    else: # text_input
        await message.answer("Шаг 4: Введите *правильный числовой* ответ.", parse_mode="Markdown")
        await state.set_state(AddTask.waiting_for_text_answer)

# -- Ветвь для 'multiple_choice' --
@router.message(AddTask.waiting_for_correct_choice)
async def process_correct_choice(message: Message, state: FSMContext):
    await state.update_data(correct_choice=message.text)
    await message.answer("Отлично. Теперь введите *первый неправильный* вариант ответа.")
    await state.set_state(AddTask.waiting_for_incorrect_choice_1)

@router.message(AddTask.waiting_for_incorrect_choice_1)
async def process_incorrect_choice_1(message: Message, state: FSMContext):
    await state.update_data(incorrect_choices=[message.text])
    await message.answer("Хорошо. Теперь *второй неправильный* вариант.")
    await state.set_state(AddTask.waiting_for_incorrect_choice_2)

@router.message(AddTask.waiting_for_incorrect_choice_2)
async def process_incorrect_choice_2(message: Message, state: FSMContext):
    user_data = await state.get_data()
    current_incorrect = user_data.get('incorrect_choices', [])
    current_incorrect.append(message.text)
    await state.update_data(incorrect_choices=current_incorrect)
    await message.answer("И *третий неправильный* вариант.")
    await state.set_state(AddTask.waiting_for_incorrect_choice_3)

@router.message(AddTask.waiting_for_incorrect_choice_3)
async def process_incorrect_choice_3(message: Message, state: FSMContext):
    user_data = await state.get_data()
    current_incorrect = user_data.get('incorrect_choices', [])
    current_incorrect.append(message.text)
    await state.update_data(incorrect_choices=current_incorrect)
    await message.answer("Шаг 5: Введите *текст подсказки* к задаче.")
    await state.set_state(AddTask.waiting_for_hint)

# -- Ветвь для 'text_input' --
@router.message(AddTask.waiting_for_text_answer)
async def process_text_answer_admin(message: Message, state: FSMContext):
    try:
        answer = float(message.text.replace(',', '.'))
        await state.update_data(text_answer=answer)
        await message.answer("Шаг 5: Введите *текст подсказки* к задаче.")
        await state.set_state(AddTask.waiting_for_hint)
    except ValueError:
        await message.answer("Ошибка. Ответ должен быть числом. Попробуйте еще раз.")

# -- Общее завершение FSM --
@router.message(AddTask.waiting_for_hint)
async def process_hint(message: Message, state: FSMContext):
    await state.update_data(hint=message.text)
    await message.answer("Шаг 6: Отправьте *решение* (текстом или одним фото).")
    await state.set_state(AddTask.waiting_for_solution)

@router.message(AddTask.waiting_for_solution, F.text)
async def process_solution_text(message: Message, state: FSMContext):
    await state.update_data(solution_data=message.text, solution_type='text')
    await show_confirmation(message, state)

@router.message(AddTask.waiting_for_solution, F.photo)
async def process_solution_photo(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(solution_data=file_id, solution_type='photo')
    await show_confirmation(message, state)

async def show_confirmation(message: Message, state: FSMContext):
    data = await state.get_data()

    # Формируем красивое превью
    preview_text = f"Подтвердите создание задачи:\n\n"
    preview_text += f"Тип: {data['type']}\n"
    preview_text += f"Раздел: {data['section_id']} (позже заменим на имя)\n\n"
    if data['type'] == 'multiple_choice':
        preview_text += f"✅ {data['correct_choice']}\n"
        for choice in data['incorrect_choices']:
            preview_text += f"❌ {choice}\n"
    else:
        preview_text += f"Ответ: {data['text_answer']}\n"

    preview_text += f"\nПодсказка: {data['hint']}\n"

    await message.answer_photo(
        photo=data['photo'],
        caption=preview_text,
        reply_markup=confirm_keyboard
    )
    await state.set_state(AddTask.confirming)

@router.callback_query(AddTask.confirming, F.data == "confirm_add_task")
async def confirm_task(callback: CallbackQuery, state: FSMContext):
    task_data = await state.get_data()
    # Печать для отладки
    print("--- ДАННЫЕ ДЛЯ СОХРАНЕНИЯ ---", task_data)

    await db.add_new_task(task_data)

    # Исправлено: используем edit_caption
    await callback.message.edit_caption(
        caption="✅ Задача успешно добавлена в базу данных!",
        reply_markup=None
    )
    await state.clear()
    await callback.answer()
    await admin_panel(callback.message) # Возвращаем в меню

@router.callback_query(AddTask.confirming, F.data == "cancel_add_task")
async def cancel_task(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete() # Удаляем превью
    await callback.answer("Создание задачи отменено.", show_alert=True)
    await admin_panel(callback.message) # Возвращаем в меню


# --- Блок просмотра статистики учеников (НОВЫЙ) ---

@router.callback_query(F.data.startswith("view_students"))
async def show_students_list(callback: CallbackQuery):
    page = int(callback.data.split('_')[-1]) if '_' in callback.data else 1
    students = await db.get_all_students(page)

    if not students:
        await callback.answer("Пока нет ни одного зарегистрированного ученика.", show_alert=True)
        return

    keyboard = get_students_keyboard(students, page)
    await callback.message.edit_text(
        "Выберите ученика для просмотра статистики:",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(F.data.startswith("student_"))
async def show_student_stats(callback: CallbackQuery):
    student_telegram_id = int(callback.data.split("_")[1])

    # Получаем общую статистику
    stats = await db.get_user_statistics(student_telegram_id)
    # Получаем последние ответы
    last_answers = await db.get_student_last_answers(student_telegram_id, 10)

    if not stats or stats['total'] == 0:
        report = "У этого ученика пока нет решенных задач."
    else:
        # Формируем отчет
        total = stats['total']
        correct = stats['correct']
        percentage = (correct / total * 100) if total > 0 else 0

        report = f"📊 *Статистика ученика (ID: {student_telegram_id})*\n\n"
        report += f"Всего решено: *{total}*\n"
        report += f"Правильно: *{correct}* ({percentage:.1f}%)\n\n"
        report += "📈 *По разделам:*\n"

        for section_name, sec_total, sec_correct in stats['sections']:
            sec_correct = sec_correct or 0
            sec_percentage = (sec_correct / sec_total * 100) if sec_total > 0 else 0
            report += f"  - {section_name}: решено *{sec_total}*, прав. *{sec_correct}* ({sec_percentage:.1f}%)\n"

        report += "\n📋 *Лог последних ответов:*\n"
        if not last_answers:
            report += "  (пока нет ответов)"
        else:
            for ans in last_answers:
                # task_id, given, is_correct, timestamp, action
                result = "✅" if ans[2] else "❌"
                if ans[4] == 'viewed_solution':
                    result = "🔍"
                elif ans[4] == 'hint_used':
                    result = "💡"

                report += f"  {ans[3][:16]} | {result} | Задача {ans[0]} | Ответ: {ans[1]}\n"

    # Клавиатура для возврата
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="view_students_1")],
        [InlineKeyboardButton(text="🏠 В админ-меню", callback_data="admin_main_menu")]
    ])

    await callback.message.edit_text(report, parse_mode="Markdown", reply_markup=back_kb)
    await callback.answer()

# --- Блок рассылки (НОВЫЙ) ---

@router.callback_query(F.data == "create_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Отправьте сообщение, которое нужно разослать всем ученикам. "
                                     "Можно использовать текст, фото, видео, документы.")
    await state.set_state(Broadcast.waiting_for_message)
    await callback.answer()

@router.message(Broadcast.waiting_for_message, F.content_type.in_({'text', 'photo', 'video', 'document'}))
async def get_broadcast_message(message: Message, state: FSMContext):
    await state.update_data(message_to_send=message)
    user_count = await db.get_all_user_ids()

    await message.answer(
        f"Вы уверены, что хотите отправить это сообщение {len(user_count)} ученикам?",
        reply_markup=confirm_broadcast_keyboard
    )
    await state.set_state(Broadcast.confirming)

@router.callback_query(Broadcast.confirming, F.data == "confirm_broadcast")
async def process_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    message_to_send = data.get('message_to_send')

    await state.clear()
    await callback.message.edit_text("Начинаю рассылку...")

    user_ids = await db.get_all_user_ids()
    sent_count = 0
    failed_count = 0

    for user_id_tuple in user_ids:
        user_id = user_id_tuple[0]
        try:
            # Используем copy_message для пересылки любого типа контента
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message_to_send.chat.id,
                message_id=message_to_send.message_id,
                reply_markup=message_to_send.reply_markup
            )
            sent_count += 1
            await asyncio.sleep(0.1) # Небольшая задержка во избежание флуда
        except (TelegramForbiddenError, TelegramBadRequest):
            # Пользователь заблокировал бота или неверный ID
            failed_count += 1
        except Exception as e:
            failed_count += 1
            print(f"Ошибка при рассылке пользователю {user_id}: {e}")

    await callback.message.answer(
        f"Рассылка завершена!\n\n✅ Отправлено: {sent_count}\n❌ Ошибок: {failed_count}",
        reply_markup=admin_main_keyboard
    )

@router.callback_query(Broadcast.confirming, F.data == "cancel_broadcast")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Рассылка отменена.", reply_markup=admin_main_keyboard)
    await callback.answer()