import os
import asyncio
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select, UserSelect

TRIGGER_CHANNEL_ID = 1459721784386523206
CATEGORY_ID = 1459692616076624087

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

voice_owners = {}

def is_owner():
    async def predicate(interaction: discord.Interaction):
        channel_id = interaction.channel_id
        owner_id = voice_owners.get(channel_id)
        if owner_id == interaction.user.id:
            return True
        await interaction.response.send_message("❌ 只有此包廂的房主才能使用此選單！", ephemeral=True)
        return False
    return discord.app_commands.check(predicate)

class NameModal(Modal, title="修改頻道名稱"):
    channel_name = TextInput(label="新頻道名稱", placeholder="輸入新的語音頻道名稱...", max_length=100)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.channel.edit(name=self.channel_name.value)
        await interaction.response.send_message(f"✅ 頻道名稱已修改為：**{self.channel_name.value}**", ephemeral=True)

class LimitModal(Modal, title="設定人數限制"):
    user_limit = TextInput(label="人數限制 (0 為無限制，上限 99)", placeholder="0", max_length=2)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            limit = int(self.user_limit.value)
            if 0 <= limit <= 99:
                await interaction.channel.edit(user_limit=limit)
                await interaction.response.send_message(f"✅ 人數限制已設定為：**{limit if limit > 0 else '無限制'}**", ephemeral=True)
            else:
                await interaction.response.send_message("❌ 請輸入 0 到 99 之間的數字！", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ 請輸入有效的數字！", ephemeral=True)

class StatusModal(Modal, title="設定頻道狀態"):
    status_text = TextInput(label="頻道狀態", placeholder="輸入目前的狀態文字...", max_length=50)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.channel.edit(status=self.status_text.value)
        await interaction.response.send_message(f"✅ 頻道狀態已更新為：**{self.status_text.value}**", ephemeral=True)

class BitrateModal(Modal, title="調整音質 (Bitrate)"):
    bitrate_kbps = TextInput(label="位元率 (kbps, 預設 64, 最高 96/128/256/384)", placeholder="64", max_length=3)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            bitrate_value = int(self.bitrate_kbps.value) * 1000
            max_bitrate = interaction.guild.bitrate_limit
            if 8000 <= bitrate_value <= max_bitrate:
                await interaction.channel.edit(bitrate=bitrate_value)
                await interaction.response.send_message(f"✅ 頻道音質已設定為：**{self.bitrate_kbps.value} kbps**", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ 請輸入 8 到 {int(max_bitrate/1000)} kbps 之間的數字！", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ 請輸入有效的數字！", ephemeral=True)

class UserSelectMenu(UserSelect):
    def __init__(self, action_type: str, owner_id: int):
        super().__init__(placeholder="請選擇成員...", min_values=1, max_values=1)
        self.action_type = action_type
        self.owner_id = owner_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message("❌ 只有房主可以使用此選單！", ephemeral=True)

        target_member = self.values[0]
        channel = interaction.channel

        if self.action_type == "permit":
            await channel.set_permissions(target_member, connect=True, view_channel=True)
            await interaction.response.send_message(f"✅ 已允許 {target_member.mention} 加入與查看頻道。", ephemeral=True)

        elif self.action_type == "reject":
            await channel.set_permissions(target_member, connect=False)
            if target_member in channel.members:
                await target_member.move_to(None)
            await interaction.response.send_message(f"🚫 已封鎖並踢出 {target_member.mention}。", ephemeral=True)

        elif self.action_type == "invite":
            await interaction.response.send_message(f"📩 {target_member.mention}，房主 {interaction.user.mention} 邀請你加入頻道：{channel.mention}")

        elif self.action_type == "transfer":
            voice_owners[channel.id] = target_member.id
            await channel.set_permissions(target_member, manage_channels=True, move_members=True)
            await channel.set_permissions(interaction.user, overwrite=None)
            await interaction.response.send_message(f"👑 房主權限已轉移給 {target_member.mention}！")

class UserSelectView(View):
    def __init__(self, action_type: str, owner_id: int):
        super().__init__(timeout=60)
        self.add_item(UserSelectMenu(action_type=action_type, owner_id=owner_id))

class ChannelSettingsSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Name", description="Change the channel name", emoji="✏️", value="name"),
            discord.SelectOption(label="Limit", description="Change the channel limit", emoji="👥", value="limit"),
            discord.SelectOption(label="Status", description="Change the channel status", emoji="💬", value="status"),
            discord.SelectOption(label="Game", description="Change the channel name to the game you're playing", emoji="🎮", value="game"),
            discord.SelectOption(label="LFM", description="Post a message to the LFM channel to let others know you're looking for members", emoji="🔍", value="lfm"),
            discord.SelectOption(label="Bitrate", description="Change the channel bitrate", emoji="🎛️", value="bitrate"),
            discord.SelectOption(label="Region", description="Change the channel voice region", emoji="🌐", value="region"),
            discord.SelectOption(label="Text", description="Create a temporary text channel", emoji="💬", value="text"),
            discord.SelectOption(label="NSFW", description="Set your temporary channel to NSFW", emoji="⚠️", value="nsfw"),
            discord.SelectOption(label="Claim", description="Claim ownership of the channel", emoji="👑", value="claim"),
        ]
        super().__init__(placeholder="⚙️ 頻道設定 (Channel Settings)", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        owner_id = voice_owners.get(channel.id)

        if self.values[0] == "claim":
            if owner_id in [m.id for m in channel.members]:
                return await interaction.response.send_message("❌ 原房主仍在此頻道中，無法轉移所有權！", ephemeral=True)
            voice_owners[channel.id] = interaction.user.id
            await interaction.response.send_message(f"👑 {interaction.user.mention} 已成功轉移並成為此包廂的新房主！")
            return

        if interaction.user.id != owner_id:
            return await interaction.response.send_message("❌ 只有此包廂的房主才能進行設定！", ephemeral=True)

        selected = self.values[0]
        if selected == "name":
            await interaction.response.send_modal(NameModal())
        elif selected == "limit":
            await interaction.response.send_modal(LimitModal())
        elif selected == "status":
            await interaction.response.send_modal(StatusModal())
        elif selected == "game":
            game_activity = next((act.name for act in interaction.user.activities if act.type == discord.ActivityType.playing), None)
            if game_activity:
                await channel.edit(name=f"🎮 {game_activity}")
                await interaction.response.send_message(f"✅ 頻道名稱已自動變更為遊戲名稱：**{game_activity}**", ephemeral=True)
            else:
                await interaction.response.send_message("❌ 偵測不到你目前正在遊玩的遊戲狀態！", ephemeral=True)
        elif selected == "lfm":
            await interaction.response.send_message(f"📢 **【組隊尋人】** {interaction.user.mention} 正在包廂 {channel.mention} 尋找隊友！歡迎加入！")
        elif selected == "bitrate":
            await interaction.response.send_modal(BitrateModal())
        elif selected == "region":
            await interaction.response.send_message("ℹ️ 目前伺服器由 Discord 自動指派最佳語音區域。", ephemeral=True)
        elif selected == "text":
            text_channel = await interaction.guild.create_text_channel(name=f"💬-{channel.name}", category=channel.category)
            await interaction.response.send_message(f"✅ 已為您建立專屬文字頻道：{text_channel.mention}", ephemeral=True)
        elif selected == "nsfw":
            is_nsfw = not channel.nsfw
            await channel.edit(nsfw=is_nsfw)
            status_msg = "已開啟 (NSFW)" if is_nsfw else "已關閉 (SFW)"
            await interaction.response.send_message(f"✅ 頻道分級已更新為：**{status_msg}**", ephemeral=True)

class ChannelPermissionsSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Lock", description="Lock the channel", emoji="🔒", value="lock"),
            discord.SelectOption(label="Unlock", description="Unlock the channel", emoji="🔓", value="unlock"),
            discord.SelectOption(label="Permit", description="Permit users/roles to access the channel", emoji="👤", value="permit"),
            discord.SelectOption(label="Reject", description="Reject/kick users/roles from accessing the channel", emoji="👤", value="reject"),
            discord.SelectOption(label="Invite", description="Invite a user to access the channel", emoji="👥", value="invite"),
            discord.SelectOption(label="Ghost", description="Make your channel invisible", emoji="🙈", value="ghost"),
            discord.SelectOption(label="Unhost", description="Make your channel visible", emoji="👁️", value="unghost"),
            discord.SelectOption(label="Transfer", description="Transfer ownership to another user", emoji="👑", value="transfer"),
        ]
        super().__init__(placeholder="🔒 頻道權限 (Channel Permissions)", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        owner_id = voice_owners.get(channel.id)

        if interaction.user.id != owner_id:
            return await interaction.response.send_message("❌ 只有此包廂的房主才能設定權限！", ephemeral=True)

        selected = self.values[0]
        guild = interaction.guild

        if selected == "lock":
            await channel.set_permissions(guild.default_role, connect=False)
            await interaction.response.send_message("🔒 頻道已上鎖，其他成員無法隨意加入。", ephemeral=True)
        elif selected == "unlock":
            await channel.set_permissions(guild.default_role, connect=None)
            await interaction.response.send_message("🔓 頻道已解鎖，所有成員皆可加入。", ephemeral=True)
        elif selected == "ghost":
            await channel.set_permissions(guild.default_role, view_channel=False)
            await interaction.response.send_message("🙈 頻道已隱藏 (Ghost Mode)。", ephemeral=True)
        elif selected == "unghost":
            await channel.set_permissions(guild.default_role, view_channel=None)
            await interaction.response.send_message("👁️ 頻道已解除隱藏，公開顯示。", ephemeral=True)
        elif selected in ["permit", "reject", "invite", "transfer"]:
            view = UserSelectView(action_type=selected, owner_id=owner_id)
            await interaction.response.send_message(f"請選擇要進行 **{selected.upper()}** 操作的成員：", view=view, ephemeral=True)

class ControlPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ChannelSettingsSelect())
        self.add_item(ChannelPermissionsSelect())

@bot.event
async def on_ready():
    print(f"機器人已成功登入為 {bot.user}")

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if after.channel and after.channel.id == TRIGGER_CHANNEL_ID:
        guild = member.guild
        category = guild.get_channel(CATEGORY_ID)

        if not category or not isinstance(category, discord.CategoryChannel):
            return

        new_channel = await guild.create_voice_channel(
            name=f"{member.display_name} 的包廂",
            category=category,
            position=len(category.channels)
        )

        voice_owners[new_channel.id] = member.id

        await member.move_to(new_channel)

        embed = discord.Embed(
            title="🎤 歡迎來到你的獨立語音頻道！",
            description=(
                f"你好 {member.mention}！這是專屬於你的私人語音空間。\n"
                "你可以透過下方選單輕鬆管理你的頻道名稱、人數限制、進出權限等設定。\n\n"
                "**📌 快捷選單說明：**\n"
                "🔹 **頻道設定 (Channel Settings)**：修改名稱、人數上限、狀態、遊戲主題、音質等。\n"
                "🔹 **頻道權限 (Channel Permissions)**：鎖定頻道、隱藏頻道、允許/踢出指定成員、轉移房主等。"
            ),
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="提示：當所有人離開頻道後，系統將會自動清理此空間。")

        view = ControlPanelView()
        await new_channel.send(embed=embed, view=view)

    if before.channel and before.channel.category_id == CATEGORY_ID:
        if before.channel.id != TRIGGER_CHANNEL_ID:
            if len(before.channel.members) == 0:
                channel_id = before.channel.id
                try:
                    await before.channel.delete()
                    if channel_id in voice_owners:
                        del voice_owners[channel_id]
                except discord.NotFound:
                    pass

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("Error: DISCORD_TOKEN Environment Variable is missing.")
