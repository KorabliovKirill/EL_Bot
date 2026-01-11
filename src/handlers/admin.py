"""
Хендлеры для админ-панели
"""
import asyncio
import logging
from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.handlers.base import check_authorization
from src.services.auth_service import is_admin, get_user_clan_ids, get_mentors
from src.services.admin_service import create_admin
from src.keyboards.admin_menu import get_admin_menu
from src.keyboards.main_menu import get_main_menu
from src.config.settings import BASE_DIR
from src.core.maintenance import maintenance_manager

router = Router(name="admin")
logger = logging.getLogger(__name__)

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


async def notify_all_users(bot, message: str):
    """
    Отправляет уведомление всем пользователям бота
    
    Args:
        bot: экземпляр бота
        message: текст уведомления
    """
    mentors = get_mentors()
    
    sent_count = 0
    failed_count = 0
    
    for mentor in mentors:
        telegram_id = mentor.get("telegram_id")
        if not telegram_id:
            continue
        
        try:
            await bot.send_message(telegram_id, message)
            sent_count += 1
            # Небольшая задержка, чтобы не превысить лимиты Telegram
            await asyncio.sleep(0.05)
        except Exception as e:
            failed_count += 1
            logger.error(f"Не удалось отправить уведомление {telegram_id}: {e}")
    
    logger.info(
        f"Уведомления отправлены: успешно={sent_count}, ошибок={failed_count}"
    )
    
    return sent_count, failed_count


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


async def run_script_async(
    script_name: str, 
    chat_id: int, 
    bot,
    operation_type: str,
    estimated_minutes: int
):
    """
    Запускает скрипт асинхронно с блокировкой бота
    
    Args:
        script_name: имя скрипта для запуска
        chat_id: ID чата для уведомлений
        bot: экземпляр бота
        operation_type: тип операции ("homeworks" или "mentors")
        estimated_minutes: примерная длительность в минутах
    """
    script_path = BASE_DIR / "scripts" / script_name
    
    logger.info(f"Запуск скрипта: {script_path}")
    
    try:
        # Включаем режим обслуживания
        maintenance_started = await maintenance_manager.start_maintenance(
            operation=operation_type,
            estimated_duration=estimated_minutes
        )
        
        if not maintenance_started:
            await bot.send_message(
                chat_id,
                "⚠️ Не удалось включить режим обслуживания. "
                "Возможно, другое обновление уже выполняется."
            )
            return
        
        # Получаем сообщение для пользователей
        maintenance_msg = await maintenance_manager.get_maintenance_message()
        
        # Отправляем уведомление всем пользователям
        sent, failed = await notify_all_users(bot, maintenance_msg)
        
        await bot.send_message(
            chat_id,
            f"📢 Уведомления отправлены:\n"
            f"✅ Успешно: {sent}\n"
            f"❌ Ошибок: {failed}\n\n"
            f"🔧 Режим обслуживания активирован\n"
            f"Запуск скрипта..."
        )
        
        # Запускаем скрипт
        process = await asyncio.create_subprocess_exec(
            "python3",
            str(script_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(BASE_DIR)
        )
        
        # Ожидаем завершения
        stdout, stderr = await process.communicate()
        
        # Декодируем вывод
        stdout_text = stdout.decode('utf-8') if stdout else ""
        stderr_text = stderr.decode('utf-8') if stderr else ""
        
        # Логируем результаты
        logger.info(f"Скрипт {script_name} завершен с кодом: {process.returncode}")
        if stdout_text:
            logger.info(f"STDOUT:\n{stdout_text}")
        if stderr_text:
            logger.error(f"STDERR:\n{stderr_text}")
        
        # Отключаем режим обслуживания
        await maintenance_manager.stop_maintenance()
        
        # Отправляем уведомление пользователю
        if process.returncode == 0:
            # Извлекаем полезную информацию из вывода
            lines = stdout_text.strip().split('\n')
            summary_lines = [
                line for line in lines 
                if any(keyword in line.lower() for keyword in 
                       ['готово', 'всего', 'уникальных', 'заданий', 'файл'])
            ]
            summary = '\n'.join(summary_lines[-5:]) if summary_lines else "Обновление завершено успешно"
            
            await bot.send_message(
                chat_id,
                f"✅ <b>Скрипт выполнен успешно!</b>\n\n"
                f"📄 <code>{script_name}</code>\n\n"
                f"📊 Результат:\n{summary}\n\n"
                f"🟢 Бот снова доступен для пользователей"
            )
            
            # Уведомляем всех пользователей о завершении
            completion_msg = (
                "✅ <b>Обновление завершено</b>\n\n"
                "Бот снова доступен для работы.\n"
                "Все данные обновлены."
            )
            await notify_all_users(bot, completion_msg)
        else:
            error_msg = stderr_text[-500:] if stderr_text else "Неизвестная ошибка"
            await bot.send_message(
                chat_id,
                f"❌ <b>Ошибка выполнения скрипта</b>\n\n"
                f"📄 <code>{script_name}</code>\n"
                f"Код возврата: {process.returncode}\n\n"
                f"Ошибка:\n<code>{error_msg}</code>\n\n"
                f"🟢 Режим обслуживания отключен"
            )
    
    except Exception as e:
        logger.error(f"Ошибка при запуске скрипта {script_name}: {e}", exc_info=True)
        
        # В случае ошибки обязательно отключаем режим обслуживания
        await maintenance_manager.stop_maintenance()
        
        await bot.send_message(
            chat_id,
            f"❌ <b>Критическая ошибка</b>\n\n"
            f"Не удалось запустить скрипт <code>{script_name}</code>\n\n"
            f"Ошибка: {str(e)}\n\n"
            f"🟢 Режим обслуживания отключен"
        )
    
    finally:
        # Снимаем блокировку
        _update_lock.discard(chat_id)


@router.message(F.text == "👤 Обновить базу наставников")
async def update_mentors(message: Message):
    """Обновляет всю базу наставников"""
    
    # Проверка авторизации
    if not await check_authorization(message):
        return
    
    # Проверка прав администратора
    if not await check_admin_rights(message):
        return
    
    chat_id = message.chat.id
    
    # Проверка блокировки
    if chat_id in _update_lock:
        await message.answer(
            "⏳ Обновление уже выполняется.\n"
            "Пожалуйста, дождитесь завершения предыдущего обновления."
        )
        return
    
    # Проверяем, не активен ли уже режим обслуживания
    if await maintenance_manager.is_maintenance_active():
        await message.answer(
            "⚠️ Бот уже находится в режиме обслуживания.\n"
            "Дождитесь завершения текущего обновления."
        )
        return
    
    # Добавляем блокировку
    _update_lock.add(chat_id)
    
    # Информируем о начале обновления
    await message.answer(
        "🔄 <b>Запуск обновления базы наставников...</b>\n\n"
        "⏳ Процесс запущен в фоновом режиме.\n"
        "⚠️ <b>БОТ БУДЕТ ЗАБЛОКИРОВАН на время обновления</b>\n\n"
        "Примерное время: ~5-10 минут\n"
        "Все пользователи получат уведомление."
    )
    
    # Запускаем скрипт асинхронно с блокировкой бота
    asyncio.create_task(
        run_script_async(
            script_name="mentors.py",
            chat_id=chat_id,
            bot=message.bot,
            operation_type="mentors",
            estimated_minutes=10
        )
    )


@router.message(F.text == "📚 Обновить базу домашек")
async def update_all_homeworks_handler(message: Message):
    """Обновляет всю базу домашних заданий"""
    
    # Проверка авторизации
    if not await check_authorization(message):
        return
    
    # Проверка прав администратора
    if not await check_admin_rights(message):
        return
    
    chat_id = message.chat.id
    
    # Проверка блокировки
    if chat_id in _update_lock:
        await message.answer(
            "⏳ Обновление уже выполняется.\n"
            "Пожалуйста, дождитесь завершения предыдущего обновления."
        )
        return
    
    # Проверяем, не активен ли уже режим обслуживания
    if await maintenance_manager.is_maintenance_active():
        await message.answer(
            "⚠️ Бот уже находится в режиме обслуживания.\n"
            "Дождитесь завершения текущего обновления."
        )
        return
    
    # Добавляем блокировку
    _update_lock.add(chat_id)
    
    # Информируем о начале обновления
    await message.answer(
        "🔄 <b>Запуск обновления базы домашних заданий...</b>\n\n"
        "⏳ Процесс запущен в фоновом режиме.\n"
        "⚠️ <b>БОТ БУДЕТ ЗАБЛОКИРОВАН на время обновления</b>\n\n"
        "Примерное время: ~30-60 минут\n"
        "Все пользователи получат уведомление."
    )
    
    # Запускаем скрипт асинхронно с блокировкой бота
    asyncio.create_task(
        run_script_async(
            script_name="homeworks.py",
            chat_id=chat_id,
            bot=message.bot,
            operation_type="homeworks",
            estimated_minutes=60
        )
    )


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
