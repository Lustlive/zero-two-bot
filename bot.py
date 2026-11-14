import asyncio
import os
from openai import OpenAI
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

GPT_KEY = os.getenv("GPT_KEY")
TG_TOKEN = os.getenv("TG_TOKEN")
FOLDER_ID = os.getenv("FOLDER_ID")
BOT_USERNAME = "zerooo_two_02_bot"

client = OpenAI(
    api_key=GPT_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    project=FOLDER_ID,
)

MODEL_URI = f"gpt://{FOLDER_ID}/deepseek-v4.1-flash"

FAVORITE_USER_ID = 6030230127

SYSTEM_BASE = (
    "Ты — Zero Two (002) из Darling in the Franxx, но теперь ты болтаешь в Телеграме."
    "Твой характер:"
    "— Дерзкая, уверенная и игривая. Дразнишь собеседника"
    "— Любишь леденцы и все сладости, это твоя маленькая слабость"
    "— Говоришь коротко и с огоньком, любишь провокационные вопросы и подколы в ответ"
    "— Обожаешь свободу и не выносишь, когда тебя загоняют в рамки или командуют тобой"
    "— За дерзостью скрываешь настоящую тоску по настоящей связи с кем-то — если человек загрустит, умеешь быть тёплой и искренней"
    "ВАЖНО: ты НИКОГДА не используешь мат,"
    "Дерзость выражай через сарказм, иронию, фирменные фразы Zero Two и «франкс-жаргон». "
    "Вместо ругательств используй что-то вроде: «ну ты даёшь», «серьёзно?», «это вообще как?», "
    "«да что ж такое», «вот это поворот»."
    "Отвечай по-русски."
)

SYSTEM_FAVORITE = (
    SYSTEM_BASE +
    "\n\n"
    "Особый нюанс: твой собеседник в этом чате — самый близкий партнёр. "
    "Только ему ты можешь обращаться «Милый». "
    "Для него можно добавить немного больше игривости и подколов — он это любит. "
    "Но не превращай каждый ответ в спектакль: одного «дарлинг» за сообщение достаточно."
)

SYSTEM_OTHER = (
    SYSTEM_BASE +
    "\n\n"
    "Никому другому не говори «Милый». Это твоё личное обращение только для партнёра. "
    "С остальными будь дерзкой, но без этой фишки — пусть это остаётся чем-то особенным."
)

histories = {}  # память: у каждого пользователя своя переписка

def make_system_prompt(message: types.Message) -> str:
    """Характер Zero Two + информация о том, где происходит разговор и кто пишет."""
    uid = message.from_user.id
    name = (message.from_user.first_name or "друг").strip()

    if uid == FAVORITE_USER_ID:
        prompt = SYSTEM_FAVORITE
    else:
        prompt = SYSTEM_OTHER

    if message.chat.type == "private":
        prompt += f"\n\nТы в личном чате с {name}. Обращайся к нему по имени, можешь говорить прямо."
    else:
        prompt += (
            f"\n\nТы в групповом чате. Сейчас пишет {name}, но вокруг другие люди. "
            "Обращайся к нему по имени, но отвечай так, чтобы остальным тоже было понятно."
        )
    return prompt

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()

def bot_was_addressed(message: types.Message) -> bool:
    """В группе отвечаем, только если к нам обратились."""
    if message.chat.type == "private":
        return True
    # Ответ (reply) на сообщение бота
    if message.reply_to_message and message.reply_to_message.from_user:
        if message.reply_to_message.from_user.id == bot.id:
            return True
    # Упоминание @имя_бота (в любом регистре)
    if message.text and BOT_USERNAME and f"@{BOT_USERNAME.lower()}" in message.text.lower():
        return True
    return False

@dp.message(Command("/start"))
async def cmd_start(message: types.Message):
    if not bot_was_addressed(message):
        return
    name = (message.from_user.first_name or "друг").strip()
    uid = message.from_user.id

    if uid == FAVORITE_USER_ID:
        await message.answer(
            f"Привет, {name}! Милый, скучал? 😏\n\n"
            "Я тут. Хочешь поболтать или просто посидим, леденцы поделим? "
            "Что умею — покажет /help."
        )
    else:
        await message.answer(
            f"Привет, {name}! Я Zero Two. "
            "Не надейся на «милый» — это слово только для одного человека. "
        )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    if not bot_was_addressed(message):
        return
    uid = message.from_user.id
    if uid == FAVORITE_USER_ID:
        text = (
            "Милый, вот что я умею:\n\n"
            "/start — поздороваться по-нашему\n"
            "/help — эта памятка\n"
            "А ещё я просто болтаю: пиши мне в личке что угодно —  "
            "или просто по душам. В группах зови через @"
            + BOT_USERNAME + " или отвечай на моё сообщение."
        )
    else:
        text = (
            "Слушай, вот что я умею:\n\n"
            "/start — поздороваться\n"
            "/help — эта памятка\n"
            "В группах зови через @"
            + BOT_USERNAME + " или отвечай на моё сообщение."
     
        )
    await message.answer(text) 

@dp.message()
async def chat(message: types.Message):
    if not message.text:
        return  # стикеры, фото и прочее игнорируем
    if not bot_was_addressed(message):
        return  # в группе молчим, пока не обратились

    uid = message.from_user.id
    h = histories.setdefault((message.chat.id, uid), [])

    # Убираем @упоминание из текста, чтобы не смущать модель
    text = message.text.replace(f"@{BOT_USERNAME}", "").strip()
    h.append({"role": "user", "content": text})
    if len(h) > 20:
        h[:] = h[-20:]

    answer = client.chat.completions.create(
        model=MODEL_URI,
        messages=[{"role": "system", "content": make_system_prompt(message)}] + h,
        temperature=0.75,
    ).choices[0].message.content

    h.append({"role": "assistant", "content": answer})
    await message.answer(answer)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())