"""
Хендлеры для админ-панели
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.handlers.base import check_authorization
from src.services.auth_service import is_admin, get_user_clan_ids
from src.services.mentor_updater import update_all_mentors
from src.services.homework_updater import update_all_homeworks
from src.services.admin_service import create_admin
from src.keyboards.admin_menu import get_admin_menu
from src.keyboards.main_menu import get_main_menu

router = Router(name="admin")

# Блокировка для предотвращения одновременных обновлений
_update_lock = set()


class AdminCreationStates(StatesGroup):
    """Состояния для создания администратора"""
    waiting_for_first_name = State()
    waiting_for_last_name = State()
    waiting_for_telegram_tag = State()
    waiting_for_email = State()
    waiting_for_phone = State()
    waiting_for_confirmation = State()


async def check_admin_rights(message: Message) -> bool:
    """Проверяет, является ли пользователь администратором"""
    username = message.from_user.username
    
    if not is_admin(username):
        await message.answer(
            "❌ У вас нет прав администратора.\n"
            "Эта функция доступна только администраторам."
        )
        return False
    return True


@router.message(F.text == "🔧 Админ-панель")
async def show_admin_panel(message: Message):
    """Показывает админ-панель"""
    
    # Проверка авторизации
    if not await check_authorization(message):
        return
    
    # Проверка прав администратора
    if not await check_admin_rights(message):
        return
    
    await message.answer(
        "🔧 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_menu()
    )


@router.message(F.text == "◀️ Назад в главное меню")
async def back_to_main_menu(message: Message, state: FSMContext):
    """Возврат в главное меню"""
    
    # Очищаем состояние, если оно было активно
    await state.clear()
    
    username = message.from_user.username
    clan_ids = get_user_clan_ids(username)
    has_clans = len(clan_ids) > 0
    is_user_admin = is_admin(username)
    
    await message.answer(
        "Главное меню",
        reply_markup=get_main_menu(has_clans=has_clans, is_admin=is_user_admin)
    )


@router.message(F.text == "👤 Обновить базу наставников")
async def update_mentors(message: Message):
    """Обновляет всю базу наставников"""
    
    # Проверка авторизации
    if not await check_authorization(message):
        return
    
    # Проверка прав администратора
    if not await check_admin_rights(message):
        return
    
    user_id = message.from_user.id
    
    # Проверка блокировки
    if user_id in _update_lock:
        await message.answer(
            "⏳ Обновление уже выполняется.\n"
            "Пожалуйста, дождитесь завершения предыдущего обновления."
        )
        return
    
    # Добавляем блокировку
    _update_lock.add(user_id)
    
    try:
        # Отправляем индикатор "печатает"
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        # Информируем о начале обновления
        await message.answer(
            "🔄 Начинаю обновление базы наставников...\n\n"
            "⏳ Это может занять продолжительное время (несколько минут).\n"
            "Пожалуйста, ожидайте..."
        )
        
        # Выполняем обновление
        result = await update_all_mentors()
        
        # Отправляем результат
        if result["success"]:
            await message.answer(
                f"✅ Обновление базы наставников завершено успешно!\n\n"
                f"📊 Статистика:\n"
                f"• Всего наставников загружено: {result['total_mentors']}\n"
                f"• Наставников с Telegram и кланами: {result['filtered_mentors']}\n\n"
                f"База данных наставников обновлена."
            )
        else:
            await message.answer(
                f"❌ Ошибка при обновлении базы наставников:\n\n"
                f"{result.get('error', 'Неизвестная ошибка')}\n\n"
                f"Попробуйте повторить попытку позже или проверьте настройки API."
            )
    
    except Exception as e:
        await message.answer(
            f"❌ Произошла непредвиденная ошибка:\n\n"
            f"{str(e)}\n\n"
            f"Пожалуйста, попробуйте позже."
        )
    
    finally:
        # Снимаем блокировку
        _update_lock.discard(user_id)


@router.message(F.text == "📚 Обновить базу домашек")
async def update_all_homeworks_handler(message: Message):
    """Обновляет всю базу домашних заданий"""
    
    # Проверка авторизации
    if not await check_authorization(message):
        return
    
    # Проверка прав администратора
    if not await check_admin_rights(message):
        return
    
    user_id = message.from_user.id
    
    # Проверка блокировки
    if user_id in _update_lock:
        await message.answer(
            "⏳ Обновление уже выполняется.\n"
            "Пожалуйста, дождитесь завершения предыдущего обновления."
        )
        return
    
    # Добавляем блокировку
    _update_lock.add(user_id)
    
    try:
        # Отправляем индикатор "печатает"
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        # Информируем о начале обновления
        await message.answer(
            "🔄 Начинаю обновление базы домашних заданий...\n\n"
            "⏳ Это может занять очень продолжительное время (десятки минут).\n"
            "Обновление загружает ДЗ по всем кланам из базы наставников.\n\n"
            "Пожалуйста, ожидайте..."
        )
        
        # Выполняем обновление
        result = await update_all_homeworks()
        
        # Отправляем результат
        if result["success"]:
            await message.answer(
                f"✅ Обновление базы домашних заданий завершено успешно!\n\n"
                f"📊 Статистика:\n"
                f"• Обработано кланов: {result['total_clans']}\n"
                f"• Загружено домашек (ожидают проверки): {result['total_homeworks']}\n\n"
                f"База данных домашних заданий обновлена."
            )
        else:
            await message.answer(
                f"❌ Ошибка при обновлении базы домашек:\n\n"
                f"{result.get('error', 'Неизвестная ошибка')}\n\n"
                f"Попробуйте повторить попытку позже или проверьте настройки API."
            )
    
    except Exception as e:
        await message.answer(
            f"❌ Произошла непредвиденная ошибка:\n\n"
            f"{str(e)}\n\n"
            f"Пожалуйста, попробуйте позже."
        )
    
    finally:
        # Снимаем блокировку
        _update_lock.discard(user_id)


# ========== FSM для создания администратора ==========

@router.message(F.text == "➕ Создать администратора")
async def start_create_admin(message: Message, state: FSMContext):
    """Начинает процесс создания администратора"""
    
    # Проверка авторизации
    if not await check_authorization(message):
        return
    
    # Проверка прав администратора
    if not await check_admin_rights(message):
        return
    
    await state.set_state(AdminCreationStates.waiting_for_first_name)
    await message.answer(
        "👤 <b>Создание нового администратора</b>\n\n"
        "Введите <b>имя</b> нового администратора:\n\n"
        "Для отмены введите /cancel"
    )


@router.message(StateFilter(AdminCreationStates.waiting_for_first_name))
async def process_first_name(message: Message, state: FSMContext):
    """Обрабатывает ввод имени"""
    
    if message.text == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Создание администратора отменено.",
            reply_markup=get_admin_menu()
        )
        return
    
    await state.update_data(first_name=message.text.strip())
    await state.set_state(AdminCreationStates.waiting_for_last_name)
    
    await message.answer(
        "Введите <b>фамилию</b> нового администратора:\n\n"
        "Для отмены введите /cancel"
    )


@router.message(StateFilter(AdminCreationStates.waiting_for_last_name))
async def process_last_name(message: Message, state: FSMContext):
    """Обрабатывает ввод фамилии"""
    
    if message.text == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Создание администратора отменено.",
            reply_markup=get_admin_menu()
        )
        return
    
    await state.update_data(last_name=message.text.strip())
    await state.set_state(AdminCreationStates.waiting_for_telegram_tag)
    
    await message.answer(
        "Введите <b>Telegram username</b> (можно с @ или без):\n\n"
        "Пример: @username или username\n\n"
        "Для отмены введите /cancel"
    )


@router.message(StateFilter(AdminCreationStates.waiting_for_telegram_tag))
async def process_telegram_tag(message: Message, state: FSMContext):
    """Обрабатывает ввод telegram_tag"""
    
    if message.text == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Создание администратора отменено.",
            reply_markup=get_admin_menu()
        )
        return
    
    telegram_tag = message.text.strip().lstrip("@")
    
    if not telegram_tag:
        await message.answer(
            "❌ Telegram username не может быть пустым.\n"
            "Попробуйте еще раз:"
        )
        return
    
    await state.update_data(telegram_tag=telegram_tag)
    await state.set_state(AdminCreationStates.waiting_for_email)
    
    await message.answer(
        "Введите <b>email</b> (необязательно):\n\n"
        "Если не хотите указывать email, введите '-'\n\n"
        "Для отмены введите /cancel"
    )


@router.message(StateFilter(AdminCreationStates.waiting_for_email))
async def process_email(message: Message, state: FSMContext):
    """Обрабатывает ввод email"""
    
    if message.text == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Создание администратора отменено.",
            reply_markup=get_admin_menu()
        )
        return
    
    email = message.text.strip() if message.text.strip() != "-" else None
    
    await state.update_data(email=email)
    await state.set_state(AdminCreationStates.waiting_for_phone)
    
    await message.answer(
        "Введите <b>телефон</b> (необязательно):\n\n"
        "Если не хотите указывать телефон, введите '-'\n\n"
        "Для отмены введите /cancel"
    )


@router.message(StateFilter(AdminCreationStates.waiting_for_phone))
async def process_phone(message: Message, state: FSMContext):
    """Обрабатывает ввод телефона и создает администратора"""
    
    if message.text == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Создание администратора отменено.",
            reply_markup=get_admin_menu()
        )
        return
    
    phone = message.text.strip() if message.text.strip() != "-" else None
    
    # Получаем все собранные данные
    data = await state.get_data()
    
    admin_data = {
        "first_name": data["first_name"],
        "last_name": data["last_name"],
        "telegram_tag": data["telegram_tag"],
        "email": phone if phone else data.get("email"),
        "phone": phone
    }
    
    # Показываем данные для подтверждения
    confirmation_text = (
        "📋 <b>Подтвердите данные нового администратора:</b>\n\n"
        f"👤 Имя: {admin_data['first_name']}\n"
        f"👤 Фамилия: {admin_data['last_name']}\n"
        f"📱 Telegram: @{admin_data['telegram_tag']}\n"
        f"📧 Email: {admin_data.get('email') or 'не указан'}\n"
        f"📞 Телефон: {admin_data.get('phone') or 'не указан'}\n\n"
        "Все верно? Для подтверждения введите 'да', для отмены - 'нет'"
    )
    
    await state.update_data(admin_data=admin_data)
    await state.set_state(AdminCreationStates.waiting_for_confirmation)
    
    await message.answer(confirmation_text)


@router.message(StateFilter(AdminCreationStates.waiting_for_confirmation))
async def process_confirmation(message: Message, state: FSMContext):
    """Обрабатывает подтверждение создания администратора"""
    
    answer = message.text.strip().lower()
    
    if answer in ["нет", "no", "n", "отмена", "cancel"]:
        await state.clear()
        await message.answer(
            "❌ Создание администратора отменено.",
            reply_markup=get_admin_menu()
        )
        return
    
    if answer not in ["да", "yes", "y", "ок", "ok"]:
        await message.answer(
            "Пожалуйста, введите 'да' для подтверждения или 'нет' для отмены."
        )
        return
    
    # Получаем данные администратора
    data = await state.get_data()
    admin_data = data["admin_data"]
    
    # Создаем администратора
    result = create_admin(admin_data)
    
    # Очищаем состояние
    await state.clear()
    
    # Отправляем результат
    if result["success"]:
        admin = result["admin"]
        await message.answer(
            f"✅ <b>Администратор успешно создан!</b>\n\n"
            f"👤 {admin['full_name']}\n"
            f"📱 @{admin['telegram_tag']}\n"
            f"🆔 ID: {admin['id']}\n\n"
            f"Новый администратор добавлен в систему.",
            reply_markup=get_admin_menu()
        )
    else:
        await message.answer(
            f"❌ Ошибка при создании администратора:\n\n"
            f"{result.get('error', 'Неизвестная ошибка')}\n\n"
            f"Попробуйте еще раз.",
            reply_markup=get_admin_menu()
        )
