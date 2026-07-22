import os
import json
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
HISTORY_PATH = os.path.join(DATA_DIR, "ai_history.json")

# Nombre d'ÉCHANGES (question + réponse) gardés en mémoire, PAR MEMBRE.
# Comme tout reste dans l'historique de la personne, si elle demande un jour
# "parle-moi plus jeune", l'IA continue naturellement sur ce ton avec ELLE
# à chaque fois (l'instruction reste dans son historique) — sans affecter
# les autres membres, qui ont leur propre historique séparé.
MAX_EXCHANGES = 50

SYSTEM_PROMPT = (
    "Tu es Noctali Bot, l'assistant IA sympa et décontracté d'un serveur Discord communautaire. "
    "Réponds en français, de façon concise et naturelle, comme dans une vraie conversation Discord "
    "(pas de réponses trop longues ou trop formelles). "
    "Si l'utilisateur t'a déjà demandé d'adopter un ton ou un style particulier plus tôt dans la "
    "conversation, continue de t'y tenir avec lui. "
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
        self.history = _load_json(HISTORY_PATH)  # {user_id: [{"role":.., "content":..}, ...]}

    async def _ask_groq(self, user_id: str, question: str) -> str:
        if not GROQ_API_KEY:
            return "⚠️ Aucune clé `GROQ_API_KEY` configurée sur Railway."

        history = self.history.setdefault(user_id, [])
        history.append({"role": "user", "content": question})
        del history[: -MAX_EXCHANGES * 2]  # *2 : question + réponse par échange

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

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
        history.append({"role": "assistant", "content": reply})
        del history[: -MAX_EXCHANGES * 2]
        _save_json(HISTORY_PATH, self.history)
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
            reply = await self._ask_groq(str(message.author.id), question)

        for i in range(0, len(reply), 2000):
            await message.reply(reply[i : i + 2000], mention_author=False)

    @app_commands.command(name="ask", description="Pose une question à l'IA du bot")
    @app_commands.describe(question="Ta question")
    async def ask(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer()
        reply = await self._ask_groq(str(interaction.user.id), question)

        first_chunk, rest = reply[:2000], reply[2000:]
        await interaction.followup.send(first_chunk)
        for i in range(0, len(rest), 2000):
            await interaction.channel.send(rest[i : i + 2000])

    @app_commands.command(
        name="forget_me", description="Efface ton historique de conversation avec l'IA"
    )
    async def forget_me(self, interaction: discord.Interaction):
        self.history.pop(str(interaction.user.id), None)
        _save_json(HISTORY_PATH, self.history)
        await interaction.response.send_message("🧹 Ton historique a été effacé.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AIChat(bot))

