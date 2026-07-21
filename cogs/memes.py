import random
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands

# API dédiée qui va chercher les memes sur Reddit de son côté (évite le blocage
# que Reddit applique aux requêtes automatisées venant de serveurs cloud comme Railway).
MEME_API_BASE = "https://meme-api.com/gimme"
HEADERS = {"User-Agent": "NoctaliBot/1.0 (Discord bot)"}

# Sous-reddits ciblés, piochés une partie du temps pour varier les thèmes
# (Simpsons, gaming, historique...) en plus du pool général de l'API.
SUBREDDITS = [
    "memes",
    "dankmemes",
    "wholesomememes",
    "ProgrammerHumor",
    "funny",
    "me_irl",
    "meirl",
    "AdviceAnimals",
    "terriblefacebookmemes",
    "SimpsonsShitposting",
    "HistoryMemes",
    "gamingmemes",
    "Animemes",
    "MarvelMemes",
    "comedyheaven",
    "BlackPeopleTwitter",
    "whitepeopletwitter",
    "ComedyCemetery",
    "shitposting",
    "cursedcomments",
    "surrealmemes",
]


class Memes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _fetch_meme(self):
        # 1 fois sur 3 : sous-reddit ciblé (pour varier les thèmes précis)
        # sinon : pool général de l'API (déjà large et "tendance")
        if random.random() < 0.35:
            url = f"{MEME_API_BASE}/{random.choice(SUBREDDITS)}"
        else:
            url = MEME_API_BASE

        try:
            async with aiohttp.ClientSession(headers=HEADERS) as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
        except Exception:
            return None

        if not data or data.get("nsfw") or data.get("code"):
            return None

        return data

    @app_commands.command(name="meme", description="Envoie un meme random")
    async def meme(self, interaction: discord.Interaction):
        await interaction.response.defer()

        post = None
        for _ in range(4):
            post = await self._fetch_meme()
            if post:
                break

        if not post:
            await interaction.followup.send(
                "❌ Pas réussi à trouver un meme, réessaie dans quelques secondes."
            )
            return

        embed = discord.Embed(title=post.get("title", "Meme"), color=discord.Color.orange())
        embed.set_image(url=post["url"])
        embed.set_footer(text=f"r/{post.get('subreddit', '?')} • 👍 {post.get('ups', 0)}")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Memes(bot))

