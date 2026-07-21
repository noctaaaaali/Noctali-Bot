import os
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = (
    "Tu es Noctali Bot, l'assistant IA sympa et décontracté d'un serveur Discord communautaire. "
    "Réponds en français, de façon concise et naturelle, comme dans une vraie conversation Discord "
    "(pas de réponses trop longues ou trop formelles). "
    "Tu ne peux pas envoyer d'images ou de vrais memes toi-même : si on te demande un meme, "
    "dis simplement d'utiliser la commande /meme à la place, sans en inventer un en texte."
)

MAX_HISTORY = 6  # nombre de messages précédents gardés en mémoire, par salon


class AIChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.history: dict[int, list[dict]] = {}  # channel_id -> historique des messages

    async def _ask_groq(self, channel_id: int, question: str) -> str:
        if not GROQ_API_KEY:
            return "⚠️ Aucune clé `GROQ_API_KEY` configurée sur Railway."

        history = self.history.setdefault(channel_id, [])
        history.append({"role": "user", "content": question})
        del history[:-MAX_HISTORY]

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {"model": GROQ_MODEL, "messages": messages, "max_tokens": 500}

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
        del history[:-MAX_HISTORY]
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
            reply = await self._ask_groq(message.channel.id, question)

        for i in range(0, len(reply), 2000):
            await message.reply(reply[i:i + 2000], mention_author=False)

    @app_commands.command(name="ask", description="Pose une question à l'IA du bot")
    @app_commands.describe(question="Ta question")
    async def ask(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer()
        reply = await self._ask_groq(interaction.channel_id, question)

        first_chunk, rest = reply[:2000], reply[2000:]
        await interaction.followup.send(first_chunk)
        for i in range(0, len(rest), 2000):
            await interaction.channel.send(rest[i:i + 2000])


async def setup(bot: commands.Bot):
    await bot.add_cog(AIChat(bot))

