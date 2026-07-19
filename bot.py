import logging
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)
from database import Database

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

CHOOSING_LANG, CHOOSING_CURRENCY, CHOOSING_CATEGORY, ENTERING_AMOUNT, ENTERING_DESCRIPTION, \
CHOOSING_DESTINATION, ENTERING_GOAL_NAME, ENTERING_GOAL_AMOUNT = range(8)

CURRENCIES = {"RUB": "₽", "UAH": "₴", "USD": "$", "EUR": "€"}

EXPENSE_CATEGORIES = ["🍔 Еда", "🚗 Транспорт", "🏠 Жильё", "👗 Одежда", "💊 Здоровье",
                      "🎮 Развлечения", "📚 Образование", "💡 Услуги", "🛒 Покупки", "❓ Другое"]
INCOME_CATEGORIES = ["💼 Зарплата", "🎁 Подарок", "📈 Инвестиции", "🔧 Фриланс", "💰 Другое"]

STRINGS = {
    "ru": {
        "welcome": "👋 Привет, {name}!\n\n💼 Я твой личный бухгалтер — помогу держать финансы под контролем.\nБуду следить за доходами и расходами, считать баланс и показывать статистику.\n\nСначала выбери валюту:",
        "welcome_back": "👋 Привет, {name}! Выбери действие:",
        "choose_currency": "💱 Выбери валюту:",
        "currency_set": "✅ Валюта установлена: *{symbol}*\n\nГотов к работе!",
        "choose_action": "Выбери действие:",
        "choose_expense_cat": "📂 Выбери категорию расхода:",
        "choose_income_cat": "📂 Выбери категорию дохода:",
        "enter_amount": "✅ Категория: *{cat}*\n\nВведи сумму:",
        "enter_desc": "📝 Добавь описание (или /skip чтобы пропустить):",
        "invalid_amount": "❌ Введи корректную сумму (например: `1500` или `99.90`):",
        "saved": "{emoji} *{type} записан!*\n\n💳 Сумма: `{sign}{amount:,.2f} {symbol}`\n📂 Категория: {cat}\n{dest_line}📝 Описание: {desc}\n🕐 Дата: {date}",
        "cancelled": "❌ Отменено.",
        "balance_title": "💼 *Общий баланс*\n\n",
        "income_line": "📈 Доходы: `+{:.2f} {}`\n",
        "expense_line": "📉 Расходы: `-{:.2f} {}`\n",
        "balance_line": "{} Баланс: `{:+.2f} {}`",
        "stats_title": "📊 *Статистика {}*\n\n",
        "stats_periods": {"today": "сегодня", "week": "за неделю", "month": "за месяц", "all": "за всё время"},
        "stats_cats": "\n📂 *Расходы по категориям:*\n",
        "history_title": "📋 *Последние 10 транзакций:*\n\n",
        "history_empty": "📋 История пуста. Добавь первую транзакцию!",
        "settings_title": "⚙️ *Настройки*\n\n💰 Валюта: *{symbol}* ({code})\n🌍 Язык: {lang}",
        "change_currency": "💱 Сменить валюту", "change_lang": "🌍 Сменить язык",
        "help": "📖 *Как пользоваться ботом:*\n\n➕ *Добавить расход* — записать трату\n💰 *Добавить доход* — записать поступление\n🫙 *Скарбничка* — копилка с целями\n📊 *Статистика* — сводка за период\n📋 *История* — последние транзакции\n💼 *Баланс* — текущий баланс\n⚙️ *Настройки* — язык и валюта\n\nБыстрый ввод:\n`-500 еда` или `+1000 зарплата`",
        "quick_unknown": "Используй меню или быстрый ввод:\n`+1000 зарплата` или `-500 еда`",
        "quick_error": "❌ Неверный формат. Пример: `-500 еда`",
        "type_expense": "Расход", "type_income": "Доход",
        "btn_expense": "➕ Добавить расход", "btn_income": "💰 Добавить доход",
        "btn_stats": "📊 Статистика", "btn_history": "📋 История",
        "btn_balance": "💼 Баланс", "btn_settings": "⚙️ Настройки",
        "btn_piggy": "🫙 Скарбничка",
        "period_today": "📅 За сегодня", "period_week": "📆 За неделю",
        "period_month": "🗓️ За месяц", "period_all": "📊 За всё время",
        "lang_name": "🇷🇺 Русский",
        "currency_rub": "🇷🇺 Рубль (₽)", "currency_uah": "🇺🇦 Гривна (₴)",
        "currency_usd": "🇺🇸 Доллар ($)", "currency_eur": "🇪🇺 Евро (€)",
        "dest_question": "💰 Куда зачислить доход?",
        "dest_wallet": "👛 Кошелёк", "dest_piggy": "🫙 Скарбничка",
        "dest_wallet_line": "👛 Куда: Кошелёк\n", "dest_piggy_line": "🫙 Куда: Скарбничка\n",
        "piggy_title": "🫙 *Скарбничка*\n\n",
        "piggy_total": "💰 Всего накоплено: `{:.2f} {}`\n\n",
        "piggy_no_goals": "Целей пока нет. Добавь первую!",
        "piggy_goals_title": "🎯 *Цели:*\n",
        "piggy_add_goal": "➕ Добавить цель",
        "piggy_delete_goal": "🗑 Удалить",
        "piggy_enter_goal_name": "🎯 Введи название цели (например: *Отпуск* или *Новый телефон*):",
        "piggy_enter_goal_amount": "💰 Введи сумму цели (например: `5000`):",
        "piggy_goal_saved": "✅ Цель *{name}* на `{amount:,.0f} {symbol}` добавлена!",
        "piggy_goal_deleted": "🗑 Цель удалена.",
        "piggy_progress": "🎯 *{name}*\n{bar} {pct:.0f}%\n`{current:,.0f}` из `{target:,.0f} {symbol}` (осталось `{left:,.0f}`)\n\n",
        "piggy_done": "🎯 *{name}*\n✅ ЦЕЛЬ ДОСТИГНУТА! `{target:,.0f} {symbol}`\n\n",
    },
    "uk": {
        "welcome": "👋 Привіт, {name}!\n\n💼 Я твій особистий бухгалтер — допоможу тримати фінанси під контролем.\nСтежитиму за доходами та витратами, рахуватиму баланс і показуватиму статистику.\n\nСпочатку обери валюту:",
        "welcome_back": "👋 Привіт, {name}! Обери дію:",
        "choose_currency": "💱 Обери валюту:",
        "currency_set": "✅ Валюту встановлено: *{symbol}*\n\nГотовий до роботи!",
        "choose_action": "Обери дію:",
        "choose_expense_cat": "📂 Обери категорію витрат:",
        "choose_income_cat": "📂 Обери категорію доходу:",
        "enter_amount": "✅ Категорія: *{cat}*\n\nВведи суму:",
        "enter_desc": "📝 Додай опис (або /skip щоб пропустити):",
        "invalid_amount": "❌ Введи коректну суму (наприклад: `1500` або `99.90`):",
        "saved": "{emoji} *{type} записано!*\n\n💳 Сума: `{sign}{amount:,.2f} {symbol}`\n📂 Категорія: {cat}\n{dest_line}📝 Опис: {desc}\n🕐 Дата: {date}",
        "cancelled": "❌ Скасовано.",
        "balance_title": "💼 *Загальний баланс*\n\n",
        "income_line": "📈 Доходи: `+{:.2f} {}`\n",
        "expense_line": "📉 Витрати: `-{:.2f} {}`\n",
        "balance_line": "{} Баланс: `{:+.2f} {}`",
        "stats_title": "📊 *Статистика {}*\n\n",
        "stats_periods": {"today": "сьогодні", "week": "за тиждень", "month": "за місяць", "all": "за весь час"},
        "stats_cats": "\n📂 *Витрати за категоріями:*\n",
        "history_title": "📋 *Останні 10 транзакцій:*\n\n",
        "history_empty": "📋 Історія порожня. Додай першу транзакцію!",
        "settings_title": "⚙️ *Налаштування*\n\n💰 Валюта: *{symbol}* ({code})\n🌍 Мова: {lang}",
        "change_currency": "💱 Змінити валюту", "change_lang": "🌍 Змінити мову",
        "help": "📖 *Як користуватися ботом:*\n\n➕ *Додати витрату* — записати трату\n💰 *Додати дохід* — записати надходження\n🫙 *Скарбничка* — копилка з цілями\n📊 *Статистика* — зведення за період\n📋 *Історія* — останні транзакції\n💼 *Баланс* — поточний баланс\n⚙️ *Налаштування* — мова та валюта",
        "quick_unknown": "Використовуй меню або швидке введення:\n`+1000 зарплата` або `-500 їжа`",
        "quick_error": "❌ Невірний формат. Приклад: `-500 їжа`",
        "type_expense": "Витрату", "type_income": "Дохід",
        "btn_expense": "➕ Додати витрату", "btn_income": "💰 Додати дохід",
        "btn_stats": "📊 Статистика", "btn_history": "📋 Історія",
        "btn_balance": "💼 Баланс", "btn_settings": "⚙️ Налаштування",
        "btn_piggy": "🫙 Скарбничка",
        "period_today": "📅 Сьогодні", "period_week": "📆 За тиждень",
        "period_month": "🗓️ За місяць", "period_all": "📊 За весь час",
        "lang_name": "🇺🇦 Українська",
        "currency_rub": "🇷🇺 Рубль (₽)", "currency_uah": "🇺🇦 Гривня (₴)",
        "currency_usd": "🇺🇸 Долар ($)", "currency_eur": "🇪🇺 Євро (€)",
        "dest_question": "💰 Куди зарахувати дохід?",
        "dest_wallet": "👛 Гаманець", "dest_piggy": "🫙 Скарбничка",
        "dest_wallet_line": "👛 Куди: Гаманець\n", "dest_piggy_line": "🫙 Куди: Скарбничка\n",
        "piggy_title": "🫙 *Скарбничка*\n\n",
        "piggy_total": "💰 Всього накопичено: `{:.2f} {}`\n\n",
        "piggy_no_goals": "Цілей поки немає. Додай першу!",
        "piggy_goals_title": "🎯 *Цілі:*\n",
        "piggy_add_goal": "➕ Додати ціль",
        "piggy_delete_goal": "🗑 Видалити",
        "piggy_enter_goal_name": "🎯 Введи назву цілі (наприклад: *Відпустка* або *Новий телефон*):",
        "piggy_enter_goal_amount": "💰 Введи суму цілі (наприклад: `5000`):",
        "piggy_goal_saved": "✅ Ціль *{name}* на `{amount:,.0f} {symbol}` додана!",
        "piggy_goal_deleted": "🗑 Ціль видалена.",
        "piggy_progress": "🎯 *{name}*\n{bar} {pct:.0f}%\n`{current:,.0f}` з `{target:,.0f} {symbol}` (залишилось `{left:,.0f}`)\n\n",
        "piggy_done": "🎯 *{name}*\n✅ ЦІЛЬ ДОСЯГНУТА! `{target:,.0f} {symbol}`\n\n",
    },
    "en": {
        "welcome": "👋 Hello, {name}!\n\n💼 I'm your personal accountant — I'll help you keep your finances under control.\nI'll track your income and expenses, calculate your balance, and show you statistics.\n\nFirst, choose your currency:",
        "welcome_back": "👋 Hello, {name}! Choose an action:",
        "choose_currency": "💱 Choose your currency:",
        "currency_set": "✅ Currency set: *{symbol}*\n\nReady to go!",
        "choose_action": "Choose an action:",
        "choose_expense_cat": "📂 Choose expense category:",
        "choose_income_cat": "📂 Choose income category:",
        "enter_amount": "✅ Category: *{cat}*\n\nEnter amount:",
        "enter_desc": "📝 Add a description (or /skip to skip):",
        "invalid_amount": "❌ Enter a valid amount (e.g. `1500` or `99.90`):",
        "saved": "{emoji} *{type} saved!*\n\n💳 Amount: `{sign}{amount:,.2f} {symbol}`\n📂 Category: {cat}\n{dest_line}📝 Note: {desc}\n🕐 Date: {date}",
        "cancelled": "❌ Cancelled.",
        "balance_title": "💼 *Total Balance*\n\n",
        "income_line": "📈 Income: `+{:.2f} {}`\n",
        "expense_line": "📉 Expenses: `-{:.2f} {}`\n",
        "balance_line": "{} Balance: `{:+.2f} {}`",
        "stats_title": "📊 *Statistics {}*\n\n",
        "stats_periods": {"today": "today", "week": "this week", "month": "this month", "all": "all time"},
        "stats_cats": "\n📂 *Expenses by category:*\n",
        "history_title": "📋 *Last 10 transactions:*\n\n",
        "history_empty": "📋 No transactions yet. Add your first one!",
        "settings_title": "⚙️ *Settings*\n\n💰 Currency: *{symbol}* ({code})\n🌍 Language: {lang}",
        "change_currency": "💱 Change currency", "change_lang": "🌍 Change language",
        "help": "📖 *How to use the bot:*\n\n➕ *Add expense* — record a spending\n💰 *Add income* — record earnings\n🫙 *Piggy Bank* — savings with goals\n📊 *Statistics* — summary by period\n📋 *History* — last transactions\n💼 *Balance* — current balance\n⚙️ *Settings* — language and currency",
        "quick_unknown": "Use the menu or quick input:\n`+1000 salary` or `-500 food`",
        "quick_error": "❌ Invalid format. Example: `-500 food`",
        "type_expense": "Expense", "type_income": "Income",
        "btn_expense": "➕ Add expense", "btn_income": "💰 Add income",
        "btn_stats": "📊 Statistics", "btn_history": "📋 History",
        "btn_balance": "💼 Balance", "btn_settings": "⚙️ Settings",
        "btn_piggy": "🫙 Piggy Bank",
        "period_today": "📅 Today", "period_week": "📆 This week",
        "period_month": "🗓️ This month", "period_all": "📊 All time",
        "lang_name": "🇬🇧 English",
        "currency_rub": "🇷🇺 Ruble (₽)", "currency_uah": "🇺🇦 Hryvnia (₴)",
        "currency_usd": "🇺🇸 Dollar ($)", "currency_eur": "🇪🇺 Euro (€)",
        "dest_question": "💰 Where to put this income?",
        "dest_wallet": "👛 Wallet", "dest_piggy": "🫙 Piggy Bank",
        "dest_wallet_line": "👛 To: Wallet\n", "dest_piggy_line": "🫙 To: Piggy Bank\n",
        "piggy_title": "🫙 *Piggy Bank*\n\n",
        "piggy_total": "💰 Total saved: `{:.2f} {}`\n\n",
        "piggy_no_goals": "No goals yet. Add your first one!",
        "piggy_goals_title": "🎯 *Goals:*\n",
        "piggy_add_goal": "➕ Add goal",
        "piggy_delete_goal": "🗑 Delete",
        "piggy_enter_goal_name": "🎯 Enter goal name (e.g. *Vacation* or *New phone*):",
        "piggy_enter_goal_amount": "💰 Enter goal amount (e.g. `5000`):",
        "piggy_goal_saved": "✅ Goal *{name}* for `{amount:,.0f} {symbol}` added!",
        "piggy_goal_deleted": "🗑 Goal deleted.",
        "piggy_progress": "🎯 *{name}*\n{bar} {pct:.0f}%\n`{current:,.0f}` of `{target:,.0f} {symbol}` (left `{left:,.0f}`)\n\n",
        "piggy_done": "🎯 *{name}*\n✅ GOAL REACHED! `{target:,.0f} {symbol}`\n\n",
    },
}

db = Database("finance.db")


def s(user_id, key):
    lang = db.get_user_lang(user_id) or "ru"
    return STRINGS.get(lang, STRINGS["ru"]).get(key, key)


def get_symbol(user_id):
    code = db.get_user_currency(user_id) or "RUB"
    return CURRENCIES.get(code, "₽")


def make_progress_bar(pct: float, length: int = 10) -> str:
    filled = int(pct / 100 * length)
    filled = min(filled, length)
    return "█" * filled + "░" * (length - filled)


def get_main_keyboard(user_id):
    st = STRINGS.get(db.get_user_lang(user_id) or "ru", STRINGS["ru"])
    keyboard = [
        [KeyboardButton(st["btn_expense"]), KeyboardButton(st["btn_income"])],
        [KeyboardButton(st["btn_stats"]), KeyboardButton(st["btn_history"])],
        [KeyboardButton(st["btn_balance"]), KeyboardButton(st["btn_piggy"])],
        [KeyboardButton(st["btn_settings"])],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_currency_keyboard(user_id):
    st = STRINGS.get(db.get_user_lang(user_id) or "ru", STRINGS["ru"])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(st["currency_rub"], callback_data="currency_RUB")],
        [InlineKeyboardButton(st["currency_uah"], callback_data="currency_UAH")],
        [InlineKeyboardButton(st["currency_usd"], callback_data="currency_USD")],
        [InlineKeyboardButton(st["currency_eur"], callback_data="currency_EUR")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.first_name)
    lang = db.get_user_lang(user.id)
    if lang:
        await update.message.reply_text(
            s(user.id, "welcome_back").format(name=user.first_name),
            reply_markup=get_main_keyboard(user.id)
        )
        return ConversationHandler.END
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("🇺🇦 Українська", callback_data="lang_uk")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
    ])
    await update.message.reply_text("🌍 Выбери язык / Обери мову / Choose language:", reply_markup=keyboard)
    return CHOOSING_LANG


async def lang_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.replace("lang_", "")
    user = update.effective_user
    db.set_user_lang(user.id, lang)
    st = STRINGS[lang]
    await query.edit_message_text(st["welcome"].format(name=user.first_name), parse_mode="Markdown", reply_markup=get_currency_keyboard(user.id))
    return CHOOSING_CURRENCY


async def currency_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    code = query.data.replace("currency_", "")
    user_id = update.effective_user.id
    db.set_user_currency(user_id, code)
    symbol = get_symbol(user_id)
    await query.edit_message_text(s(user_id, "currency_set").format(symbol=symbol), parse_mode="Markdown")
    await update.effective_message.reply_text(s(user_id, "choose_action"), reply_markup=get_main_keyboard(user_id))
    return ConversationHandler.END


async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id) or "ru"
    code = db.get_user_currency(user_id) or "RUB"
    symbol = get_symbol(user_id)
    lang_name = STRINGS[lang]["lang_name"]
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(s(user_id, "change_currency"), callback_data="open_currency")],
        [InlineKeyboardButton(s(user_id, "change_lang"), callback_data="open_lang")],
    ])
    await update.message.reply_text(
        s(user_id, "settings_title").format(symbol=symbol, code=code, lang=lang_name),
        parse_mode="Markdown", reply_markup=keyboard
    )


async def open_currency_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(s(query.from_user.id, "choose_currency"), reply_markup=get_currency_keyboard(query.from_user.id))


async def open_lang_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("🇺🇦 Українська", callback_data="lang_uk")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
    ])
    await query.edit_message_text("🌍 Выбери язык / Обери мову / Choose language:", reply_markup=keyboard)


async def lang_change_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.replace("lang_", "")
    db.set_user_lang(query.from_user.id, lang)
    await query.edit_message_text(f"✅ {STRINGS[lang]['lang_name']}", parse_mode="Markdown")
    await update.effective_message.reply_text(s(query.from_user.id, "choose_action"), reply_markup=get_main_keyboard(query.from_user.id))


async def add_expense_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data['transaction_type'] = 'expense'
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in EXPENSE_CATEGORIES]
    await update.message.reply_text(s(user_id, "choose_expense_cat"), reply_markup=InlineKeyboardMarkup(keyboard))
    return CHOOSING_CATEGORY


async def add_income_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data['transaction_type'] = 'income'
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in INCOME_CATEGORIES]
    await update.message.reply_text(s(user_id, "choose_income_cat"), reply_markup=InlineKeyboardMarkup(keyboard))
    return CHOOSING_CATEGORY


async def category_chosen_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data.replace("cat_", "")
    context.user_data['category'] = category
    await query.edit_message_text(s(query.from_user.id, "enter_amount").format(cat=category), parse_mode="Markdown")
    return ENTERING_AMOUNT


async def amount_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip().replace(',', '.')
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(s(user_id, "invalid_amount"), parse_mode="Markdown")
        return ENTERING_AMOUNT
    context.user_data['amount'] = amount
    context.user_data['description'] = ""
    return await ask_destination(update, context)


async def description_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    return await ask_destination(update, context)


async def skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = ""
    return await ask_destination(update, context)


async def ask_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    t_type = context.user_data.get('transaction_type')
    if t_type == 'income':
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(s(user_id, "dest_wallet"), callback_data="dest_wallet"),
             InlineKeyboardButton(s(user_id, "dest_piggy"), callback_data="dest_piggy")],
        ])
        await update.message.reply_text(s(user_id, "dest_question"), reply_markup=keyboard)
        return CHOOSING_DESTINATION
    else:
        await save_transaction(update, context, destination="wallet")
        return ConversationHandler.END


async def destination_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    destination = query.data.replace("dest_", "")
    await query.delete_message()
    await save_transaction(query, context, destination=destination)
    return ConversationHandler.END


async def save_transaction(update, context: ContextTypes.DEFAULT_TYPE, destination: str = "wallet"):
    if hasattr(update, 'effective_user'):
        user_id = update.effective_user.id
    else:
        user_id = update.from_user.id

    t_type = context.user_data['transaction_type']
    category = context.user_data['category']
    amount = context.user_data['amount']
    description = context.user_data.get('description', '')
    symbol = get_symbol(user_id)

    db.add_transaction(user_id, t_type, amount, category, description, destination)

    emoji = "📉" if t_type == 'expense' else "📈"
    sign = "-" if t_type == 'expense' else "+"
    type_name = s(user_id, "type_expense") if t_type == 'expense' else s(user_id, "type_income")
    dest_line = s(user_id, f"dest_{destination}_line") if t_type == 'income' else ""

    msg = s(user_id, "saved").format(
        emoji=emoji, type=type_name, sign=sign, amount=amount,
        symbol=symbol, cat=category, dest_line=dest_line,
        desc=description or "—", date=datetime.now().strftime('%d.%m.%Y %H:%M')
    )

    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))
    elif hasattr(update, 'effective_message') and update.effective_message:
        await update.effective_message.reply_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(s(user_id, "cancelled"), reply_markup=get_main_keyboard(user_id))
    return ConversationHandler.END


async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = db.get_stats(user_id, 'all')
    symbol = get_symbol(user_id)
    income, expense = stats['total_income'], stats['total_expense']
    wallet = db.get_wallet_balance(user_id)
    piggy = db.get_piggy_total(user_id)
    total = wallet + piggy
    wallet_emoji = "✅" if wallet >= 0 else "⚠️"

    text = s(user_id, "balance_title")
    text += s(user_id, "income_line").format(income, symbol)
    text += s(user_id, "expense_line").format(expense, symbol)
    text += "─" * 20 + "\n"
    text += f"{wallet_emoji} 👛 Кошелёк: `{wallet:,.2f} {symbol}`\n"
    text += f"🫙 Скарбничка: `{piggy:,.2f} {symbol}`\n"
    text += f"💰 Итого: `{total:,.2f} {symbol}`"

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    st = STRINGS.get(db.get_user_lang(user_id) or "ru", STRINGS["ru"])
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(st["period_today"], callback_data="stats_today")],
        [InlineKeyboardButton(st["period_week"], callback_data="stats_week")],
        [InlineKeyboardButton(st["period_month"], callback_data="stats_month")],
        [InlineKeyboardButton(st["period_all"], callback_data="stats_all")],
    ])
    await update.message.reply_text("📊", reply_markup=keyboard)


async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    period = query.data.replace("stats_", "")
    user_id = query.from_user.id
    stats = db.get_stats(user_id, period)
    symbol = get_symbol(user_id)
    lang = db.get_user_lang(user_id) or "ru"
    st = STRINGS[lang]
    period_name = st["stats_periods"].get(period, period)
    income, expense = stats['total_income'], stats['total_expense']
    balance = income - expense
    text = st["stats_title"].format(period_name)
    text += st["income_line"].format(income, symbol)
    text += st["expense_line"].format(expense, symbol)
    text += st["balance_line"].format("💼", balance, symbol) + "\n"
    if stats['expense_by_category']:
        text += st["stats_cats"]
        for cat, amount in sorted(stats['expense_by_category'].items(), key=lambda x: -x[1]):
            pct = (amount / expense * 100) if expense > 0 else 0
            text += f"  {cat}: `{amount:,.2f} {symbol}` ({pct:.0f}%)\n"
    await query.edit_message_text(text, parse_mode="Markdown")


async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    transactions = db.get_history(user_id, limit=10)
    symbol = get_symbol(user_id)
    if not transactions:
        await update.message.reply_text(s(user_id, "history_empty"), reply_markup=get_main_keyboard(user_id))
        return
    text = s(user_id, "history_title")
    for t in transactions:
        emoji = "📉" if t['type'] == 'expense' else "📈"
        sign = "-" if t['type'] == 'expense' else "+"
        dest_icon = "🫙" if t.get('destination') == 'piggy' else ""
        date = datetime.fromisoformat(t['date']).strftime('%d.%m %H:%M')
        desc = f" — {t['description']}" if t['description'] else ""
        text += f"{emoji}{dest_icon} `{sign}{t['amount']:,.0f} {symbol}` {t['category']}{desc}\n"
        text += f"   🕐 {date}\n\n"
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))


async def show_piggy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    symbol = get_symbol(user_id)
    total = db.get_piggy_total(user_id)
    goals = db.get_piggy_goals(user_id)

    text = s(user_id, "piggy_title")
    text += s(user_id, "piggy_total").format(total, symbol)

    if goals:
        text += s(user_id, "piggy_goals_title")
        for g in goals:
            target = g['target']
            current = min(total, target)
            pct = (current / target * 100) if target > 0 else 0
            left = max(target - total, 0)
            if total >= target:
                text += s(user_id, "piggy_done").format(name=g['name'], target=target, symbol=symbol)
            else:
                bar = make_progress_bar(pct)
                text += s(user_id, "piggy_progress").format(
                    name=g['name'], bar=bar, pct=pct,
                    current=current, target=target, symbol=symbol, left=left
                )
    else:
        text += s(user_id, "piggy_no_goals")

    keyboard_rows = []
    for g in goals:
        keyboard_rows.append([InlineKeyboardButton(f"🗑 {g['name']}", callback_data=f"delgoal_{g['id']}")])
    keyboard_rows.append([InlineKeyboardButton(s(user_id, "piggy_add_goal"), callback_data="add_goal")])

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard_rows))


async def piggy_add_goal_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)
    await update.effective_message.reply_text(
        s(query.from_user.id, "piggy_enter_goal_name"), parse_mode="Markdown"
    )
    return ENTERING_GOAL_NAME


async def piggy_goal_name_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['goal_name'] = update.message.text
    await update.message.reply_text(s(update.effective_user.id, "piggy_enter_goal_amount"), parse_mode="Markdown")
    return ENTERING_GOAL_AMOUNT


async def piggy_goal_amount_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip().replace(',', '.')
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(s(user_id, "invalid_amount"), parse_mode="Markdown")
        return ENTERING_GOAL_AMOUNT

    name = context.user_data.get('goal_name', '?')
    symbol = get_symbol(user_id)
    db.add_piggy_goal(user_id, name, amount)
    await update.message.reply_text(
        s(user_id, "piggy_goal_saved").format(name=name, amount=amount, symbol=symbol),
        parse_mode="Markdown", reply_markup=get_main_keyboard(user_id)
    )
    return ConversationHandler.END


async def piggy_delete_goal_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    goal_id = int(query.data.replace("delgoal_", ""))
    db.delete_piggy_goal(goal_id)
    await query.edit_message_text(s(query.from_user.id, "piggy_goal_deleted"), parse_mode="Markdown")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.reset_user(user_id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("🇺🇦 Українська", callback_data="lang_uk")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
    ])
    await update.message.reply_text("🔄 Настройки сброшены. Выбери язык:\n\n🌍 Выбери язык / Обери мову / Choose language:", reply_markup=keyboard)
    return CHOOSING_LANG


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(s(user_id, "help"), parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))


async def quick_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    symbol = get_symbol(user_id)
    all_buttons = [STRINGS[l].get(k, "") for l in STRINGS for k in ["btn_expense","btn_income","btn_stats","btn_history","btn_balance","btn_settings","btn_piggy"]]
    if text in all_buttons:
        return
    if not (text.startswith('+') or text.startswith('-')):
        await update.message.reply_text(s(user_id, "quick_unknown"), parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))
        return
    parts = text.split(maxsplit=1)
    try:
        amount = float(parts[0].replace(',', '.'))
    except ValueError:
        await update.message.reply_text(s(user_id, "quick_error"), parse_mode="Markdown")
        return
    description = parts[1] if len(parts) > 1 else ""
    t_type = 'income' if amount > 0 else 'expense'
    category = "💰 Другое" if t_type == 'income' else "❓ Другое"
    db.add_transaction(user_id, t_type, abs(amount), category, description, "wallet")
    sign = "+" if t_type == 'income' else "-"
    emoji = "📈" if t_type == 'income' else "📉"
    type_name = s(user_id, "type_income") if t_type == 'income' else s(user_id, "type_expense")
    await update.message.reply_text(
        s(user_id, "saved").format(
            emoji=emoji, type=type_name, sign=sign, amount=abs(amount),
            symbol=symbol, cat=category, dest_line="",
            desc=description or "—", date=datetime.now().strftime('%d.%m.%Y %H:%M')
        ),
        parse_mode="Markdown", reply_markup=get_main_keyboard(user_id)
    )


def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("Установи переменную окружения BOT_TOKEN!")

    app = Application.builder().token(token).build()

    start_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_LANG: [CallbackQueryHandler(lang_chosen, pattern="^lang_")],
            CHOOSING_CURRENCY: [CallbackQueryHandler(currency_chosen, pattern="^currency_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    piggy_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(piggy_add_goal_cb, pattern="^add_goal$")],
        states={
            ENTERING_GOAL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, piggy_goal_name_entered)],
            ENTERING_GOAL_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, piggy_goal_amount_entered)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    income_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^(➕ Добавить расход|➕ Додати витрату|➕ Add expense)$"), add_expense_start),
            MessageHandler(filters.Regex("^(💰 Добавить доход|💰 Додати дохід|💰 Add income)$"), add_income_start),
        ],
        states={
            CHOOSING_CATEGORY: [CallbackQueryHandler(category_chosen_cb, pattern="^cat_")],
            ENTERING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_entered)],
            ENTERING_DESCRIPTION: [
                CommandHandler("skip", skip_description),
                MessageHandler(filters.TEXT & ~filters.COMMAND, description_entered),
            ],
            CHOOSING_DESTINATION: [CallbackQueryHandler(destination_chosen, pattern="^dest_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    app.add_handler(start_conv)
    app.add_handler(piggy_conv)
    app.add_handler(income_conv)
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset", reset_command))

    for lang_key, st in STRINGS.items():
        app.add_handler(MessageHandler(filters.Regex(f"^{st['btn_stats']}$"), show_stats))
        app.add_handler(MessageHandler(filters.Regex(f"^{st['btn_history']}$"), show_history))
        app.add_handler(MessageHandler(filters.Regex(f"^{st['btn_balance']}$"), show_balance))
        app.add_handler(MessageHandler(filters.Regex(f"^{st['btn_settings']}$"), show_settings))
        app.add_handler(MessageHandler(filters.Regex(f"^{st['btn_piggy']}$"), show_piggy))

    app.add_handler(CallbackQueryHandler(currency_chosen, pattern="^currency_"))
    app.add_handler(CallbackQueryHandler(lang_change_cb, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(open_currency_cb, pattern="^open_currency$"))
    app.add_handler(CallbackQueryHandler(open_lang_cb, pattern="^open_lang$"))
    app.add_handler(CallbackQueryHandler(stats_callback, pattern="^stats_"))
    app.add_handler(CallbackQueryHandler(category_chosen_cb, pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(piggy_delete_goal_cb, pattern="^delgoal_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_handler))

    logger.info("Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


async def ai_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import httpx, json as json_lib
    user_id = update.effective_user.id
    text = update.message.text.strip()
    symbol = get_symbol(user_id)
    lang = db.get_user_lang(user_id) or "ru"

    all_buttons = [STRINGS[l].get(k, "") for l in STRINGS for k in ["btn_expense","btn_income","btn_stats","btn_history","btn_balance","btn_settings","btn_piggy"]]
    if text in all_buttons:
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        await update.message.reply_text("⚠️ AI не настроен.", reply_markup=get_main_keyboard(user_id))
        return

    await update.message.chat.send_action("typing")

    # Gather user's financial data for AI context
    stats_all = db.get_stats(user_id, 'all')
    stats_month = db.get_stats(user_id, 'month')
    piggy_total = db.get_piggy_total(user_id)
    wallet_balance = db.get_wallet_balance(user_id)
    piggy_goals = db.get_piggy_goals(user_id)
    recent = db.get_history(user_id, limit=5)

    total = wallet_balance + piggy_total

    goals_info = ""
    for g in piggy_goals:
        pct = min(piggy_total / g['target'] * 100, 100) if g['target'] > 0 else 0
        left = max(g['target'] - piggy_total, 0)
        goals_info += f"  - {g['name']}: цель {g['target']:,.0f} {symbol}, накоплено {piggy_total:,.0f}, прогресс {pct:.0f}%, осталось {left:,.0f}\n"

    recent_info = ""
    for t in recent:
        sign = "+" if t['type'] == 'income' else "-"
        recent_info += f"  - {sign}{t['amount']:,.0f} {symbol} {t['category']} ({t.get('date','')[:10]})\n"

    expense_cats = ""
    for cat, amt in sorted(stats_month['expense_by_category'].items(), key=lambda x: -x[1]):
        expense_cats += f"  - {cat}: {amt:,.0f} {symbol}\n"

    user_data_context = f"""
ДАННЫЕ ПОЛЬЗОВАТЕЛЯ (используй для ответов на вопросы о финансах):
Валюта: {symbol}

БАЛАНС (за всё время):
- Доходы: +{stats_all['total_income']:,.2f} {symbol}
- Расходы: -{stats_all['total_expense']:,.2f} {symbol}
- Баланс кошелька: {balance:,.2f} {symbol}

ЗА ПОСЛЕДНИЙ МЕСЯЦ:
- Доходы: +{stats_month['total_income']:,.2f} {symbol}
- Расходы: -{stats_month['total_expense']:,.2f} {symbol}
- Расходы по категориям:
{expense_cats or '  нет данных'}

СКАРБНИЧКА (копилка):
- Накоплено: {piggy_total:,.2f} {symbol}
- Цели:
{goals_info or '  целей нет'}

ПОСЛЕДНИЕ 5 ТРАНЗАКЦИЙ:
{recent_info or '  нет транзакций'}

ВОЗМОЖНОСТИ БОТА:
- Кнопки меню: добавить расход/доход, статистика, история, баланс, скарбничка, настройки
- Скарбничка: копилка с целями, можно добавлять цели и отслеживать прогресс
- При добавлении дохода можно выбрать куда: кошелёк или скарбничка
- Языки: русский, украинский, английский
- Валюты: рубль, гривна, доллар, евро
- AI ассистент: можно писать обычным текстом ("потратил 200 на еду", "добавь 1000 зарплата")
- /reset — сброс языка и валюты
- Статистика за: сегодня, неделю, месяц, всё время
"""

    system_prompt = f"""Ты финансовый ассистент в Telegram боте. Язык пользователя: {lang}. Отвечай на том же языке что и пользователь.

{user_data_context}

Если пользователь хочет добавить транзакцию — распознай и верни JSON:
{{"action": "transaction", "type": "income" или "expense", "amount": число, "category": категория, "destination": "wallet" или "piggy", "description": ""}}

Категории расходов: Еда, Транспорт, Жильё, Одежда, Здоровье, Развлечения, Образование, Услуги, Покупки, Другое
Категории доходов: Зарплата, Подарок, Инвестиции, Фриланс, Другое
Destination "piggy" только если пользователь упоминает скарбничку/копилку/накопления.

Если это вопрос о финансах или боте — ответь используя данные выше и верни JSON:
{{"action": "answer", "text": "твой ответ"}}

Если это любой другой вопрос — ответь кратко и верни JSON:
{{"action": "answer", "text": "твой ответ"}}

Отвечай ТОЛЬКО валидным JSON без markdown блоков. Суммы форматируй красиво."""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-sonnet-4-6", "max_tokens": 500, "system": system_prompt, "messages": [{"role": "user", "content": text}]}
            )
        data = resp.json()
        raw = data["content"][0]["text"].strip().replace("```json","").replace("```","").strip()
        result = json_lib.loads(raw)

        if result.get("action") == "transaction":
            t_type = result.get("type", "expense")
            amount = float(result.get("amount", 0))
            cat_name = result.get("category", "Другое")
            destination = result.get("destination", "wallet")
            description = result.get("description", "")
            cat_map = {
                "еда":"🍔 Еда","транспорт":"🚗 Транспорт","жильё":"🏠 Жильё","жилье":"🏠 Жильё",
                "одежда":"👗 Одежда","здоровье":"💊 Здоровье","развлечения":"🎮 Развлечения",
                "образование":"📚 Образование","услуги":"💡 Услуги","покупки":"🛒 Покупки",
                "зарплата":"💼 Зарплата","подарок":"🎁 Подарок","инвестиции":"📈 Инвестиции","фриланс":"🔧 Фриланс",
            }
            category = cat_map.get(cat_name.lower(), f"❓ {cat_name}")
            db.add_transaction(user_id, t_type, amount, category, description, destination)
            emoji = "📈" if t_type == "income" else "📉"
            sign = "+" if t_type == "income" else "-"
            type_name = s(user_id, "type_income") if t_type == "income" else s(user_id, "type_expense")
            dest_line = s(user_id, f"dest_{destination}_line") if t_type == "income" else ""
            await update.message.reply_text(
                s(user_id, "saved").format(
                    emoji=emoji, type=type_name, sign=sign, amount=amount,
                    symbol=symbol, cat=category, dest_line=dest_line,
                    desc=description or "—", date=datetime.now().strftime('%d.%m.%Y %H:%M')
                ),
                parse_mode="Markdown", reply_markup=get_main_keyboard(user_id)
            )
        else:
            await update.message.reply_text(f"🤖 {result.get('text','')}", reply_markup=get_main_keyboard(user_id))
    except Exception as e:
        logger.error(f"AI error: {e}")
        await update.message.reply_text("⚠️ Ошибка AI. Попробуй снова.", reply_markup=get_main_keyboard(user_id))


if __name__ == "__main__":
    main()
