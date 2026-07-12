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

CHOOSING_LANG, CHOOSING_CURRENCY, CHOOSING_CATEGORY, ENTERING_AMOUNT, ENTERING_DESCRIPTION = range(5)

CURRENCIES = {
    "RUB": "₽", "UAH": "₴", "USD": "$", "EUR": "€"
}

EXPENSE_CATEGORIES = ["🍔 Еда", "🚗 Транспорт", "🏠 Жильё", "👗 Одежда", "💊 Здоровье",
                      "🎮 Развлечения", "📚 Образование", "💡 Услуги", "🛒 Покупки", "❓ Другое"]
INCOME_CATEGORIES = ["💼 Зарплата", "🎁 Подарок", "📈 Инвестиции", "🔧 Фриланс", "💰 Другое"]

STRINGS = {
    "ru": {
        "welcome": (
            "👋 Привет, {name}!\n\n"
            "💼 Я твой личный бухгалтер — помогу держать финансы под контролем.\n"
            "Буду следить за доходами и расходами, считать баланс и показывать статистику.\n\n"
            "Сначала выбери валюту:"
        ),
        "welcome_back": "👋 Привет, {name}! Выбери действие:",
        "choose_currency": "💱 Выбери валюту:",
        "currency_set": "✅ Валюта установлена: *{symbol}*\n\nГотов к работе!",
        "choose_action": "Выбери действие:",
        "choose_expense_cat": "📂 Выбери категорию расхода:",
        "choose_income_cat": "📂 Выбери категорию дохода:",
        "enter_amount": "✅ Категория: *{cat}*\n\nВведи сумму:",
        "enter_desc": "📝 Добавь описание (или /skip чтобы пропустить):",
        "invalid_amount": "❌ Введи корректную сумму (например: `1500` или `99.90`):",
        "saved": "{emoji} *{type} записан!*\n\n💳 Сумма: `{sign}{amount:,.2f} {symbol}`\n📂 Категория: {cat}\n📝 Описание: {desc}\n🕐 Дата: {date}",
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
        "change_currency": "💱 Сменить валюту",
        "change_lang": "🌍 Сменить язык",
        "help": (
            "📖 *Как пользоваться ботом:*\n\n"
            "➕ *Добавить расход* — записать трату\n"
            "💰 *Добавить доход* — записать поступление\n"
            "📊 *Статистика* — сводка за период\n"
            "📋 *История* — последние транзакции\n"
            "💼 *Баланс* — текущий баланс\n"
            "⚙️ *Настройки* — язык и валюта\n\n"
            "Быстрый ввод:\n`-500 еда` или `+1000 зарплата`"
        ),
        "quick_unknown": "Используй меню или быстрый ввод:\n`+1000 зарплата` или `-500 еда`",
        "quick_error": "❌ Неверный формат. Пример: `-500 еда`",
        "type_expense": "Расход", "type_income": "Доход",
        "btn_expense": "➕ Добавить расход", "btn_income": "💰 Добавить доход",
        "btn_stats": "📊 Статистика", "btn_history": "📋 История",
        "btn_balance": "💼 Баланс", "btn_settings": "⚙️ Настройки",
        "period_today": "📅 За сегодня", "period_week": "📆 За неделю",
        "period_month": "🗓️ За месяц", "period_all": "📊 За всё время",
        "lang_name": "🇷🇺 Русский",
        "currency_rub": "🇷🇺 Рубль (₽)", "currency_uah": "🇺🇦 Гривна (₴)",
        "currency_usd": "🇺🇸 Доллар ($)", "currency_eur": "🇪🇺 Евро (€)",
    },
    "uk": {
        "welcome": (
            "👋 Привіт, {name}!\n\n"
            "💼 Я твій особистий бухгалтер — допоможу тримати фінанси під контролем.\n"
            "Стежитиму за доходами та витратами, рахуватиму баланс і показуватиму статистику.\n\n"
            "Спочатку обери валюту:"
        ),
        "welcome_back": "👋 Привіт, {name}! Обери дію:",
        "choose_currency": "💱 Обери валюту:",
        "currency_set": "✅ Валюту встановлено: *{symbol}*\n\nГотовий до роботи!",
        "choose_action": "Обери дію:",
        "choose_expense_cat": "📂 Обери категорію витрат:",
        "choose_income_cat": "📂 Обери категорію доходу:",
        "enter_amount": "✅ Категорія: *{cat}*\n\nВведи суму:",
        "enter_desc": "📝 Додай опис (або /skip щоб пропустити):",
        "invalid_amount": "❌ Введи коректну суму (наприклад: `1500` або `99.90`):",
        "saved": "{emoji} *{type} записано!*\n\n💳 Сума: `{sign}{amount:,.2f} {symbol}`\n📂 Категорія: {cat}\n📝 Опис: {desc}\n🕐 Дата: {date}",
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
        "change_currency": "💱 Змінити валюту",
        "change_lang": "🌍 Змінити мову",
        "help": (
            "📖 *Як користуватися ботом:*\n\n"
            "➕ *Додати витрату* — записати трату\n"
            "💰 *Додати дохід* — записати надходження\n"
            "📊 *Статистика* — зведення за період\n"
            "📋 *Історія* — останні транзакції\n"
            "💼 *Баланс* — поточний баланс\n"
            "⚙️ *Налаштування* — мова та валюта\n\n"
            "Швидке введення:\n`-500 їжа` або `+1000 зарплата`"
        ),
        "quick_unknown": "Використовуй меню або швидке введення:\n`+1000 зарплата` або `-500 їжа`",
        "quick_error": "❌ Невірний формат. Приклад: `-500 їжа`",
        "type_expense": "Витрату", "type_income": "Дохід",
        "btn_expense": "➕ Додати витрату", "btn_income": "💰 Додати дохід",
        "btn_stats": "📊 Статистика", "btn_history": "📋 Історія",
        "btn_balance": "💼 Баланс", "btn_settings": "⚙️ Налаштування",
        "period_today": "📅 Сьогодні", "period_week": "📆 За тиждень",
        "period_month": "🗓️ За місяць", "period_all": "📊 За весь час",
        "lang_name": "🇺🇦 Українська",
        "currency_rub": "🇷🇺 Рубль (₽)", "currency_uah": "🇺🇦 Гривня (₴)",
        "currency_usd": "🇺🇸 Долар ($)", "currency_eur": "🇪🇺 Євро (€)",
    },
    "en": {
        "welcome": (
            "👋 Hello, {name}!\n\n"
            "💼 I'm your personal accountant — I'll help you keep your finances under control.\n"
            "I'll track your income and expenses, calculate your balance, and show you statistics.\n\n"
            "First, choose your currency:"
        ),
        "welcome_back": "👋 Hello, {name}! Choose an action:",
        "choose_currency": "💱 Choose your currency:",
        "currency_set": "✅ Currency set: *{symbol}*\n\nReady to go!",
        "choose_action": "Choose an action:",
        "choose_expense_cat": "📂 Choose expense category:",
        "choose_income_cat": "📂 Choose income category:",
        "enter_amount": "✅ Category: *{cat}*\n\nEnter amount:",
        "enter_desc": "📝 Add a description (or /skip to skip):",
        "invalid_amount": "❌ Enter a valid amount (e.g. `1500` or `99.90`):",
        "saved": "{emoji} *{type} saved!*\n\n💳 Amount: `{sign}{amount:,.2f} {symbol}`\n📂 Category: {cat}\n📝 Note: {desc}\n🕐 Date: {date}",
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
        "change_currency": "💱 Change currency",
        "change_lang": "🌍 Change language",
        "help": (
            "📖 *How to use the bot:*\n\n"
            "➕ *Add expense* — record a spending\n"
            "💰 *Add income* — record earnings\n"
            "📊 *Statistics* — summary by period\n"
            "📋 *History* — last transactions\n"
            "💼 *Balance* — current balance\n"
            "⚙️ *Settings* — language and currency\n\n"
            "Quick input:\n`-500 food` or `+1000 salary`"
        ),
        "quick_unknown": "Use the menu or quick input:\n`+1000 salary` or `-500 food`",
        "quick_error": "❌ Invalid format. Example: `-500 food`",
        "type_expense": "Expense", "type_income": "Income",
        "btn_expense": "➕ Add expense", "btn_income": "💰 Add income",
        "btn_stats": "📊 Statistics", "btn_history": "📋 History",
        "btn_balance": "💼 Balance", "btn_settings": "⚙️ Settings",
        "period_today": "📅 Today", "period_week": "📆 This week",
        "period_month": "🗓️ This month", "period_all": "📊 All time",
        "lang_name": "🇬🇧 English",
        "currency_rub": "🇷🇺 Ruble (₽)", "currency_uah": "🇺🇦 Hryvnia (₴)",
        "currency_usd": "🇺🇸 Dollar ($)", "currency_eur": "🇪🇺 Euro (€)",
    },
}

db = Database("finance.db")


def s(user_id, key):
    lang = db.get_user_lang(user_id) or "ru"
    return STRINGS.get(lang, STRINGS["ru"]).get(key, key)


def get_symbol(user_id):
    code = db.get_user_currency(user_id) or "RUB"
    return CURRENCIES.get(code, "₽")


def get_main_keyboard(user_id):
    st = STRINGS.get(db.get_user_lang(user_id) or "ru", STRINGS["ru"])
    keyboard = [
        [KeyboardButton(st["btn_expense"]), KeyboardButton(st["btn_income"])],
        [KeyboardButton(st["btn_stats"]), KeyboardButton(st["btn_history"])],
        [KeyboardButton(st["btn_balance"]), KeyboardButton(st["btn_settings"])],
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

    # New user — choose language
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("🇺🇦 Українська", callback_data="lang_uk")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
    ])
    await update.message.reply_text(
        "🌍 Выбери язык / Обери мову / Choose language:",
        reply_markup=keyboard
    )
    return CHOOSING_LANG


async def lang_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.replace("lang_", "")
    user = update.effective_user
    db.set_user_lang(user.id, lang)

    st = STRINGS[lang]
    await query.edit_message_text(
        st["welcome"].format(name=user.first_name),
        parse_mode="Markdown",
        reply_markup=get_currency_keyboard(user.id)
    )
    return CHOOSING_CURRENCY


async def currency_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    code = query.data.replace("currency_", "")
    user_id = update.effective_user.id
    db.set_user_currency(user_id, code)
    symbol = get_symbol(user_id)

    await query.edit_message_text(
        s(user_id, "currency_set").format(symbol=symbol),
        parse_mode="Markdown"
    )
    await update.effective_message.reply_text(
        s(user_id, "choose_action"),
        reply_markup=get_main_keyboard(user_id)
    )
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
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def open_currency_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        s(query.from_user.id, "choose_currency"),
        reply_markup=get_currency_keyboard(query.from_user.id)
    )


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
    symbol = get_symbol(query.from_user.id)
    await query.edit_message_text(f"✅ {STRINGS[lang]['lang_name']}", parse_mode="Markdown")
    await update.effective_message.reply_text(
        s(query.from_user.id, "choose_action"),
        reply_markup=get_main_keyboard(query.from_user.id)
    )


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
    await query.edit_message_text(
        s(query.from_user.id, "enter_amount").format(cat=category),
        parse_mode="Markdown"
    )
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
    await update.message.reply_text(s(user_id, "enter_desc"))
    return ENTERING_DESCRIPTION


async def description_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await save_transaction(update, context, update.message.text)
    return ConversationHandler.END


async def skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await save_transaction(update, context, "")
    return ConversationHandler.END


async def save_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE, description: str):
    user_id = update.effective_user.id
    t_type = context.user_data['transaction_type']
    category = context.user_data['category']
    amount = context.user_data['amount']
    symbol = get_symbol(user_id)
    db.add_transaction(user_id, t_type, amount, category, description)

    emoji = "📉" if t_type == 'expense' else "📈"
    sign = "-" if t_type == 'expense' else "+"
    type_name = s(user_id, "type_expense") if t_type == 'expense' else s(user_id, "type_income")

    await update.message.reply_text(
        s(user_id, "saved").format(
            emoji=emoji, type=type_name, sign=sign, amount=amount,
            symbol=symbol, cat=category, desc=description or "—",
            date=datetime.now().strftime('%d.%m.%Y %H:%M')
        ),
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(user_id)
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(s(user_id, "cancelled"), reply_markup=get_main_keyboard(user_id))
    return ConversationHandler.END


async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = db.get_stats(user_id, 'all')
    symbol = get_symbol(user_id)
    income, expense = stats['total_income'], stats['total_expense']
    balance = income - expense
    emoji = "✅" if balance >= 0 else "⚠️"

    text = s(user_id, "balance_title")
    text += s(user_id, "income_line").format(income, symbol)
    text += s(user_id, "expense_line").format(expense, symbol)
    text += "─" * 20 + "\n"
    text += s(user_id, "balance_line").format(emoji, balance, symbol)

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
        date = datetime.fromisoformat(t['date']).strftime('%d.%m %H:%M')
        desc = f" — {t['description']}" if t['description'] else ""
        text += f"{emoji} `{sign}{t['amount']:,.0f} {symbol}` {t['category']}{desc}\n"
        text += f"   🕐 {date}\n\n"

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(s(user_id, "help"), parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))


async def quick_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    symbol = get_symbol(user_id)

    # Check if it's a menu button in any language
    all_buttons = []
    for lang_strings in STRINGS.values():
        all_buttons += [lang_strings.get(k, "") for k in ["btn_expense", "btn_income", "btn_stats", "btn_history", "btn_balance", "btn_settings"]]
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
    db.add_transaction(user_id, t_type, abs(amount), category, description)

    sign = "+" if t_type == 'income' else "-"
    emoji = "📈" if t_type == 'income' else "📉"
    type_name = s(user_id, "type_income") if t_type == 'income' else s(user_id, "type_expense")

    await update.message.reply_text(
        s(user_id, "saved").format(
            emoji=emoji, type=type_name, sign=sign, amount=abs(amount),
            symbol=symbol, cat=category, desc=description or "—",
            date=datetime.now().strftime('%d.%m.%Y %H:%M')
        ),
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(user_id)
    )


def build_button_filter():
    all_buttons = []
    for lang_strings in STRINGS.values():
        for key in ["btn_expense", "btn_income", "btn_stats", "btn_history", "btn_balance", "btn_settings"]:
            btn = lang_strings.get(key, "")
            if btn:
                all_buttons.append(btn)
    pattern = "^(" + "|".join(map(lambda x: x.replace("+", r"\+"), all_buttons)) + ")$"
    return pattern


def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("Установи переменную окружения BOT_TOKEN!")

    app = Application.builder().token(token).build()

    btn_pattern = build_button_filter()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_LANG: [CallbackQueryHandler(lang_chosen, pattern="^lang_")],
            CHOOSING_CURRENCY: [CallbackQueryHandler(currency_chosen, pattern="^currency_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    add_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(btn_pattern), lambda u, c: None)],
        states={
            CHOOSING_CATEGORY: [CallbackQueryHandler(category_chosen_cb, pattern="^cat_")],
            ENTERING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_entered)],
            ENTERING_DESCRIPTION: [
                CommandHandler("skip", skip_description),
                MessageHandler(filters.TEXT & ~filters.COMMAND, description_entered),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))

    # All button handlers
    for lang_key, st in STRINGS.items():
        app.add_handler(MessageHandler(filters.Regex(f"^{st['btn_expense'].replace('+', r'+')}$"), add_expense_start))
        app.add_handler(MessageHandler(filters.Regex(f"^{st['btn_income']}$"), add_income_start))
        app.add_handler(MessageHandler(filters.Regex(f"^{st['btn_stats']}$"), show_stats))
        app.add_handler(MessageHandler(filters.Regex(f"^{st['btn_history']}$"), show_history))
        app.add_handler(MessageHandler(filters.Regex(f"^{st['btn_balance']}$"), show_balance))
        app.add_handler(MessageHandler(filters.Regex(f"^{st['btn_settings']}$"), show_settings))

    app.add_handler(CallbackQueryHandler(currency_chosen, pattern="^currency_"))
    app.add_handler(CallbackQueryHandler(lang_change_cb, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(open_currency_cb, pattern="^open_currency$"))
    app.add_handler(CallbackQueryHandler(open_lang_cb, pattern="^open_lang$"))
    app.add_handler(CallbackQueryHandler(stats_callback, pattern="^stats_"))
    app.add_handler(CallbackQueryHandler(category_chosen_cb, pattern="^cat_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, quick_add))

    logger.info("Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
