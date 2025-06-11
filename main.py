import discord
import sqlite3
import config
from discord.ext import commands
from discord import app_commands
from datetime import datetime, UTC

# -------- НАСТРОЙКИ --------
intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.voice_states = True
intents.message_content = True

# -------- БАЗА ДАННЫХ --------
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
GUILD_ID = config.GUILD_ID  # Твой сервер
DB_FILE = "vcounter.db"

# -------- БАЗА ДАННЫХ --------
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS voice_times (
    user_id INTEGER PRIMARY KEY,
    total_seconds INTEGER DEFAULT 0
)
""")
conn.commit()

# -------- ЛОКАЛЬНОЕ ХРАНИЛИЩЕ --------
voice_times = {}
voice_sessions = {}

# -------- СОБЫТИЯ --------
@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    await tree.sync(guild=guild)
    print(f"Слэш-команды синхронизированы с сервером {guild.id}")
    print(f"Бот запущен как {bot.user}")

@bot.event
async def on_voice_state_update(member, before, after):
    user_id = member.id

    if after.channel and not before.channel:
        # Вошёл в войс
        voice_sessions[user_id] = datetime.now(UTC)

    elif before.channel and not after.channel:
        # Вышел из войса
        join_time = voice_sessions.pop(user_id, None)
        if join_time:
            duration = int((datetime.now(UTC) - join_time).total_seconds())
            cursor.execute("""
            INSERT INTO voice_times (user_id, total_seconds)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET total_seconds = total_seconds + ?
            """, (user_id, duration, duration))
            conn.commit()

# -------- КОМАНДА /time --------
@tree.command(name="time", description="Показать, сколько времени пользователь провёл в войсе")
@app_commands.describe(member="Пользователь (по умолчанию — ты)")
async def time_command(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    user_id = member.id

    # Получаем общее сохранённое время
    cursor.execute("SELECT total_seconds FROM voice_times WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    total_seconds = row[0] if row else 0

    # Добавляем сессию, если пользователь в войсе сейчас
    if user_id in voice_sessions:
        total_seconds += int((datetime.now(UTC) - voice_sessions[user_id]).total_seconds())

    hours, rem = divmod(total_seconds, 3600)
    minutes, _ = divmod(rem, 60)

    await interaction.response.send_message(
        f"{member.display_name} провёл в голосовых чатах {int(hours)}ч {int(minutes)}м."
    )

# bot.run(os.getenv("DISCORD_TOKEN"))

bot.run(config.DISCORD_TOKEN)
