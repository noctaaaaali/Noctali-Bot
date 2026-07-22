import random
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands

# API publique et gratuite d'Imgflip : renvoie les ~100 templates de memes
# les plus utilisés/connus (Drake, Distracted Boyfriend, Woman Yelling at Cat,
# Change My Mind, etc.) — mêmes bases que dans le jeu "Make It Meme".
IMGFLIP_MEMES_URL = "https://api.imgflip.com/get_memes"


class Memes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cache = []  # mis en cache après le 1er appel, la liste bouge très peu

    async def _get_templates(self):
        if self._cache:
            return self._cache

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(IMGFLIP_MEMES_URL, timeout=10) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
        except Exception:
            return []

        if data.get("success"):
            self._cache = data["data"]["memes"]

        return self._cache

    @app_commands.command(name="meme", description="Envoie un meme culte et connu")
    async def meme(self, interaction: discord.Interaction):
        await interaction.response.defer()

        templates = await self._get_templates()
        if not templates:
            await interaction.followup.send("❌ Pas réussi à récupérer un meme, réessaie.")
            return

        template = random.choice(templates)
        embed = discord.Embed(title=template["name"], color=discord.Color.orange())
        embed.set_image(url=template["url"])
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Memes(bot))

