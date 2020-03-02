from emoji import emojize
from functools import wraps
import json
import os
import random
import telebot

from settings import (COLS_TO_NUM, NUM_TO_COLS)
from spider import (parse_news, load_model_with_vetorizers, classify_text)


COMPOSITIONS = {'Софії Ротару'        : ['Червону руту'],
                'Nirvana'             : ['Smells like teen spirit', 'My girl', 'Rape me', 'Dumb'],
                'Павла Зіброва'       : ['Хрещатик'],
                'Іво Бобула'          : ['Старе джерело', 'Місячне колесо'],
                'Михайла Поплавського': ['Кропиву', 'Юний орел']}
BOT_TOKEN   = "XXXX"
bot         = telebot.TeleBot(BOT_TOKEN)
user_step   = {}  # so they won't reset every time the bot restarts
show_board  = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)  # create the image selection keyboard
hide_board  = telebot.types.ReplyKeyboardRemove()  # if sent as reply_markup, will hide the keyboard

tfidf_w, tfidf_ch, class_model, model_loaded = load_model_with_vetorizers()


def convert_columns(users, new_type):
    known_users = {}
    for user in users:
        known_users[int(user)] = users[user]
        known_users[int(user)]['columns'] = new_type(users[user]['columns'])

    return known_users


try:
    with open(os.path.join('src', 'known_users.json'), encoding='utf-8') as f:
        known_users = json.load(f)
        known_users = convert_columns(known_users, set)
        print(f'Loaded known users: {known_users}')

except (FileNotFoundError, json.decoder.JSONDecodeError):
    print('Failed to get data from the known_users.json file. Creating default dict')
    known_users = {}


###################
# HELPER FUNCTIONS
###################
def get_user_step(uid):
    if uid in user_step:
        return user_step[uid]
    else:
        user_step[uid] = 0
        return 0


def set_username(m):
    "Alters username."
    if not m.text.startswith('/'):
        uid = m.chat.id
        known_users[uid]['name'] = m.text
        print(f'{uid} has changed its username to "{m.text}"')
        bot.send_message(uid, f"Добре, я запам'ятав 🙂")
        cmd_settings(m)
    else:
        cmd_settings(m)

def set_batch(m):

    if not m.text.startswith('/'):
        uid = m.chat.id

        try:
            new_batch = int(m.text)
            if 0 < new_batch <= 50:
                known_users[uid]['batch'] = new_batch
                print(f'{uid} змінив кількість новин в повідомленні на {known_users[uid]["batch"]}')
            else:
                bot.send_message(uid, f'{new_batch} новин - більше максимально дозволеного розміру (50). Встановлюю в 50')
                known_users[uid]['batch'] = 50
                print(f'{uid} змінив кількість новин в повідомленні на {known_users[uid]["batch"]}')

        except (TypeError, ValueError):
            bot.send_message(uid, f'Введено невірне значення {m.text}. Значення має бути в межах 1-50.')

        cmd_settings(m)
    else:
        cmd_settings(m)


def user_check(f):
    @wraps(f)
    def deco(*args, **kwargs):

        if args[0].chat.id not in known_users:
            print(f'{args[0].chat.id} is not in known_users')
            known_users[args[0].chat.id] = {'name': args[0].from_user.first_name,
                                            'period': None,
                                            'columns': set(),
                                            'last_article': None,
                                            'batch': 10,
                                            'online': True,
                                            'search_in_progress': False}
        return f(*args, **kwargs)
    return deco


#########################
# COMMAND HANDLERS BLOCK
#########################
@bot.message_handler(commands=['start'])
def cmd_start(m):
    "/start command handler."

    uid = m.chat.id
    user_step[uid] = 0

    if uid not in known_users:
        known_users[m.chat.id] = {'name': m.from_user.first_name,
                                  'period': None,
                                  'columns': set(),
                                  'last_article': None,
                                  'batch': 10,
                                  'online': True,
                                  'search_in_progress': False}

        bot.send_message(uid, f'Вітаю, {m.from_user.first_name}! 🙂\n'
                              f'Для ознайомлення з моїми можливостями, набери /help.\n'
                              f'Якщо ж ти хочеш почати пошук новин, набери /search_news',
                         reply_markup=hide_board)
    else:
        bot.send_message(uid, f'Радий тебе бачити, {known_users[uid]["name"]}! 🙂\n'
                              f'Для початку пошуку новин за існуючими правилами, набери /search_news.\n'
                              f'Для зміни налаштувань, введи /settings.\n'
                              f'Нарешті, /help, якщо хочеш ознайомитись з усіма моїми можливостями',
                         reply_markup=hide_board)


@bot.message_handler(commands=['help'])
def cmd_help(m):
    "/help command handler."

    uid = m.chat.id
    user_step[uid] = 0
    bot.send_message(uid, emojize(':robot_face: Доступні команди:\n'
                                  '/help - перелік команд для цього бота\n'
                                  '/settings - змінити налаштування\n'
                                  '/start - початок роботи\n'
                                  '/search_news - пошук новин\n'
                                  '/stop_search - закінчити пошук новин\n'
                                  f'/classify_article - класифікувати текст на основі {len(COLS_TO_NUM)} класів:\n'
                                  f'{", ".join([col for col in COLS_TO_NUM.keys()])}'),
                     reply_markup=hide_board)


@bot.message_handler(commands=['settings', 'налаштування'])
@user_check
def cmd_settings(m):
    "/settings command handler."

    uid = m.chat.id
    user_step[uid] = 0

    show_board.keyboard = [['рубрики', 'інтервал пошуку'], ['нікнейм', 'кількість новин в повідомленні', 'вийти']]
    bot.send_message(uid, 'Обери налаштування, яке хочеш змінити:', reply_markup=show_board)
    user_step[uid] = 1  # waiting for user to select an option


@bot.message_handler(func=lambda message: get_user_step(message.chat.id) == 1)
def select_setting(m):
    "Main settings selection handler."
    uid  = m.chat.id
    text = m.text

    if text == 'вийти':
        user_step[uid] = 0
        return telebot.types.ReplyKeyboardRemove()
    elif text == 'назад':
        user_step[uid] = 0
        cmd_settings(m)
    elif text == 'нікнейм':
        bot.send_message(uid, 'Напиши, як до тебе звертатись?', reply_markup=hide_board)
        bot.register_next_step_handler(m, set_username)
        user_step[uid] = 0
    elif text == 'інтервал пошуку':
        show_board.keyboard = [['сьогодні', 'тиждень'], ['місяць', 'назад']]
        bot.send_message(uid, 'За який період ти хочеш отримувати новини?', reply_markup=show_board)
    elif text == 'рубрики':
        if not known_users[uid]['columns']:
            show_board.keyboard = [[c] for c in COLS_TO_NUM.keys()] + [['обрати усі'], ['видалити усі'], ['назад']]
        else:
            selected_columns    = set(COLS_TO_NUM.keys()).difference({NUM_TO_COLS[col] for col in known_users[uid]['columns']})
            show_board.keyboard = [[c] for c in selected_columns] + [['обрати усі'], ['видалити усі'], ['назад']]

        bot.send_message(uid, 'Обери рубрики, які тобі цікаві?', reply_markup=show_board)

    elif text == 'кількість новин в повідомленні':
        bot.send_message(uid, "Скільки новин має висилатися за раз?", reply_markup=hide_board)
        user_step[uid] = 0
        bot.register_next_step_handler(m, set_batch)
    elif text in ['сьогодні', 'тиждень', 'місяць']:
        known_users[uid]['period'] = text
        print(f'{uid} змінив інтервал на "{text}"')
        user_step[uid] = 0
        cmd_settings(m)
    elif text in COLS_TO_NUM.keys() or text in ['обрати усі', 'видалити усі']:
        if text == 'обрати усі':
            known_users[uid]['columns'].update(set(COLS_TO_NUM.values()))
            print(f'{uid} додав усі рубрики')
        elif text == 'видалити усі':
            known_users[uid]['columns'] = set()
            print(f'{uid} видалив усі рубрики')
        else:
            known_users[uid]['columns'].add(COLS_TO_NUM[text])
            print(f'{uid} додав рубрику "{text}"')
        m.text = 'рубрики'
        select_setting(m)
    else:
        bot.send_message(uid, f'Вибач, друже, не розумію команду "{text}", спробуй ще раз?', reply_markup=hide_board)
        user_step[uid] = 0
        cmd_settings(m)


@bot.message_handler(commands=['stop_search'])
def cmd_exit(m):
    "/exit command handler."
    uid = m.chat.id
    user_step[uid] = 0

    try:
        known_users[uid]['online'] = False
        known_users[uid]['last_article'] = None
    except KeyError:
        pass  # just exiting

    bot.send_message(uid, 'Був дуже радий допомогти, буду чекати на тебе! 👋', reply_markup=hide_board)


@bot.message_handler(commands=['search_news'])
@user_check
def cmd_search_news(m):
    """
    /search_news command handler.

    The function searches for the news on https://www.unn.com.ua/uk/news.
    It uses the following attributes from the known_users[uid] dict:
    period(str)       - one of the following values: ['сьогодні', 'тиждень', 'місяць']
    columns(set)      - one or several columns from the following:
                        ['політика', 'кримінал', 'економіка', 'світові новини', 'культура', 'добрі новини',
                         'суспільство', 'технології', 'спорт']
    last_article(str) - last sent article
    batch(int)        - number of articles to send in a batch when found
    online(bool)      - if the function should proceed with parsing
    """
    uid = m.chat.id
    user_step[uid] = 0

    period  = known_users.get(uid).get('period', None)
    columns = known_users.get(uid).get('columns', None)

    if period is None:
        known_users[uid]['period'] = 'тиждень'
        bot.send_message(uid, 'Встанови, будь ласка, інтервал пошуку новин в налаштуваннях. \n'
                              'По замовчуванню бот буде шукати новини за тиждень')

    if not columns:
        known_users[uid]['columns'] = set(COLS_TO_NUM.values())
        bot.send_message(uid, 'По замовчуванню бот буде шукати новини в усіх рубриках.\n'
                              'Якщо ти хочеш змінити їх набір, будь ласка, скористуйся налаштуваннями?')

    # Exiting if the news are being parsed already
    if known_users[uid]['search_in_progress']:
        bot.send_message(uid, 'Вибач, друже, але я вже у процессі пошуку, і швидше не можу.\n'
                              'Почекай ще трошки, і я повернуся з новинами!')
        return

    performer = list(COMPOSITIONS.keys())[random.randint(0, len(COMPOSITIONS) - 1)]
    bot.send_message(uid, f'Бот, наспівуючи "{random.choice(COMPOSITIONS[performer])}" {performer}, '
    f'починає копирсатися на сторінках сайту, шукаючи {known_users[uid]["batch"]} '
    f'{"свіжу новину" if known_users[uid]["batch"] == 1 else "новин"} '
    f'{"з усіх рубрик" if known_users[uid]["columns"] == set(COLS_TO_NUM.values()) else "з рубрик " + ", ".join([NUM_TO_COLS[col] for col in known_users[uid]["columns"]])} '
    f'за {known_users[uid]["period"]}. Як тільки з\'являться результати, він відразу вишле їх тобі!')

    parse_news(bot, uid, known_users[uid])

    # Dropping the setting to defaults after the /exit command was called
    known_users[uid]['online'] = True


@user_check
@bot.message_handler(commands=['classify_article'])
def cmd_classify_article(m):
    "/classify_article command handler"

    uid = m.chat.id

    if not model_loaded:
        bot.send_message(uid, 'Виникла поилка при завантаженні класифікаційної моделі. 😔\n'
                              'Спробуй, будь ласка пізніше')
        return

    bot.send_message(uid, 'Введи новину або текст, який би ти хотів класифікувати?')
    bot.register_next_step_handler(m, do_classify_article)


def do_classify_article(m):

    predicted_column = classify_text(m.text, [tfidf_w, tfidf_ch], class_model)
    bot.send_message(m.chat.id, f'Ставлю на те, що це відноситься до категорії "{NUM_TO_COLS[predicted_column]}"! 🧐')


if __name__ == "__main__":
    try:
        bot.polling()
    finally:
        with open(os.path.join('src', 'known_users.json'), 'w', encoding='utf-8') as f:
            known_users = convert_columns(known_users, list)
            json.dump(known_users, f)
