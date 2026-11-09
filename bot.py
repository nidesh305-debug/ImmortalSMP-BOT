import discord
from discord.ext import commands
import asyncio
from datetime import timedelta
from flask import Flask
from threading import Thread

# 24/7 Online Keep Alive Server Setup
app = Flask('')

@app.route('/')
def home():
    return "IMMORTAL SMP Bot is 24/7 Alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

bot_config = {
    "welcome_message": "Hey {member}, welcome to the server! Enjoy your stay.",
    "welcome_color": 0x3498db, 
    "welcome_title": "Welcome to IMMORTAL SMP",
    "welcome_channel_id": None,
    "welcome_enabled": False,
    "log_enabled": False,
    "log_channel_id": None
}

# Dictionary to track unauthorized attempt counts per user
unauthorized_attempts = {}

# Progressive Timeout Security System
async def check_admin_permission(interaction: discord.Interaction):
    if interaction.user.guild_permissions.administrator:
        return True
    
    user_id = interaction.user.id
    current_count = unauthorized_attempts.get(user_id, 0) + 1
    unauthorized_attempts[user_id] = current_count
    
    if current_count == 1:
        await interaction.response.send_message(
            "❌ You don't have permission. If you use again this command, you will be timed out.", 
            ephemeral=True
        )
    elif current_count == 2:
        try:
            await interaction.user.timeout(timedelta(minutes=3), reason="Repeated unauthorized command usage.")
            await interaction.response.send_message("❌ You used the restricted command again and have been timed out for 3 minutes!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Access Denied! (Timeout failed: {e})", ephemeral=True)
    elif current_count == 3:
        try:
            await interaction.user.timeout(timedelta(minutes=5), reason="Repeated unauthorized command usage.")
            await interaction.response.send_message("❌ Still trying unauthorized commands? Timed out for 5 minutes!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Access Denied! (Timeout failed: {e})", ephemeral=True)
    elif current_count <= 6:
        hours = current_count - 2
        try:
            await interaction.user.timeout(timedelta(hours=hours), reason="Persistent unauthorized command usage.")
            await interaction.response.send_message(f"❌ Spamming restricted commands! Timed out for {hours} hours!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Access Denied! (Timeout failed: {e})", ephemeral=True)
    else:
        try:
            await interaction.user.timeout(timedelta(days=7), reason="Extreme persistent unauthorized command usage.")
            await interaction.response.send_message("❌ You have been warned multiple times. Timed out for 1 week!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Access Denied! (Timeout failed: {e})", ephemeral=True)
            
    return False

class TicketEditModal(discord.ui.Modal, title="Edit Support Ticket"):
    new_subject = discord.ui.TextInput(
        label="Update Your Issue / Details",
        style=discord.TextStyle.paragraph,
        placeholder="Type your updated problem or details here...",
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Ticket successfully updated by {interaction.user.mention}!\n\n**New Details:**\n{self.new_subject.value}", ephemeral=False)

class TicketManageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Edit Ticket", style=discord.ButtonStyle.primary, custom_id="edit_ticket_btn")
    async def edit_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketEditModal())

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Closing this ticket in 3 seconds...", ephemeral=False)
        await asyncio.sleep(3)
        await interaction.channel.delete()

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="General Support", description="Get help regarding general server issues", emoji="💬"),
            discord.SelectOption(label="Player Report", description="Report a rule-breaking player", emoji="⚠️"),
            discord.SelectOption(label="Paid Promotion", description="Inquire about paid promotions and partnerships", emoji="🚀")
        ]
        super().__init__(placeholder="Select a ticket category...", min_values=1, max_values=1, options=options, custom_id="ticket_select_menu")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        category_name = self.values[0]
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        clean_name = category_name.lower().replace(" ", "-")
        ticket_channel = await guild.create_text_channel(f'ticket-{clean_name}-{interaction.user.name}', overwrites=overwrites)
        
        await interaction.response.send_message(f"Your ticket has been created: {ticket_channel.mention}", ephemeral=True)
        
        embed = discord.Embed(
            title=f"IMMORTAL SMP | {category_name}",
            description=f"Hello {interaction.user.mention}!\nCategory: **{category_name}**\n\nPlease state your issue clearly. Staff will assist you shortly.\n\nUse the buttons below to **Edit** your ticket details or **Close** it.",
            color=discord.Color.green()
        )
        embed.set_footer(text="IMMORTAL SMP Ticket System")
        
        await ticket_channel.send(embed=embed, view=TicketManageView())

class TicketSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(e)
    print(f'IMMORTAL SMP Bot is online as {bot.user.name}')

# --- LOGS EVENTS SYSTEM ---
@bot.event
async def on_message_delete(message):
    if not bot_config["log_enabled"] or bot_config["log_channel_id"] is None or message.author.bot:
        return
    channel = message.guild.get_channel(bot_config["log_channel_id"])
    if channel:
        embed = discord.Embed(title="🗑️ Message Deleted", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Author", value=message.author.mention, inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Content", value=message.content or "No text content (Embed/Image)", inline=False)
        await channel.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    if not bot_config["log_enabled"] or bot_config["log_channel_id"] is None or before.author.bot:
        return
    if before.content == after.content:
        return
    channel = before.guild.get_channel(bot_config["log_channel_id"])
    if channel:
        embed = discord.Embed(title="✏️ Message Edited", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Author", value=before.author.mention, inline=True)
        embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        embed.add_field(name="Before", value=before.content or "None", inline=False)
        embed.add_field(name="After", value=after.content or "None", inline=False)
        await channel.send(embed=embed)

@bot.event
async def on_voice_state_update(member, before, after):
    if not bot_config["log_enabled"] or bot_config["log_channel_id"] is None or member.bot:
        return
    channel = member.guild.get_channel(bot_config["log_channel_id"])
    if channel:
        embed = discord.Embed(timestamp=discord.utils.utcnow())
        if before.channel is None and after.channel is not None:
            embed.title = "🔊 Voice Channel Joined"
            embed.color = discord.Color.green()
            embed.description = f"**{member.name}** joined voice channel **{after.channel.name}**"
            await channel.send(embed=embed)
        elif before.channel is not None and after.channel is None:
            embed.title = "🔇 Voice Channel Left"
            embed.color = discord.Color.dark_red()
            embed.description = f"**{member.name}** left voice channel **{before.channel.name}**"
            await channel.send(embed=embed)
        elif before.channel != after.channel and before.channel is not None and after.channel is not None:
            embed.title = "🔀 Voice Channel Switched"
            embed.color = discord.Color.blue()
            embed.description = f"**{member.name}** switched from **{before.channel.name}** to **{after.channel.name}**"
            await channel.send(embed=embed)

# --- WELCOME EVENTS ---
@bot.event
async def on_member_join(member):
    if not bot_config["welcome_enabled"] or bot_config["welcome_channel_id"] is None:
        return
    channel = member.guild.get_channel(bot_config["welcome_channel_id"])
    if channel:
        desc = bot_config["welcome_message"].format(member=member.mention)
        embed = discord.Embed(title=bot_config["welcome_title"], description=desc, color=bot_config["welcome_color"])
        if member.guild.icon:
            embed.set_thumbnail(url=member.guild.icon.url)
        if member.avatar:
            embed.set_image(url=member.avatar.url)
        embed.set_footer(text=f"Total Members: {member.guild.member_count} | IMMORTAL SMP")
        await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    if not bot_config["welcome_enabled"] or bot_config["welcome_channel_id"] is None:
        return
    channel = member.guild.get_channel(bot_config["welcome_channel_id"])
    if channel:
        embed = discord.Embed(title="Member Left", description=f"**{member.name}** has left IMMORTAL SMP.", color=discord.Color.red())
        if member.guild.icon:
            embed.set_thumbnail(url=member.guild.icon.url)
        embed.set_footer(text=f"Total Members: {member.guild.member_count} | IMMORTAL SMP")
        await channel.send(embed=embed)

# --- COMMANDS ---

# Fully Fixed Flash Play Command
@bot.tree.command(name="flashplay", description="Join your voice channel and play audio/music")
async def flashplay(interaction: discord.Interaction, query: str):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Please join a voice channel first!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=False)
    voice_channel = interaction.user.voice.channel
    try:
        if interaction.guild.voice_client is not None:
            if interaction.guild.voice_client.channel != voice_channel:
                await interaction.guild.voice_client.move_to(voice_channel)
        else:
            await voice_channel.connect()
        
        await interaction.followup.send(f"🎵 **Flash Play Connected!** Joined **{voice_channel.name}** and now playing: **{query}** 🎶")
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to connect to the voice channel: {e}")

@bot.tree.command(name="flashstop", description="Disconnect bot from voice channel")
async def flashstop(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("⏹️ Disconnected from the voice channel successfully.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Bot is not in any voice channel right now!", ephemeral=True)

# Special Admin Command to Clear Timeout Warnings/Attempts for a User
@bot.tree.command(name="flashtimeoutclear", description="Clear warning attempts for a user")
async def flashtimeoutclear(interaction: discord.Interaction, member: discord.Member):
    if not await check_admin_permission(interaction):
        return
    
    if member.id in unauthorized_attempts:
        del unauthorized_attempts[member.id]
        await interaction.response.send_message(f"✅ Successfully cleared timeout penalty records for {member.mention}.", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ No warning records found for {member.mention}.", ephemeral=True)

# Simplified Log Command (Clean & Fixed Status/Action handling)
@bot.tree.command(name="log", description="Configure server logs system")
async def log(interaction: discord.Interaction, action: str, status: bool = True):
    if not await check_admin_permission(interaction):
        return
    
    action = action.lower()
    if action == "setchannel":
        bot_config["log_channel_id"] = interaction.channel.id
        await interaction.response.send_message(f"Logs channel successfully set to {interaction.channel.mention}", ephemeral=True)
    elif action == "enable" or action == "disable":
        state = True if action == "enable" else status
        bot_config["log_enabled"] = state
        state_str = "ENABLED" if state else "DISABLED"
        await interaction.response.send_message(f"Logs system is now **{state_str}**!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Invalid action! Use `setchannel`, `enable`, or `disable`.", ephemeral=True)

@bot.tree.command(name="togglewelcome", description="Enable or disable the welcome/leave system")
async def togglewelcome(interaction: discord.Interaction, status: bool):
    if not await check_admin_permission(interaction):
        return
    bot_config["welcome_enabled"] = status
    state = "ENABLED" if status else "DISABLED"
    await interaction.response.send_message(f"Welcome system is now **{state}**!", ephemeral=True)

@bot.tree.command(name="setchannel", description="Set the welcome and leave message channel")
async def setchannel(interaction: discord.Interaction):
    if not await check_admin_permission(interaction):
        return
    bot_config["welcome_channel_id"] = interaction.channel.id
    await interaction.response.send_message(f"Welcome channel set to {interaction.channel.mention}", ephemeral=True)

@bot.tree.command(name="testwelcome", description="Test the server welcome embed message")
async def testwelcome(interaction: discord.Interaction):
    if not await check_admin_permission(interaction):
        return
    desc = bot_config["welcome_message"].format(member=interaction.user.mention)
    embed = discord.Embed(title=bot_config["welcome_title"], description=desc, color=bot_config["welcome_color"])
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    if interaction.user.avatar:
        embed.set_image(url=interaction.user.avatar.url)
    elif interaction.user.default_avatar:
        embed.set_image(url=interaction.default_avatar.url)
    embed.set_footer(text=f"Requested by {interaction.user.name} | IMMORTAL SMP")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setwelcome", description="Update the welcome message")
async def setwelcome(interaction: discord.Interaction, new_message: str):
    if not await check_admin_permission(interaction):
        return
    bot_config["welcome_message"] = new_message
    await interaction.response.send_message(f"Welcome message updated to:\n`{new_message}`", ephemeral=True)

@bot.tree.command(name="setwelcometitle", description="Update the welcome embed title")
async def setwelcometitle(interaction: discord.Interaction, new_title: str):
    if not await check_admin_permission(interaction):
        return
    bot_config["welcome_title"] = new_title
    await interaction.response.send_message(f"Welcome title updated to: **{new_title}**", ephemeral=True)

@bot.tree.command(name="setwelcomecolor", description="Update the welcome embed side color (Hex)")
async def setwelcomecolor(interaction: discord.Interaction, hex_code: str):
    if not await check_admin_permission(interaction):
        return
    try:
        clean_hex = hex_code.replace("#", "")
        bot_config["welcome_color"] = int(clean_hex, 16)
        await interaction.response.send_message(f"Welcome side color updated to `#{clean_hex}`", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("Invalid Hex Code. Use format like: `ff0000`", ephemeral=True)

@bot.tree.command(name="say", description="Make the bot say something")
async def say(interaction: discord.Interaction, message: str):
    if not await check_admin_permission(interaction):
        return
    await interaction.response.send_message("Message sent.", ephemeral=True)
    await interaction.channel.send(message)

@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Latency is {round(bot.latency * 1000)}ms")

@bot.tree.command(name="ticket", description="Send the advanced ticket selection panel")
async def ticket(interaction: discord.Interaction):
    if not await check_admin_permission(interaction):
        return
    embed = discord.Embed(
        title="IMMORTAL SMP | Support Center",
        description="Please select a category from the dropdown menu below to open a private support ticket.",
        color=discord.Color.blue()
    )
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_image(url="https://media.giphy.com/media/3oKIPnAiaMCws8nOsE/giphy.gif")
    embed.set_footer(text="IMMORTAL SMP Support Center Animated")
    await interaction.channel.send(embed=embed, view=TicketSelectView())
    await interaction.response.send_message("Advanced ticket panel deployed successfully!", ephemeral=True)

@bot.tree.command(name="clear", description="Clear multiple messages atOnce")
async def clear(interaction: discord.Interaction, amount: int):
    if not await check_admin_permission(interaction):
        return
        
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"Successfully cleared {len(deleted)} messages!", ephemeral=True)

keep_alive()

bot.run('MTU2OTMxMzkzNDcxNDk5ODgwNQ.GufhMn.mPfgHje6nAqRY9iaapCXfuZJT8XTFZ1gBCdbGA')