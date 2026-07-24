import os
import json
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
HISTORY_PATH = os.path.join(DATA_DIR, "ai_history.json")

# Un SEUL historique, partagé par tout le monde sur le serveur (pas par membre).
MAX_EXCHANGES = 50

SYSTEM_PROMPT = (
    "Tu es Noctali Bot, l'assistant IA sympa et décontracté d'un serveur Discord communautaire. "
    "Plusieurs membres différents te parlent dans la même conversation : les messages "
    "'user' peuvent venir de personnes différentes. "
    "Réponds en français, de façon concise et naturelle, comme dans une vraie conversation Discord "
    "(pas de réponses trop longues ou trop formelles). "
    "Tu ne peux pas envoyer d'images ou de vrais memes toi-même : si on te demande un meme, "
    "dis simplement d'utiliser la commande /meme à la place, sans en inventer un en texte."
)


def _load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: str, data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class AIChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        loaded = _load_json(HISTORY_PATH)
        self.history: list = loaded.get("messages", [])  # un seul historique, partagé

    async def _ask_groq(self, author_name: str, question: str) -> str:
        if not GROQ_API_KEY:
            return "⚠️ Aucune clé `GROQ_API_KEY` configurée sur Railway."

        # On préfixe avec le pseudo pour que l'IA sache qui parle dans la conv commune
        self.history.append({"role": "user", "content": f"{author_name} : {question}"})
        del self.history[: -MAX_EXCHANGES * 2]

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self.history

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {"model": GROQ_MODEL, "messages": messages, "max_tokens": 600}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(GROQ_URL, headers=headers, json=payload, timeout=30) as resp:
                    data = await resp.json()
                    if resp.status != 200:
                        error_msg = data.get("error", {}).get("message", str(data))
                        return f"❌ Erreur IA : {error_msg}"
        except Exception as e:
            return f"❌ Erreur de connexion à l'IA : {e}"

        reply = data["choices"][0]["message"]["content"].strip()
        self.history.append({"role": "assistant", "content": reply})
        del self.history[: -MAX_EXCHANGES * 2]
        _save_json(HISTORY_PATH, {"messages": self.history})
        return reply

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if self.bot.user not in message.mentions:
            return

        question = message.content
        for mention in message.mentions:
            question = question.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "")
        question = question.strip() or "Salut !"

        async with message.channel.typing():
            reply = await self._ask_groq(message.author.display_name, question)

        for i in range(0, len(reply), 2000):
            await message.reply(reply[i : i + 2000], mention_author=False)

    @app_commands.command(name="ask", description="Pose une question à l'IA du bot")
    @app_commands.describe(question="Ta question")
    async def ask(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer()
        reply = await self._ask_groq(interaction.user.display_name, question)

        first_chunk, rest = reply[:2000], reply[2000:]
        await interaction.followup.send(first_chunk)
        for i in range(0, len(rest), 2000):
            await interaction.channel.send(rest[i : i + 2000])

    @app_commands.command(
        name="reset_ia", description="Efface l'historique de conversation de l'IA (pour tout le monde)"
    )
    async def reset_ia(self, interaction: discord.Interaction):
        self.history.clear()
        _save_json(HISTORY_PATH, {"messages": self.history})
        await interaction.response.send_message("🧹 Historique de l'IA effacé pour tout le monde.")


async def setup(bot: commands.Bot):
    await bot.add_cog(AIChat(bot))

