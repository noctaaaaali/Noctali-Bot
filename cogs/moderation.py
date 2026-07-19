import discord
from discord.ext import commands
from discord import app_commands


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="clear_all",
        description="Supprime TOUS les messages du salon (le salon lui-même est conservé)",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def clear_all(self, interaction: discord.Interaction):
        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Cette commande ne marche que dans un salon textuel classique.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        author_name = str(interaction.user)

        total_deleted = 0
        for _ in range(50):  # garde-fou : max ~10 000 messages
            deleted = await channel.purge(limit=200)
            total_deleted += len(deleted)
            if len(deleted) < 200:
                break

        await channel.send(
            f"✅ {total_deleted} message(s) supprimé(s) par **{author_name}**."
        )
        await interaction.followup.send(
            f"🧹 Nettoyage terminé — {total_deleted} message(s) supprimé(s).",
            ephemeral=True,
        )

    @clear_all.error
    async def clear_all_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            message = "❌ Tu dois être administrateur pour utiliser cette commande."
        else:
            message = f"❌ Erreur : {error}"

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
