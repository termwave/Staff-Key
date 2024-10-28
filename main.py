import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import json
import datetime
import string
import random


def get_owner_ids():
    try:
        with open('owners.txt', 'r') as file:
            return [line.strip() for line in file.readlines()]
    except FileNotFoundError:
        return []

owners = get_owner_ids()


bot = commands.Bot(command_prefix="?", intents=discord.Intents.all(), case_insensitive=True)

TOKEN = ""
STAFF_ROLE_ID = 1288772885401305143  

def read_json(filename):
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def write_json(filename, data):
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)

def generate_random_key(length=25):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def save_key_with_expiry(key):
    expiry_date = datetime.datetime.now() + datetime.timedelta(days=30)
    new_key_entry = {"key": key, "expiry": expiry_date.timestamp()}
    keys_data = read_json('keys.json')
    if not isinstance(keys_data, list):
        keys_data = []
    keys_data.append(new_key_entry)
    write_json('keys.json', keys_data)

async def save_panel_info(channel_id, message_id):
    with open('panels.txt', 'a') as f:
        f.write(f"{channel_id},{message_id}\n")

async def load_panels():
    try:
        with open('panels.txt', 'r') as f:
            for line in f:
                channel_id, message_id = map(int, line.strip().split(','))
                channel = bot.get_channel(channel_id)
                if channel:
                    try:
                        message = await channel.fetch_message(message_id)
                        await message.edit(view=StaffPanelView())
                    except discord.NotFound:
                        print(f"Message {message_id} in channel {channel_id} not found.")
    except FileNotFoundError:
        print("No panels found to load.")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await load_panels()
    bot.add_view(StaffPanelView())  # Register the view for persistent usage

class StaffPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Auto Restore", emoji="<:Whitelist:1252922863124742274>", style=discord.ButtonStyle.primary, custom_id="auto_restore_button")
    async def auto_restore(self, interaction: discord.Interaction, button: Button):
        await handle_auto_restore(interaction)

    @discord.ui.button(label="Enter Key", emoji="<a:key:1252921920073240686>", style=discord.ButtonStyle.primary, custom_id="enter_key_button")
    async def enter_key(self, interaction: discord.Interaction, button: Button):
        await handle_enter_key(interaction)


@bot.command(name="generatekey", aliases=["genkey"])
async def generatekey(ctx):
    if str(ctx.author.id) not in owners:
        await ctx.send("You do not have permission to use this command.")
        return
    new_key = generate_random_key()
    save_key_with_expiry(new_key)
    expiry_timestamp = int((datetime.datetime.now() + datetime.timedelta(days=30)).timestamp())
    expiry_format = f"<t:{expiry_timestamp}:R>"
    try:
        embedkey = discord.Embed(
            title="",
            description=f"**Generated Key:** {new_key}\n**Expiry Date:** {expiry_format}",
            color=discord.Color.green()
        )
        await ctx.author.send(embed=embedkey)
        embedsent = discord.Embed(
            title="",
            description="The key has been sent to your DMs.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embedsent)
    except discord.Forbidden:
        embedforbidden = discord.Embed(
            title="",
            description="I cannot send you DMs. Please check your privacy settings.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embedforbidden)

@bot.command(name="sendstaffpanel")
async def sendstaffpanel(ctx):
    if str(ctx.author.id) not in owners:
        await ctx.send("You do not have permission to use this command.")
        return
    ghostyembedpanel = discord.Embed(
        title="Staff Panel",
        description="**Recover your roles and data using the options below**",
        color=discord.Color.blue()
    )
    message = await ctx.send(embed=ghostyembedpanel, view=StaffPanelView())
    await save_panel_info(ctx.channel.id, message.id)

class KeyModal(Modal):
    def __init__(self):
        super().__init__(title="Staff Role Panel")
        self.key_input = TextInput(label="Enter Your Staff Key", placeholder="Enter Staff Key which is assigned to you.")
        self.add_item(self.key_input)

    async def on_submit(self, interaction: discord.Interaction):
        key = self.key_input.value.strip()
        keys = read_json('keys.json')
        for entry in keys:
            if entry["key"] == key:
                if datetime.datetime.fromtimestamp(entry["expiry"]) < datetime.datetime.now():
                    await interaction.response.send_message("This key is expired.", ephemeral=True)
                else:
                    role = interaction.guild.get_role(STAFF_ROLE_ID)
                    await interaction.user.add_roles(role)
                    keys.remove(entry)
                    write_json('keys.json', keys)
                    staffs = read_json('staffs.json')
                    staffs.append({
                        "key": key,
                        "user": interaction.user.name,
                        "user_id": interaction.user.id,
                        "redeemed_at": datetime.datetime.now().isoformat()
                    })
                    write_json('staffs.json', staffs)
                    await interaction.response.send_message("Key redeemed successfully. You have been given the staff role.", ephemeral=True)
                return
        await interaction.response.send_message("This key is invalid.", ephemeral=True)

async def handle_enter_key(interaction: discord.Interaction):
    await interaction.response.send_modal(KeyModal())

async def handle_auto_restore(interaction: discord.Interaction):
    staffs = read_json('staffs.json')
    for entry in staffs:
        if entry["user_id"] == interaction.user.id:
            role = interaction.guild.get_role(STAFF_ROLE_ID)
            await interaction.user.add_roles(role)
            await interaction.response.send_message("Your staff role has been restored.", ephemeral=True)
            return
    await interaction.response.send_message("You are not in the staff database.", ephemeral=True)

bot.run(TOKEN)
