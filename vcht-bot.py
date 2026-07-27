import os
import asyncio
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select, UserSelect

TRIGGER_CHANNEL_ID = 1530974075902759083
CATEGORY_ID = 1459692616076624087
STAFF_ROLE_ID = 1459696673239470338

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

voice_owners = {}

# --- 選單標題專用 Emoji ---
E_MENU_SETTINGS = discord.PartialEmoji(name="menu_settings", id=1531236010413920276) # 藍色齒輪

# --- 18 個選項 Emoji (藍色鎖頭歸位至 E_11 上鎖頻道，其餘精準對齊) ---
E_01 = discord.PartialEmoji(name="e01", id=1531235954893783070) # 修改名稱
E_02 = discord.PartialEmoji(name="e02", id=1531235983956377742) # 人數限制
E_03 = discord.PartialEmoji(name="e03", id=1531236041736978563) # 頻道狀態
E_04 = discord.PartialEmoji(name="e04", id=1531236073768751235) # 遊戲主題
E_05 = discord.PartialEmoji(name="e05", id=1531236105914159154) # 組隊尋人
E_06 = discord.PartialEmoji(name="e06", id=1531236135202848938) # 調整音質
E_07 = discord.PartialEmoji(name="e07", id=1531236162763620422) # 語音區域
E_08 = discord.PartialEmoji(name="e08", id=1531236193503547565) # 專屬文字房
E_09 = discord.PartialEmoji(name="e09", id=1531236231122391133) # 年齡分級
E_10 = discord.PartialEmoji(name="e10", id=1531237058662633492) # 聲明/接管房主
E_11 = discord.PartialEmoji(name="e11", id=1531236263338709093) # 上鎖頻道 (藍色鎖頭)
E_12 = discord.PartialEmoji(name="e12", id=1531237091264954418) # 解鎖頻道
E_13 = discord.PartialEmoji(name="e13", id=1531237123514961931) # 允許成員
E_14 = discord.PartialEmoji(name="e14", id=1531237152736678089) # 踢出/封鎖
E_15 = discord.PartialEmoji(name="e15", id=1531237201780805723) # 邀請成員
E_16 = discord.PartialEmoji(name="e16", id=1531237291639439492) # 隱藏頻道
E_17 = discord.PartialEmoji(name="e17", id=1531237228905496826) # 取消隱藏
E_18 = discord.PartialEmoji(name="e18", id=1531237261205573654) # 讓渡房主


def is_authorized(member: discord.Member, channel_id: int) -> bool:
    owner_id = voice_owners.get(channel_id)
    if member.id == owner_id:
        return True
    if member.guild_permissions.manage_channels:
        return True
    if any(role.id == STAFF_ROLE_ID for role in member.roles):
        return True
    return False


class DeleteTextChannelView(View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    @discord.ui.button(label="刪除頻道", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_channel(self, interaction: discord.Interaction, button: Button):
        if not is_authorized(interaction.user, interaction.channel.id) and interaction.user.id != self.owner_id:
            return await interaction.response.send_message("❌ 只有房主或管理人員才能刪除此文字頻道！", ephemeral=True)
        
        await interaction.response.send_message("🗑️ 專屬文字頻道即將刪除...", ephemeral=True)
        await asyncio.sleep(1)
        await interaction.channel.delete()


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


class BitrateModal(Modal, title="調整音質 (位元率)"):
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
        if not is_authorized(interaction.user, interaction.channel.id):
            return await interaction.response.send_message("❌ 只有房主或管理人員可以使用此選單！", ephemeral=True)

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
            await interaction.response.send_message(f"📩 {target_member.mention}，{interaction.user.mention} 邀請你加入頻道：{channel.mention}")

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
            discord.SelectOption(label="修改名稱", description="變更語音頻道的名稱", emoji=E_01, value="name"),
            discord.SelectOption(label="人數限制", description="設定頻道的最大容納人數", emoji=E_02, value="limit"),
            discord.SelectOption(label="頻道狀態", description="設定頻道的自訂狀態文字", emoji=E_03, value="status"),
            discord.SelectOption(label="遊戲主題", description="自動將頻道名稱改為你正在玩的遊戲", emoji=E_04, value="game"),
            discord.SelectOption(label="組隊尋人", description="發送尋找隊友的訊息通知", emoji=E_05, value="lfm"),
            discord.SelectOption(label="調整音質", description="修改頻道的位元率 (Bitrate)", emoji=E_06, value="bitrate"),
            discord.SelectOption(label="語音區域", description="查看語音伺服器區域資訊", emoji=E_07, value="region"),
            discord.SelectOption(label="專屬文字房", description="建立臨時的專屬文字頻道", emoji=E_08, value="text"),
            discord.SelectOption(label="年齡分級", description="切換頻道的 NSFW (限制級) 狀態", emoji=E_09, value="nsfw"),
            discord.SelectOption(label="聲明房主", description="接管目前無人管理的頻道房主權限", emoji=E_10, value="claim"),
        ]
        # 使用藍色齒輪作為 Placeholder 前綴選單名稱
        super().__init__(placeholder="⚙️ 頻道設定 (Channel Settings)", min_values=1, max_values=1, options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        owner_id = voice_owners.get(channel.id)

        if self.values[0] == "claim":
            if owner_id in [m.id for m in channel.members]:
                return await interaction.response.send_message("❌ 原房主仍在此頻道中，無法轉移所有權！", ephemeral=True)
            voice_owners[channel.id] = interaction.user.id
            await interaction.response.send_message(f"👑 {interaction.user.mention} 已成功轉移並成為此包廂的新房主！")
            return

        if not is_authorized(interaction.user, channel.id):
            return await interaction.response.send_message("❌ 只有房主或管理人員才能進行設定！", ephemeral=True)

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
            staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            for member in channel.members:
                overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            text_channel = await interaction.guild.create_text_channel(
                name=f"💬-{channel.name}",
                category=channel.category,
                overwrites=overwrites
            )

            welcome_embed = discord.Embed(
                title=f"💬 {channel.name} - 專屬討論空間",
                description=(
                    f"歡迎來到專屬文字頻道 {text_channel.mention}！\n\n"
                    "📌 **說明：**\n"
                    "• 此頻道為此語音包廂的臨時文字討論區。\n"
                    "• 點擊下方按鈕可由房主或管理員隨時手動刪除此文字頻道。"
                ),
                color=discord.Color.green()
            )
            welcome_embed.set_footer(text=f"房主：{interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

            delete_view = DeleteTextChannelView(owner_id=interaction.user.id)
            await text_channel.send(embed=welcome_embed, view=delete_view)

            await interaction.response.send_message(f"✅ 已為您建立專屬文字頻道：{text_channel.mention}", ephemeral=True)

        elif selected == "nsfw":
            is_nsfw = not channel.nsfw
            await channel.edit(nsfw=is_nsfw)
            status_msg = "已開啟 (NSFW)" if is_nsfw else "已關閉 (SFW)"
            await interaction.response.send_message(f"✅ 頻道分級已更新為：**{status_msg}**", ephemeral=True)


class ChannelPermissionsSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="上鎖頻道", description="上鎖頻道，禁止其他成員隨意加入", emoji=E_11, value="lock"), # 藍色鎖頭
            discord.SelectOption(label="解鎖頻道", description="解鎖頻道，允許所有人加入", emoji=E_12, value="unlock"),
            discord.SelectOption(label="允許成員", description="允許指定成員查看與加入頻道", emoji=E_13, value="permit"),
            discord.SelectOption(label="踢出/封鎖", description="封鎖指定成員並將其踢出頻道", emoji=E_14, value="reject"),
            discord.SelectOption(label="邀請成員", description="發送邀請給指定成員加入頻道", emoji=E_15, value="invite"),
            discord.SelectOption(label="隱藏頻道", description="讓頻道對其他人不可見 (隱身模式)", emoji=E_16, value="ghost"),
            discord.SelectOption(label="取消隱藏", description="讓頻道恢復公開顯示", emoji=E_17, value="unghost"),
            discord.SelectOption(label="讓渡房主", description="將房主管理權限轉移給其他成員", emoji=E_18, value="transfer"),
        ]
        # 頻道權限選單標題使用原版 🔒 Emoji
        super().__init__(placeholder="🔒 頻道權限 (Channel Permissions)", min_values=1, max_values=1, options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        owner_id = voice_owners.get(channel.id)

        if not is_authorized(interaction.user, channel.id):
            return await interaction.response.send_message("❌ 只有房主或管理人員才能設定權限！", ephemeral=True)

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
            await interaction.response.send_message("👻 頻道已隱藏 (隱身模式)。", ephemeral=True)
        elif selected == "unghost":
            await channel.set_permissions(guild.default_role, view_channel=None)
            await interaction.response.send_message("⭕ 頻道已解除隱藏，公開顯示。", ephemeral=True)
        elif selected in ["permit", "reject", "invite", "transfer"]:
            action_names = {
                "permit": "允許成員",
                "reject": "踢出/封鎖",
                "invite": "邀請成員",
                "transfer": "讓渡房主"
            }
            view = UserSelectView(action_type=selected, owner_id=owner_id)
            await interaction.response.send_message(f"請選擇要進行 **{action_names[selected]}** 操作的成員：", view=view, ephemeral=True)


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
            title="🎤 語音包廂管理控制面板",
            description=(
                f"歡迎 {member.mention}！使用下方選單調整頻道設定：\n"
                "───────────────────────────\n"
                "**Channel Settings**\n\n"
                "───────────────────────────\n"
                "**Channel Permissions**"
            ),
            color=discord.Color.from_rgb(47, 49, 54)
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="提示：所有人離開頻道後，系統將自動清理此空間。")

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
        print("錯誤：找不到 DISCORD_TOKEN 環境變數。")
