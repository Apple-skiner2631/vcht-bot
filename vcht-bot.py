import os
import asyncio
import discord
from discord.ext import commands
from discord.ui import View, Modal, TextInput, Select, UserSelect

TRIGGER_CHANNEL_ID = 1530970371862298706
CATEGORY_ID = 1459692616076624087

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

voice_owners = {}

class NameModal(Modal, title="✏️ 修改頻道名稱"):
    channel_name = TextInput(
        label="新頻道名稱",
        placeholder="請輸入欲變更的頻道名稱...",
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.channel.edit(name=self.channel_name.value)
        embed = discord.Embed(
            description=f"✨ **頻道名稱已成功修改為：** `{self.channel_name.value}`",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class LimitModal(Modal, title="👥 設定人數限制"):
    user_limit = TextInput(
        label="人數限制 ( 0 為無限制，最高 99 人 )",
        placeholder="例如：0 或 5",
        max_length=2
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            limit = int(self.user_limit.value)
            if 0 <= limit <= 99:
                await interaction.channel.edit(user_limit=limit)
                status_str = "無限制" if limit == 0 else f"{limit} 人"
                embed = discord.Embed(
                    description=f"✨ **頻道人數上限已更新為：** `{status_str}`",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    description="⚠️ **請輸入介於 0 至 99 之間的數字！**",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except ValueError:
            embed = discord.Embed(
                description="⚠️ **請輸入有效的純數字格式！**",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class StatusModal(Modal, title="💬 設定頻道動態狀態"):
    status_text = TextInput(
        label="頻道狀態內容",
        placeholder="例如：聊天中 / 打瓦...",
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.channel.edit(status=self.status_text.value)
        embed = discord.Embed(
            description=f"✨ **頻道狀態已更新為：** `{self.status_text.value}`",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class BitrateModal(Modal, title="🎛️ 調整頻道音質 (Bitrate)"):
    bitrate_kbps = TextInput(
        label="位元率 kbps ( 預設 64，最高依伺服器加成等級限制 )",
        placeholder="例如：64、96 或 128",
        max_length=3
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            bitrate_value = int(self.bitrate_kbps.value) * 1000
            max_bitrate = interaction.guild.bitrate_limit
            if 8000 <= bitrate_value <= max_bitrate:
                await interaction.channel.edit(bitrate=bitrate_value)
                embed = discord.Embed(
                    description=f"✨ **頻道音質已成功調整為：** `{self.bitrate_kbps.value} kbps`",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                max_kbps = int(max_bitrate / 1000)
                embed = discord.Embed(
                    description=f"⚠️ **音質範圍必須介於 8 至 {max_kbps} kbps 之間！**",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except ValueError:
            embed = discord.Embed(
                description="⚠️ **請輸入有效的純數字格式！**",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class UserSelectMenu(UserSelect):
    def __init__(self, action_type: str, owner_id: int):
        super().__init__(placeholder="🔍 請選擇欲設定的伺服器成員...", min_values=1, max_values=1)
        self.action_type = action_type
        self.owner_id = owner_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            embed = discord.Embed(description="❌ **僅有此包廂的房主有權使用此選單！**", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        target_member = self.values[0]
        channel = interaction.channel

        if self.action_type == "permit":
            await channel.set_permissions(target_member, connect=True, view_channel=True)
            embed = discord.Embed(
                description=f"✅ **已授予存取權利：** {target_member.mention} 現在可以自由進入並查看本包廂。",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif self.action_type == "reject":
            await channel.set_permissions(target_member, connect=False)
            if target_member in channel.members:
                await target_member.move_to(None)
            embed = discord.Embed(
                description=f"🚫 **已封鎖並移除成員：** {target_member.mention} 已被禁止進入本包廂。",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif self.action_type == "invite":
            embed = discord.Embed(
                title="✉️ 語音包廂邀請通知",
                description=f"🎉 {target_member.mention}，房主 {interaction.user.mention} 邀請你加入私人包廂！\n👉 **點擊連結加入：** {channel.mention}",
                color=discord.Color.gold()
            )
            await interaction.response.send_message(content=target_member.mention, embed=embed)

        elif self.action_type == "transfer":
            voice_owners[channel.id] = target_member.id
            await channel.set_permissions(target_member, manage_channels=True, move_members=True)
            await channel.set_permissions(interaction.user, overwrite=None)
            embed = discord.Embed(
                title="👑 房主權限轉移公告",
                description=f"原房主 {interaction.user.mention} 已將包廂管理權限移交給 {target_member.mention}！",
                color=discord.Color.gold()
            )
            await interaction.response.send_message(embed=embed)

class UserSelectView(View):
    def __init__(self, action_type: str, owner_id: int):
        super().__init__(timeout=60)
        self.add_item(UserSelectMenu(action_type=action_type, owner_id=owner_id))

class ChannelSettingsSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="名稱設定 (Name)", description="修改此語音頻道的有名名稱", emoji="✏️", value="name"),
            discord.SelectOption(label="人數限制 (Limit)", description="設定可進入包廂的最大人數", emoji="👥", value="limit"),
            discord.SelectOption(label="頻道狀態 (Status)", description="自訂廣播頻道側邊顯示的狀態文字", emoji="💬", value="status"),
            discord.SelectOption(label="遊戲主題 (Game)", description="根據你正在遊玩的遊戲自動修改房名", emoji="🎮", value="game"),
            discord.SelectOption(label="組隊尋人 (LFM)", description="在包廂發送公開邀請徵求隊友", emoji="🔍", value="lfm"),
            discord.SelectOption(label="音質調整 (Bitrate)", description="設定語音位元率以提升音質體驗", emoji="🎛️", value="bitrate"),
            discord.SelectOption(label="語音區域 (Region)", description="檢視當前包廂語音區域資訊", emoji="🌐", value="region"),
            discord.SelectOption(label="專屬文字 (Text)", description="建立此包廂獨立的臨時文字討論頻道", emoji="📝", value="text"),
            discord.SelectOption(label="分級切換 (NSFW)", description="開啟或關閉本包廂的成人內容限制", emoji="⚠️", value="nsfw"),
            discord.SelectOption(label="接管房主 (Claim)", description="當房主離線或離開時接管包廂所有權", emoji="👑", value="claim"),
        ]
        super().__init__(placeholder="⚙️ 頻道基本設定選單 (Channel Settings)", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        owner_id = voice_owners.get(channel.id)

        if self.values[0] == "claim":
            if owner_id in [m.id for m in channel.members]:
                embed = discord.Embed(description="❌ **原房主目前仍留在包廂內，無法進行轉移接管！**", color=discord.Color.red())
                return await interaction.response.send_message(embed=embed, ephemeral=True)
            voice_owners[channel.id] = interaction.user.id
            embed = discord.Embed(
                description=f"👑 **權限接管成功！** {interaction.user.mention} 已成為本包廂的新房主。",
                color=discord.Color.gold()
            )
            return await interaction.response.send_message(embed=embed)

        if interaction.user.id != owner_id:
            embed = discord.Embed(description="❌ **僅有此包廂的房主有權修改頻道設定！**", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)

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
                await channel.edit(name=f"🎮｜{game_activity}")
                embed = discord.Embed(description=f"✨ **頻道名稱已自動調整為遊戲動態：** `{game_activity}`", color=discord.Color.green())
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(description="⚠️ **未偵測到你正在遊玩任何遊戲狀態！**", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
        elif selected == "lfm":
            embed = discord.Embed(
                title="📢 隊友募集廣播",
                description=f"🔥 {interaction.user.mention} 正在包廂 {channel.mention} 徵求隊友中！歡迎大家踴躍加入～",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed)
        elif selected == "bitrate":
            await interaction.response.send_modal(BitrateModal())
        elif selected == "region":
            embed = discord.Embed(description="ℹ️ **當前語音區域為 Discord 自動最佳化指派模式。**", color=discord.Color.blue())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif selected == "text":
            text_channel = await interaction.guild.create_text_channel(name=f"💬-包廂討論", category=channel.category)
            embed = discord.Embed(description=f"✨ **已為您建立專屬臨時文字頻道：** {text_channel.mention}", color=discord.Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif selected == "nsfw":
            is_nsfw = not channel.nsfw
            await channel.edit(nsfw=is_nsfw)
            status_msg = "已啟用 (NSFW 模式)" if is_nsfw else "已停用 (一般模式)"
            embed = discord.Embed(description=f"✨ **頻道成人分級限制：** `{status_msg}`", color=discord.Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)

class ChannelPermissionsSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="上鎖頻道 (Lock)", description="將頻道鎖定，禁止一般成員進入", emoji="🔒", value="lock"),
            discord.SelectOption(label="解鎖頻道 (Unlock)", description="解除鎖定狀態，開放所有人加入", emoji="🔓", value="unlock"),
            discord.SelectOption(label="允許成員 (Permit)", description="指定成員或身分組進入頻道", emoji="👤", value="permit"),
            discord.SelectOption(label="封鎖成員 (Reject)", description="禁止並踢出指定成員", emoji="⛔", value="reject"),
            discord.SelectOption(label="邀請成員 (Invite)", description="向特定成員發送快捷加入邀請", emoji="✉️", value="invite"),
            discord.SelectOption(label="隱藏頻道 (Ghost)", description="使頻道對一般成員不可見", emoji="🚫", value="ghost"),
            discord.SelectOption(label="顯示頻道 (Unhost)", description="解除隱藏，公開顯示頻道", emoji="👁️", value="unghost"),
            discord.SelectOption(label="轉移房主 (Transfer)", description="將包廂管理權限移交給其他人", emoji="👑", value="transfer"),
        ]
        super().__init__(placeholder="🔒 頻道權限設定選單 (Channel Permissions)", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        owner_id = voice_owners.get(channel.id)

        if interaction.user.id != owner_id:
            embed = discord.Embed(description="❌ **僅有此包廂的房主有權設定權限！**", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        selected = self.values[0]
        guild = interaction.guild

        if selected == "lock":
            await channel.set_permissions(guild.default_role, connect=False)
            embed = discord.Embed(description="🔒 **頻道已成功上鎖！** 非獲准成員將無法進入。", color=discord.Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif selected == "unlock":
            await channel.set_permissions(guild.default_role, connect=None)
            embed = discord.Embed(description="🔓 **頻道已成功解鎖！** 所有成員皆可進入。", color=discord.Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif selected == "ghost":
            await channel.set_permissions(guild.default_role, view_channel=False)
            embed = discord.Embed(description="🙈 **頻道已進入隱藏模式！** 非獲准成員將無法在列表中看見。", color=discord.Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif selected == "unghost":
            await channel.set_permissions(guild.default_role, view_channel=None)
            embed = discord.Embed(description="👁️ **頻道已解除隱藏！** 現已公開於頻道列表。", color=discord.Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif selected in ["permit", "reject", "invite", "transfer"]:
            action_names = {
                "permit": "允許加入",
                "reject": "封鎖踢出",
                "invite": "發送邀請",
                "transfer": "轉移房主"
            }
            view = UserSelectView(action_type=selected, owner_id=owner_id)
            embed = discord.Embed(
                description=f"👉 **請選擇欲進行「{action_names[selected]}」操作的成員：**",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

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
            name=f"🔊｜{member.display_name} 的語音頻道",
            category=category,
            position=len(category.channels)
        )


        voice_owners[new_channel.id] = member.id

        await member.move_to(new_channel)

        embed = discord.Embed(
            title="✨ 歡迎來到你的獨立語音頻道！",
            description=(
                f"你好 {member.mention}！這是專屬於你的私人語音包廂。\n"
                "透過下方選單，你可以自由調整房間設定與成員進出權限。\n\n"
                "➡️ **設定說明**\n"
                "> ⚙️ **頻道設定選單**：修改名稱、人數限制、動態狀態、遊戲主題、音質及專屬討論區等。\n"
                "> 🔒 **頻道權限選單**：上鎖/解鎖包廂、隱藏包廂、允許/封鎖成員及轉移房主等。\n"
            ),
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="💡 提示：當頻道內所有成員離開後，系統將自動進行空間清理與回收。")

        view = ControlPanelView()
        await new_channel.send(embed=embed, view=view)


    if before.channel:

        if before.channel.id == TRIGGER_CHANNEL_ID:
            return


        if before.channel.id in voice_owners:
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
