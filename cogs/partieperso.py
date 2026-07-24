import os
import random
import discord
from discord.ext import commands
from discord import app_commands

# ID Discord de la seule personne autorisée à utiliser /partieperso.
# Clic droit sur ton propre pseudo (mode développeur activé) > Copier l'identifiant.
OWNER_ID = int(os.environ.get("PARTY_OWNER_ID", 0))

ROLES = ["Top", "Jungle", "Mid", "Adc", "Support"]
ROLE_EMOJIS = {"Top": "⚔️", "Jungle": "🌲", "Mid": "🔮", "Adc": "🏹", "Support": "🛡️"}
TEAM_EMOJIS = {"Bleue": "🔵", "Rouge": "🔴"}


class EditSelectView(discord.ui.View):
    """Vue éphémère (visible seulement par l'organisateur) pour déplacer un joueur
    vers une autre équipe/rôle. Échange automatiquement avec qui occupait la place."""

    def __init__(self, parent: "PartiePersoView"):
        super().__init__(timeout=120)
        self.parent = parent
        self.selected_player = None
        self.selected_team = None
        self.selected_role = None

        player_select = discord.ui.Select(
            placeholder="Joueur à déplacer",
            options=[
                discord.SelectOption(label=parent.names[uid], value=str(uid))
                for uid in parent.players
            ],
        )
        player_select.callback = self._on_player
        self.player_select = player_select
        self.add_item(player_select)

        team_select = discord.ui.Select(
            placeholder="Nouvelle équipe",
            options=[
                discord.SelectOption(label="Équipe Bleue", value="Bleue"),
                discord.SelectOption(label="Équipe Rouge", value="Rouge"),
            ],
        )
        team_select.callback = self._on_team
        self.team_select = team_select
        self.add_item(team_select)

        role_select = discord.ui.Select(
            placeholder="Nouveau rôle",
            options=[discord.SelectOption(label=r, value=r) for r in ROLES],
        )
        role_select.callback = self._on_role
        self.role_select = role_select
        self.add_item(role_select)

    async def _maybe_apply(self, interaction: discord.Interaction):
        if self.selected_player and self.selected_team and self.selected_role:
            await self._apply(interaction)
        else:
            await interaction.response.defer()

    async def _on_player(self, interaction: discord.Interaction):
        self.selected_player = int(self.player_select.values[0])
        await self._maybe_apply(interaction)

    async def _on_team(self, interaction: discord.Interaction):
        self.selected_team = self.team_select.values[0]
        await self._maybe_apply(interaction)

    async def _on_role(self, interaction: discord.Interaction):
        self.selected_role = self.role_select.values[0]
        await self._maybe_apply(interaction)

    async def _apply(self, interaction: discord.Interaction):
        teams = self.parent.teams

        old_team = old_role = None
        for team_name, roster in teams.items():
            for role, uid in roster.items():
                if uid == self.selected_player:
                    old_team, old_role = team_name, role

        target_roster = teams[self.selected_team]
        displaced_uid = target_roster.get(self.selected_role)

        target_roster[self.selected_role] = self.selected_player
        if old_team and old_role and (old_team, old_role) != (self.selected_team, self.selected_role):
            if displaced_uid is not None and displaced_uid != self.selected_player:
                teams[old_team][old_role] = displaced_uid
            else:
                del teams[old_team][old_role]

        await self.parent.message.edit(embed=self.parent.build_embed())
        await interaction.response.send_message("✅ Modifié !", ephemeral=True)
        self.stop()


class RemovePlayerSelectView(discord.ui.View):
    """Vue éphémère (organisateur uniquement) pour retirer un joueur inscrit,
    ex. quelqu'un devenu inactif/indisponible avant que les équipes soient faites."""

    def __init__(self, parent: "PartiePersoView"):
        super().__init__(timeout=60)
        self.parent = parent
        select = discord.ui.Select(
            placeholder="Joueur à retirer",
            options=[
                discord.SelectOption(label=parent.names[uid], value=str(uid))
                for uid in parent.players
            ],
        )
        select.callback = self._on_select
        self.add_item(select)

    async def _on_select(self, interaction: discord.Interaction):
        uid = int(self.children[0].values[0])
        name = self.parent.names.get(uid, "Ce joueur")
        if uid in self.parent.players:
            self.parent.players.remove(uid)

        await self.parent.message.edit(embed=self.parent.build_embed())
        await interaction.response.send_message(f"🚫 {name} a été retiré de la liste.", ephemeral=True)
        self.stop()


class PartiePersoView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.players: list[int] = []
        self.names: dict[int, str] = {}
        self.teams: dict | None = None
        self.message: discord.Message | None = None

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🎮 Partie perso League of Legends",
            description=(
                "Clique sur **S'inscrire** pour rejoindre la partie (10 places).\n"
                "**Règles :** bans interdits pour la 1ère game."
            ),
            color=discord.Color.blue(),
        )

        if not self.teams:
            joueurs_txt = (
                "\n".join(f"{i + 1}. {self.names[uid]}" for i, uid in enumerate(self.players))
                or "Personne pour l'instant"
            )
            embed.add_field(name=f"📋 Inscrits ({len(self.players)}/10)", value=joueurs_txt, inline=False)
        else:
            for team_name, roster in self.teams.items():
                lines = [
                    f"{ROLE_EMOJIS[role]} **{role}** — {self.names[uid]}"
                    for role, uid in roster.items()
                ]
                embed.add_field(
                    name=f"{TEAM_EMOJIS[team_name]} Équipe {team_name}",
                    value="\n".join(lines) or "—",
                    inline=True,
                )

        return embed

    @discord.ui.button(label="S'inscrire / Se désinscrire", style=discord.ButtonStyle.success)
    async def signup(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.teams:
            await interaction.response.send_message(
                "❌ Les équipes ont déjà été faites, inscriptions closes.", ephemeral=True
            )
            return

        uid = interaction.user.id
        if uid in self.players:
            self.players.remove(uid)
            await interaction.response.send_message("Tu t'es désinscrit.", ephemeral=True)
        else:
            if len(self.players) >= 10:
                await interaction.response.send_message("❌ Complet (10/10).", ephemeral=True)
                return
            self.players.append(uid)
            self.names[uid] = interaction.user.display_name
            await interaction.response.send_message("Tu es inscrit !", ephemeral=True)

        await self.message.edit(embed=self.build_embed())

    @discord.ui.button(label="🚫 Retirer un joueur", style=discord.ButtonStyle.danger)
    async def remove_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Seul l'organisateur peut faire ça.", ephemeral=True
            )
            return
        if self.teams:
            await interaction.response.send_message(
                "❌ Les équipes sont déjà faites, utilise plutôt « Modifier équipe/rôle ».",
                ephemeral=True,
            )
            return
        if not self.players:
            await interaction.response.send_message("❌ Personne à retirer pour l'instant.", ephemeral=True)
            return

        await interaction.response.send_message(
            "Choisis qui retirer (ex. quelqu'un devenu inactif/indisponible) :",
            view=RemovePlayerSelectView(self),
            ephemeral=True,
        )

    @discord.ui.button(label="🎲 Faire les équipes et rôles", style=discord.ButtonStyle.primary)
    async def generate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Seul l'organisateur peut faire ça.", ephemeral=True
            )
            return
        if len(self.players) < 10:
            await interaction.response.send_message(
                f"❌ Il faut 10 joueurs ({len(self.players)}/10 pour l'instant).", ephemeral=True
            )
            return

        shuffled = self.players.copy()
        random.shuffle(shuffled)
        team_blue, team_red = shuffled[:5], shuffled[5:]
        random.shuffle(team_blue)
        random.shuffle(team_red)

        self.teams = {
            "Bleue": dict(zip(ROLES, team_blue)),
            "Rouge": dict(zip(ROLES, team_red)),
        }

        await interaction.response.send_message("✅ Équipes générées !", ephemeral=True)
        await self.message.edit(embed=self.build_embed())

    @discord.ui.button(label="✏️ Modifier équipe/rôle", style=discord.ButtonStyle.secondary)
    async def edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Seul l'organisateur peut modifier.", ephemeral=True
            )
            return
        if not self.teams:
            await interaction.response.send_message(
                "❌ Génère d'abord les équipes.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            "Choisis le joueur, sa nouvelle équipe et son nouveau rôle "
            "(les 3 doivent être sélectionnés) :",
            view=EditSelectView(self),
            ephemeral=True,
        )


class PartiePerso(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="partieperso", description="Organise une partie perso LoL (inscriptions, équipes, rôles)"
    )
    async def partieperso(self, interaction: discord.Interaction):
        if OWNER_ID and interaction.user.id != OWNER_ID:
            await interaction.response.send_message(
                "❌ Seul l'organisateur du serveur peut lancer cette commande.", ephemeral=True
            )
            return

        view = PartiePersoView(owner_id=interaction.user.id)
        await interaction.response.send_message(embed=view.build_embed(), view=view)
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot):
    await bot.add_cog(PartiePerso(bot))

