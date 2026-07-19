import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta


def _is_role_too_high(actor: discord.Member, target: discord.Member) -> bool:
    """Empêche d'agir sur quelqu'un avec un rôle égal ou supérieur (sauf le propriétaire)."""
    if actor.id == actor.guild.owner_id:
        return False
    return target.top_role >= actor.top_role


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------- CLEAR ALL ----------

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

    # ---------- KICK ----------

    @app_commands.command(name="kick", description="Expulse un membre du serveur")
    @app_commands.describe(member="Le membre à expulser", reason="Raison (optionnelle)")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(
        self, interaction: discord.Interaction, member: discord.Member, reason: str = None
    ):
        if _is_role_too_high(interaction.user, member):
            await interaction.response.send_message(
                "❌ Tu ne peux pas expulser un membre avec un rôle égal ou supérieur au tien.",
                ephemeral=True,
            )
            return

        try:
            await member.kick(reason=reason or f"Expulsé par {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Je n'ai pas la permission d'expulser ce membre (son rôle est peut-être "
                "au-dessus du mien).",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"👢 **{member.display_name}** a été expulsé du serveur.\n"
            f"Raison : {reason or 'Non précisée'}"
        )

    # ---------- BAN ----------

    @app_commands.command(name="ban", description="Bannit un membre du serveur")
    @app_commands.describe(
        member="Le membre à bannir",
        reason="Raison (optionnelle)",
        delete_messages_days="Supprimer ses messages des X derniers jours (0-7, défaut 0)",
    )
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = None,
        delete_messages_days: app_commands.Range[int, 0, 7] = 0,
    ):
        if _is_role_too_high(interaction.user, member):
            await interaction.response.send_message(
                "❌ Tu ne peux pas bannir un membre avec un rôle égal ou supérieur au tien.",
                ephemeral=True,
            )
            return

        try:
            await member.ban(
                reason=reason or f"Banni par {interaction.user}",
                delete_message_seconds=delete_messages_days * 86400,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Je n'ai pas la permission de bannir ce membre (son rôle est peut-être "
                "au-dessus du mien).",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"🔨 **{member.display_name}** a été banni du serveur.\n"
            f"Raison : {reason or 'Non précisée'}"
        )

    # ---------- TIMEOUT (mute temporaire) ----------

    @app_commands.command(
        name="timeout", description="Mute temporairement un membre (timeout Discord)"
    )
    @app_commands.describe(
        member="Le membre à mute",
        duration_minutes="Durée en minutes (max 40320 = 28 jours)",
        reason="Raison (optionnelle)",
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration_minutes: app_commands.Range[int, 1, 40320],
        reason: str = None,
    ):
        if _is_role_too_high(interaction.user, member):
            await interaction.response.send_message(
                "❌ Tu ne peux pas mute un membre avec un rôle égal ou supérieur au tien.",
                ephemeral=True,
            )
            return

        try:
            await member.timeout(
                timedelta(minutes=duration_minutes), reason=reason or f"Mute par {interaction.user}"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Je n'ai pas la permission de mute ce membre.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"🔇 **{member.display_name}** est mute pendant **{duration_minutes} min**.\n"
            f"Raison : {reason or 'Non précisée'}"
        )

    @app_commands.command(name="untimeout", description="Retire le mute (timeout) d'un membre")
    @app_commands.describe(member="Le membre à démute")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member):
        try:
            await member.timeout(None, reason=f"Démute par {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Je n'ai pas la permission de démute ce membre.", ephemeral=True
            )
            return

        await interaction.response.send_message(f"🔊 **{member.display_name}** n'est plus mute.")

    # ---------- Gestion d'erreurs commune à toutes les commandes du cog ----------

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            message = "❌ Tu n'as pas la permission nécessaire pour utiliser cette commande."
        else:
            message = f"❌ Erreur : {error}"

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))

