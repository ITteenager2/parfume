import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from config import TELEGRAM_TOKEN, OPENAI_API_KEY, DATABASE_URL, ADMIN_IDS
from database import init_db, add_user, get_user, update_user, get_all_users, save_support_request
from ai_helper import generate_recommendation
from data_analysis import analyze_user_data, analyze_order_history
from feedback import save_feedback, get_feedback_stats
from security import encrypt_data, decrypt_data
from google_sheets import update_google_sheets
from admin import handle_admin_command, send_broadcast, get_bot_statistics, get_support_requests_list

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class Form(StatesGroup):
    main_menu = State()
    age = State()
    gender = State()
    fragrances = State()
    location = State()
    awaiting_location = State()
    support = State()
    support_photo = State()
    admin_broadcast = State()

AGE_RANGES = ["18-24", "25-34", "35-44", "45-54", "55+"]
GENDERS = ["Мужской", "Женский", "Другой"]
FRAGRANCES = [
    ["Цветочные", "Древесные", "Цитрусовые", "Восточные", "Фужерные"],
    ["Шипровые", "Кожаные", "Гурманские", "Акватические", "Зеленые"],
    ["Пряные", "Фруктовые", "Альдегидные", "Мускусные", "Табачные"]
]
LOCATIONS = [
    ["Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань"],
    ["Нижний Новгород", "Челябинск", "Самара", "Омск", "Ростов-на-Дону"],
    ["Уфа", "Красноярск", "Воронеж", "Пермь", "Волгоград"]
]

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user = message.from_user
    encrypted_user_id = encrypt_data(str(user.id))
    add_user(encrypted_user_id, user.first_name, user.last_name)
    await message.reply(f'Привет, {user.first_name}! Я ваш персональный консультант по парфюмерии.')
    await show_main_menu(message)
    await state.set_state(Form.main_menu)

async def show_main_menu(message: types.Message):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="Подобрать парфюм", callback_data="select_perfume"))
    keyboard.add(InlineKeyboardButton(text="Поддержка", callback_data="support"))
    if str(message.from_user.id) in ADMIN_IDS:
        keyboard.add(InlineKeyboardButton(text="Админ панель", callback_data="admin_panel"))
    await message.answer("Выберите действие:", reply_markup=keyboard.as_markup())

@dp.callback_query(lambda c: c.data == "admin_panel")
async def process_admin_panel(callback_query: types.CallbackQuery):
    if str(callback_query.from_user.id) in ADMIN_IDS:
        await callback_query.answer()
        await handle_admin_command(callback_query.message)
    else:
        await callback_query.answer("У вас нет прав для доступа к админ панели.", show_alert=True)

@dp.callback_query(lambda c: c.data == "select_perfume")
async def process_select_perfume(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.answer("Отлично! Давайте подберем для вас идеальный парфюм. Для начала ответьте на несколько вопросов.")
    await ask_age(callback_query.message)
    await state.set_state(Form.age)

@dp.callback_query(lambda c: c.data == "support")
async def process_support(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.answer("Пожалуйста, напишите ваш вопрос или отзыв. Вы также можете прикрепить фото, если это необходимо.")
    await state.set_state(Form.support)

@dp.message(Form.support)
async def handle_support_message(message: types.Message, state: FSMContext):
    if message.text:
        encrypted_user_id = encrypt_data(str(message.from_user.id))
        save_support_request(encrypted_user_id, message.text)
        await message.reply("Спасибо за ваше сообщение! Мы обязательно рассмотрим его.")
        await notify_admins(f"Новое обращение в поддержку от пользователя {message.from_user.id}:\n\n{message.text}")
        await show_main_menu(message)
        await state.set_state(Form.main_menu)
    elif message.photo:
        await state.update_data(photo=message.photo[-1].file_id)
        await message.reply("Фото получено. Пожалуйста, добавьте описание к фото.")
        await state.set_state(Form.support_photo)
    else:
        await message.reply("Пожалуйста, отправьте текстовое сообщение или фото.")

@dp.message(Form.support_photo)
async def handle_support_photo_description(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    photo_id = user_data.get('photo')
    if message.text and photo_id:
        encrypted_user_id = encrypt_data(str(message.from_user.id))
        save_support_request(encrypted_user_id, message.text, photo_id)
        await message.reply("Спасибо за ваше сообщение и фото! Мы обязательно рассмотрим их.")
        await notify_admins(f"Новое обращение в поддержку с фото от пользователя {message.from_user.id}:\n\n{message.text}")
        await show_main_menu(message)
        await state.set_state(Form.main_menu)
    else:
        await message.reply("Произошла ошибка. Пожалуйста, попробуйте еще раз.")

async def ask_age(message: types.Message):
    keyboard = InlineKeyboardBuilder()
    for age in AGE_RANGES:
        keyboard.add(InlineKeyboardButton(text=age, callback_data=f"age_{age}"))
    keyboard.adjust(2)
    await message.answer('Выберите ваш возрастной диапазон:', reply_markup=keyboard.as_markup())

@dp.callback_query(lambda c: c.data and c.data.startswith('age_'))
async def process_age(callback_query: types.CallbackQuery, state: FSMContext):
    age = callback_query.data.split('_')[1]
    await state.update_data(age=age)
    encrypted_user_id = encrypt_data(str(callback_query.from_user.id))
    update_user(encrypted_user_id, 'age', encrypt_data(age))
    await callback_query.message.edit_text(f"Вы выбрали возраст: {age}")
    await ask_gender(callback_query.message)
    await state.set_state(Form.gender)

async def ask_gender(message: types.Message):
    keyboard = InlineKeyboardBuilder()
    for gender in GENDERS:
        keyboard.add(InlineKeyboardButton(text=gender, callback_data=f"gender_{gender}"))
    keyboard.adjust(2)
    await message.answer('Выберите ваш пол:', reply_markup=keyboard.as_markup())

@dp.callback_query(lambda c: c.data and c.data.startswith('gender_'))
async def process_gender(callback_query: types.CallbackQuery, state: FSMContext):
    gender = callback_query.data.split('_')[1]
    await state.update_data(gender=gender)
    encrypted_user_id = encrypt_data(str(callback_query.from_user.id))
    update_user(encrypted_user_id, 'gender', encrypt_data(gender))
    await callback_query.message.edit_text(f"Вы выбрали пол: {gender}")
    await ask_fragrances(callback_query.message, state)
    await state.set_state(Form.fragrances)

async def ask_fragrances(message: types.Message, state: FSMContext, page=0):
    keyboard = InlineKeyboardBuilder()
    for fragrance in FRAGRANCES[page]:
        keyboard.add(InlineKeyboardButton(text=fragrance, callback_data=f"fragrance_{fragrance}"))
    if page < len(FRAGRANCES) - 1:
        keyboard.add(InlineKeyboardButton(text="Следующая страница", callback_data=f"fragrance_next_{page+1}"))
    keyboard.adjust(2)
    await message.answer('Выберите предпочитаемые ароматы (можно выбрать несколько):', reply_markup=keyboard.as_markup())

@dp.callback_query(lambda c: c.data and c.data.startswith('fragrance_'))
async def process_fragrance(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data.split('_')
    if data[1] == 'next':
        page = int(data[2])
        await ask_fragrances(callback_query.message, state, page)
    else:
        fragrance = '_'.join(data[1:])
        user_data = await state.get_data()
        fragrances = user_data.get('fragrances', [])
        if fragrance not in fragrances:
            fragrances.append(fragrance)
        await state.update_data(fragrances=fragrances)
        encrypted_user_id = encrypt_data(str(callback_query.from_user.id))
        update_user(encrypted_user_id, 'preferred_fragrances', encrypt_data(str(fragrances)))
        if len(fragrances) < 3:
            await callback_query.message.edit_text(f"Вы выбрали: {fragrance}. Можете выбрать еще.")
            await ask_fragrances(callback_query.message, state)
        else:
            await callback_query.message.edit_text(f"Вы выбрали: {', '.join(fragrances)}")
            await ask_location(callback_query.message)
            await state.set_state(Form.location)

async def ask_location(message: types.Message, page=0):
    keyboard = InlineKeyboardBuilder()
    for location in LOCATIONS[page]:
        keyboard.add(InlineKeyboardButton(text=location, callback_data=f"location_{location}"))
    if page < len(LOCATIONS) - 1:
        keyboard.add(InlineKeyboardButton(text="Следующая страница", callback_data=f"location_next_{page+1}"))
    keyboard.add(InlineKeyboardButton(text="Другой город", callback_data="location_other"))
    keyboard.adjust(2)
    await message.answer('Выберите ваше местоположение:', reply_markup=keyboard.as_markup())

@dp.callback_query(lambda c: c.data and c.data.startswith('location_'))
async def process_location(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data.split('_')
    if data[1] == 'next':
        page = int(data[2])
        await ask_location(callback_query.message, page)
    elif data[1] == 'other':
        await callback_query.message.edit_text("Пожалуйста, введите название вашего города:")
        await state.set_state(Form.awaiting_location)
    else:
        location = '_'.join(data[1:])
        await state.update_data(location=location)
        encrypted_user_id = encrypt_data(str(callback_query.from_user.id))
        update_user(encrypted_user_id, 'location', encrypt_data(location))
        await callback_query.message.edit_text(f"Вы выбрали город: {location}")
        await finish_survey(callback_query.message, state)

@dp.message(Form.awaiting_location)
async def process_custom_location(message: types.Message, state: FSMContext):
    location = message.text
    await state.update_data(location=location)
    encrypted_user_id = encrypt_data(str(message.from_user.id))
    update_user(encrypted_user_id, 'location', encrypt_data(location))
    await message.reply(f"Вы ввели город: {location}")
    await finish_survey(message, state)

async def finish_survey(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    encrypted_user_id = encrypt_data(str(message.from_user.id))
    decrypted_user_data = {k: decrypt_data(v) if isinstance(v, str) else v for k, v in get_user(encrypted_user_id).items() if k != 'id'}
    recommendation = await generate_recommendation(decrypted_user_data)
    await message.answer(f'Спасибо за ответы! Вот моя рекомендация для вас:\n\n{recommendation}')
    await ask_feedback(message)

async def ask_feedback(message: types.Message):
    keyboard = InlineKeyboardBuilder()
    for i in range(1, 6):
        keyboard.add(InlineKeyboardButton(text=str(i), callback_data=f'feedback_{i}'))
    keyboard.adjust(5)
    await message.answer('Пожалуйста, оцените качество рекомендации от 1 до 5:', reply_markup=keyboard.as_markup())

@dp.callback_query(lambda c: c.data and c.data.startswith('feedback_'))
async def process_feedback(callback_query: types.CallbackQuery, state: FSMContext):
    feedback_score = int(callback_query.data.split('_')[1])
    encrypted_user_id = encrypt_data(str(callback_query.from_user.id))
    save_feedback(encrypted_user_id, feedback_score)
    await callback_query.message.edit_text(f"Спасибо за вашу оценку: {feedback_score}!")
    await show_main_menu(callback_query.message)
    await state.set_state(Form.main_menu)

@dp.message()
async def handle_message(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == Form.main_menu:
        await message.reply("Пожалуйста, выберите действие из меню.")
    else:
        encrypted_user_id = encrypt_data(str(message.from_user.id))
        user_data = get_user(encrypted_user_id)
        decrypted_user_data = {k: decrypt_data(v) if isinstance(v, str) else v for k, v in user_data.items() if k != 'id'}
        response = await generate_recommendation(decrypted_user_data, message.text)
        await message.reply(response)
        await ask_feedback(message)

async def send_recommendations():
    users = get_all_users()
    for user in users:
        decrypted_user_data = {k: decrypt_data(v) if isinstance(v, str) else v for k, v in user.items() if k != 'id'}
        recommendation = await generate_recommendation(decrypted_user_data)
        try:
            await bot.send_message(chat_id=int(decrypt_data(user['id'])), text=f"Новая рекомендация для вас:\n\n{recommendation}")
        except Exception as e:
            logging.error(f"Failed to send recommendation to user {user['id']}: {str(e)}")

async def update_analytics():
    feedback_stats = get_feedback_stats()
    update_google_sheets(feedback_stats)

async def scheduler():
    while True:
        await asyncio.gather(
            asyncio.sleep(86400),  # 24 hours
            send_recommendations()
        )
        await asyncio.gather(
            asyncio.sleep(3600),  # 1 hour
            update_analytics()
        )

async def notify_admins(message: str):
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=message)
        except Exception as e:
            logging.error(f"Failed to send notification to admin {admin_id}: {str(e)}")

@dp.message(Command("admin"))
async def admin_command(message: types.Message):
    if str(message.from_user.id) in ADMIN_IDS:
        await handle_admin_command(message)
    else:
        await message.reply("У вас нет прав для выполнения этой команды.")

@dp.callback_query(lambda c: c.data and c.data.startswith('admin_'))
async def process_admin_callback(callback_query: types.CallbackQuery, state: FSMContext):
    if str(callback_query.from_user.id) in ADMIN_IDS:
        action = callback_query.data.split('_')[1]
        if action == 'broadcast':
            await callback_query.message.edit_text("Введите сообщение для рассылки:")
            await state.set_state(Form.admin_broadcast)
        elif action == 'stats':
            stats = await get_bot_statistics()
            await callback_query.message.edit_text(stats)
        elif action == 'support':
            support_requests = await get_support_requests_list()
            await callback_query.message.edit_text(support_requests)
    else:
        await callback_query.answer("У вас нет прав для выполнения этой команды.", show_alert=True)

@dp.message(Form.admin_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext):
    if str(message.from_user.id) in ADMIN_IDS:
        success_count, total_users = await send_broadcast(bot, message.text)
        await message.reply(f"Рассылка выполнена успешно. Отправлено {success_count} из {total_users} пользователей.")
        await state.clear()
        await handle_admin_command(message)
    else:
        await message.reply("У вас нет прав для выполнения этой команды.")


@dp.message(Command("broadcast"))
async def start_broadcast(message: types.Message, state: FSMContext):
    if str(message.from_user.id) in ADMIN_IDS:
        await message.reply("Введите сообщение для рассылки:")
        await state.set_state(Form.admin_broadcast)
    else:
        await message.reply("У вас нет прав для выполнения этой команды.")

@dp.message(Command("stats"))
async def show_stats(message: types.Message):
    if str(message.from_user.id) in ADMIN_IDS:
        stats = await get_bot_statistics()
        await message.reply(f"Статистика бота:\n\n{stats}")
    else:
        await message.reply("У вас нет прав для выполнения этой команды.")

async def main():
    init_db()
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

