import discord
from discord.ext import commands
import requests
import sys
import traceback
import logging
from prefixcommand import prefix_warn
from utils import *
import time
import random
from tokens import cynibeta_token
from menu import *
import psutil
import json
import os
import asyncio
from threading import Thread
#from hyme import run_staff_bot as run_hyme
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
import mysql.connector as msc
mycon=msc.connect(host='localhost',user='root',passwd='root',database='cyni')
mycur=mycon.cursor()

def dbstatus():
    if mycon.is_connected():
        return "Connected"
    else:
        return "Disconnected"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=':', intents=intents)
bot.remove_command('help')

async def load():
    for filename in os.listdir('./Cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'Cogs.{filename[:-3]}')
            print(f'Loaded {filename}')
    for filename in os.listdir("./Roblox"):
        if filename.endswith(".py"):
            await bot.load_extension(f"Roblox.{filename[:-3]}")
            print(f"Loaded {filename}")
    for filename in os.listdir("./ImagesCommand"):
        if filename.endswith(".py"):
            await bot.load_extension(f"ImagesCommand.{filename[:-3]}")
            print(f"Loaded {filename}")
    for filename in os.listdir("./Staff_Commands"):
        if filename.endswith(".py"):
            await bot.load_extension(f"Staff_Commands.{filename[:-3]}")
            print(f"Loaded {filename}")

@bot.event
async def on_ready():
    await load()
    await bot.tree.sync()
    bot.start_time = time.time()
    save_data()
    for guild in bot.guilds:
        create_or_get_server_config(guild.id)
    cleanup_guild_data(bot)
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="/support | Cyni"))
    await bot.load_extension("jishaku")
    print(f'Logged in as {bot.user.name} - {bot.user.id}')

cyni_support_role_id = 800203880515633163
@bot.event
async def on_thread_create(ctx):
    print("Thread created!")
    await ctx.send(f"<@{cyni_support_role_id}")
    await ctx.purge(limit=1)


BOT_USER_ID = 1136945734399295538

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if message.content.startswith(":jsk shutdown"):
        await message.channel.send("<@800203880515633163> Get to work!")

    if message.guild.id == 1152949579407442050 and message.channel.id == 1160481898536112170:
        if message.content.startswith('<@') and len(message.mentions) >= 2:
            voter = message.mentions[0]
            voted_for = message.mentions[1]
            if BOT_USER_ID == voted_for.id:
                role_id = 1209464266898407444
                role = discord.utils.get(message.guild.roles, id=role_id)
                if role:
                    try:
                        await voter.add_roles(role)
                        await asyncio.sleep(43200)
                        await voter.remove_roles(role)
                    except discord.Forbidden:
                        print("Bot doesn't have permission to manage roles.")
                    except discord.HTTPException as e:
                        print(f"An error occurred: {e}")
                else:
                    print("Role not found")
    await bot.process_commands(message)

    try:
        guild_id = message.guild.id
        cursor.execute("SELECT * FROM server_config WHERE guild_id = %s", (guild_id,))
        server_config = cursor.fetchone()
        
        if server_config:
            # Unpack server_config values
            guild_id, staff_roles, management_roles, mod_log_channel, premium, report_channel, blocked_search, anti_ping, anti_ping_roles, bypass_anti_ping_roles, loa_role, staff_management_channel = server_config
            
            # Check if anti_ping is enabled and not None
            if anti_ping == 1:
                anti_ping_roles = anti_ping_roles or []  # If anti_ping_roles is None, set it to an empty list
                bypass_anti_ping_roles = bypass_anti_ping_roles or []  # If bypass_anti_ping_roles is None, set it to an empty list
                
                # Assuming message.mentions is a list, check if it's not empty
                if message.mentions:
                    mentioned_user = message.mentions[0]
                    
                    author_has_bypass_role = any(str(role.id) in bypass_anti_ping_roles for role in message.author.roles)
                    has_management_role = any(str(role.id) in anti_ping_roles for role in mentioned_user.roles)
                    
                    # Check if the author has a bypass role
                    if not author_has_bypass_role:
                        # Check if mentioned user has management role
                        if has_management_role:
                            author_can_warn = any(str(role.id) in anti_ping_roles for role in message.author.roles)
                            # Check if author can warn
                            if not author_can_warn:
                                warning_message = f"{message.author.mention} Refrain from pinging users with Anti-ping enabled role, if it's not necessary."
                                await message.channel.send(warning_message)
    except Exception as e:
        print(f"An error occurred while processing message: {e}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound) and ctx.message.content.startswith('?warn'):
        return
    existing_uids = get_existing_uids()
    error_uid = generate_error_uid(existing_uids)
    sentry = discord.Embed(
        title="❌ An error occurred.",
        description=f"Error I'd `{error_uid}`\nThis can be solved by joining our support server.\n[Join Cyni Support](https://discord.gg/2D29TSfNW6)",
        color=0xFF0000
    )
    await ctx.send(embed=sentry)
    
    error_data = {
        "error_uid": error_uid,
        "command": ctx.message.content,
        "error": str(error),
        "traceback": ''.join(traceback.format_exception(type(error), error, error.__traceback__))
    }
    
    log_error('cerror.json', error, error_uid)

existing_uids = get_existing_uids()

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    error_uid = generate_error_uid(existing_uids)
    logger.error(f"Error UID: {error_uid}\n{''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))}")
sys.excepthook = handle_exception

@bot.event
async def on_guild_join(guild):
  create_or_get_server_config(guild.id)

@bot.tree.command()
async def say(interaction: discord.Interaction, message: str):
  '''Broadcasts a message in the channel'''
  channel = interaction.channel
  if await check_permissions(interaction, interaction.user):
    try:
        await interaction.response.send_message("Message sent.", ephemeral=True)
        await channel.send(message)
    except Exception as e:
        await on_general_error(interaction,e)
  else:
     await interaction.response.send_message("❌ You are not permitted to use this command",ephemeral=True)

@bot.tree.command()
async def slowmode(interaction: discord.Interaction, duration: str):
  '''Sets slowmode in channel'''
  time_units = {'s': 1, 'm': 60, 'h': 3600}
  try:
      if await check_permissions(interaction, interaction.user):
        try:
          amount = int(duration[:-1])
          unit = duration[-1]
          if unit not in time_units:
            raise ValueError
        except (ValueError, IndexError):
          await interaction.response.send_message('Invalid duration format. Please use a number followed by "s" for seconds, "m" for minutes, or "h" for hours.',ephemeral=True)
          return
        total_seconds = amount * time_units[unit]
        if total_seconds == 0:
          await interaction.response.send_message("Slow mode disabled from the channel.")
        elif total_seconds > 21600:
          await interaction.response.send_message('Slow mode duration cannot exceed 6 hours (21600 seconds).')
          return
        else:
          await interaction.channel.edit(slowmode_delay=total_seconds)
          await interaction.response.send_message(f'Slow mode set to {amount} {unit} in this channel.',ephemeral=True)
      else:
        await interaction.response.send_message("❌ You don't have permission to use this command.")
  except Exception as error:
          await on_general_error(interaction, error)

@bot.tree.command()
async def roleadd(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    '''Add a role to member'''
    try:
        if await check_permissions(interaction, interaction.user):
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.response.send_message("❌ You don't have the 'Manage Roles' permission.")
            elif role >= member.top_role:
                await interaction.response.send_message("❌ I can't add a role higher than or equal to the member's top role.")
            else:
                await member.add_roles(role)
                embed = discord.Embed(
                    title='Role added.',
                    description=f"Role {role.mention} added to {member.mention}",
                    color=0x00FF00)
                await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ You don't have permission to use this command.")
    except Exception as error:
        await on_general_error(interaction, error)

@bot.tree.command()
async def roleremove(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    '''Removes a role from member'''
    try:
        if await check_permissions(interaction, interaction.user):
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.response.send_message("❌ You don't have the 'Manage Roles' permission.")
            elif role >= member.top_role:
                await interaction.response.send_message("❌ I can't remove a role higher than or equal to the member's top role.")
            else:
                await member.remove_roles(role)
                embed = discord.Embed(title='Role Removed.', description=f"Role {role.mention} is now removed from {member.mention}", color=0xFF0000)
                await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ You don't have permission to use this command.")
    except Exception as error:
        await on_general_error(interaction, error)


@bot.tree.command()
async def membercount(interaction: discord.Interaction):
  '''Gives the total number of members in server.'''
  await interaction.response.send_message(f"{interaction.guild.member_count} members.")

@bot.command()
async def membercount(interaction: discord.Interaction):
  await interaction.channel.send(f"{interaction.guild.member_count} members.")

@bot.tree.command()
async def promote(interaction: discord.Interaction, member: discord.Member, *,old_rank: discord.Role, next_rank: discord.Role,approved: discord.Role, reason: str):
  '''Promote Server Staff'''
  try:
      if await check_permissions_management(interaction, interaction.user):
        channel = interaction.channel
        embed = discord.Embed(title=f"{interaction.guild.name} Promotions.",color=0x00FF00)
        embed.add_field(name="Staff Name", value=member.mention)
        embed.add_field(name="Old Rank", value=old_rank.mention)
        embed.add_field(name="New Rank", value=next_rank.mention)
        embed.add_field(name="Approved By", value=approved.mention)
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Signed By", value=interaction.user.mention)
        await interaction.response.send_message("Promotion Sent", ephemeral=True)
        await channel.send(member.mention, embed=embed)
      else:
        await interaction.response.send_message("❌ You don't have permission to use this command.")
  except Exception as error:
          await on_general_error(interaction, error)

@bot.tree.command()
async def demote(interaction: discord.Interaction, member: discord.Member, *,old_rank: discord.Role, next_rank: discord.Role,approved: discord.Role, reason: str):
  '''Demote Server Staff'''
  try:
      if await check_permissions_management(interaction, interaction.user):
        channel = interaction.channel
        embed = discord.Embed(title=f"{interaction.guild.name} Demotions.",color=0x00FF00)
        embed.add_field(name="Staff Name", value=member.mention)
        embed.add_field(name="Old Rank", value=old_rank.mention)
        embed.add_field(name="New Rank", value=next_rank.mention)
        embed.add_field(name="Approved By", value=approved.mention)
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Signed By", value=interaction.user.mention)
        await interaction.response.send_message("Demotion Sent", ephemeral=True)
        await channel.send(member.mention, embed=embed)
      else:
        await interaction.response.send_message("❌ You don't have permission to use this command.")
  except Exception as error:
          await on_general_error(interaction, error)

@bot.tree.command()
async def passapp(interaction: discord.Interaction, member: discord.Member, *,server_message: str, feedback: str):
  '''Post Passed Application Result'''
  try:
      if await check_permissions_management(interaction, interaction.user):
        channel = interaction.channel
        embed = discord.Embed(
        title=f"{interaction.guild.name} Application Passed.", color=0x00FF00)
        embed.add_field(name="Staff Name", value=member.mention)
        embed.add_field(name="Server Message", value=server_message)
        embed.add_field(name="Feedback", value=feedback)
        embed.add_field(name="Signed By", value=interaction.user.mention)
        await interaction.response.send_message("Result Sent", ephemeral=True)
        await channel.send(member.mention, embed=embed)
      else:
        await interaction.response.send_message("❌ You don't have permission to use this command.")
  except Exception as error:
          await on_general_error(interaction, error)

@bot.tree.command()
async def failapp(interaction: discord.Interaction, member: discord.Member, *,feedback: str):
  '''Post Failed Application result.'''
  try:
      if await check_permissions_management(interaction, interaction.user):
          channel = interaction.channel
          embed = discord.Embed(
          title=f"{interaction.guild.name} Application Failed.", color=0xFF0000)
          embed.add_field(name="Staff Name", value=member.mention)
          embed.add_field(name="Feedback", value=feedback)
          embed.add_field(name="Signed By", value=interaction.user.mention)
          await interaction.response.send_message("Result Sent", ephemeral=True)
          await channel.send(member.mention, embed=embed)
      else:
          await interaction.response.send_message("❌ You don't have permission to use this command.")
  except Exception as error:
          await on_general_error(interaction, error)

@bot.tree.command()
async def purge(interaction: discord.Interaction, amount: int):   
  '''Purge messages from channel'''
  try:
    if await check_permissions(interaction, interaction.user):
      await interaction.response.send_message(f'Cleared {amount} messages.',ephemeral=True)
      await interaction.channel.purge(limit=amount + 1)      
    else:
      await interaction.response.send_message("❌ You don't have permission to use this command.")
  except Exception as error:
          await on_general_error(interaction, error)

@bot.tree.command()
async def custom_run(interaction:discord.Interaction,command_name:str):
    '''Run Custom Command'''
    if await check_permissions(interaction, interaction.user):
          await run_custom_command(interaction, command_name)
          embed = discord.Embed(title="Custom Command Executed",description=f"Custom Command {command_name} executed by {interaction.user.mention}",color=0x00FF00)
          await interaction.response.send_message(embed=embed)
    else:
      await interaction.response.send_message("❌ You don't have permission to use this command.")

@bot.tree.command()
async def custom_manage(interaction:discord.Interaction, action:str, name:str):
    '''Manage Custom Commands (create, delete, list)'''
    try:
      if await check_permissions_management(interaction, interaction.user):
            if action == 'create':
                await create_custom_command(interaction, name) 
            elif action == 'delete':
                await delete_custom_command(interaction, name)
            elif action == 'list':
                await list_custom_commands(interaction)
            else:
                await interaction.response.send_message("Invalid action. Valid actions are: create, delete, list.")
            await interaction.response.send_message("Custom command executed successfully.")
    except Exception as error:
          await on_general_error(interaction, error)

def list_custom_commands_embeds(interaction):
    config = load_customcommand()
    guild_id = str(interaction.guild.id)
    custom_commands = config.get(guild_id, {})
    if not custom_commands:
        return [discord.Embed(description="No custom commands found for this server.")]
    embeds = []
    for name, details in custom_commands.items():
        embed = discord.Embed(title=details.get('title', ''),description=details.get('description', ''), color=details.get('colour', discord.Color.default().value))
        image_url = details.get('image_url')
        if image_url:
            embed.set_image(url=image_url)
        embeds.append(embed)
    return embeds

async def list_custom_commands(interaction):
    embeds = list_custom_commands_embeds(interaction)
    for embed in embeds:
        await interaction.channel.send(embed=embed)

async def run_custom_command(interaction, command_name):
    config = load_customcommand()
    guild_id = str(interaction.guild.id)
    command_details = config.get(guild_id, {}).get(command_name)
    if command_details:
        embed = discord.Embed(
            title=command_details.get('title', ''),
            description=command_details.get('description', ''),
            color=command_details.get('colour', discord.Color.default().value))
        image_url = command_details.get('image_url')
        embed.set_footer(text="Executed By: " + interaction.user.name)
        if image_url:
            embed.set_image(url=image_url)
        channel_id = command_details.get('channel')
        channel = bot.get_channel(channel_id)
        role_id = command_details.get('role')
        if role_id:
            role = interaction.guild.get_role(role_id)
            if role:
                await channel.send(f"<@&{role_id}>")  
            else:
                await interaction.channel.send("Role not found. Please make sure the role exists.")
                return
        await channel.send(embed=embed)
        await interaction.channel.send(f"Custom command '{command_name}' executed in {channel.mention}.")
    else:
        await interaction.channel.send(f"Custom command '{command_name}' not found.")

async def create_custom_command(interaction, command_name):
    config = load_customcommand()
    guild_id = str(interaction.guild.id)
    if command_name in config.get(guild_id, {}):
        await interaction.channel.send(f"Custom command '{command_name}' already exists.")
        return
    if len(config.get(guild_id, {})) >= 5:
        await interaction.channel.send("Sorry, the server has reached the maximum limit of custom commands (5).")
        return
    await interaction.channel.send("Enter embed title:")
    title = await bot.wait_for('message', check=lambda m: m.author == interaction.user, timeout=60)
    await interaction.channel.send("Enter embed description:")
    description = await bot.wait_for('message', check=lambda m: m.author == interaction.user, timeout=60)
    await interaction.channel.send("Enter embed colour (hex format, e.g., #RRGGBB):")
    colour = await bot.wait_for('message', check=lambda m: m.author == interaction.user, timeout=60)
    await interaction.channel.send("Enter image URL (enter 'none' for no image):")
    image_url_input = await bot.wait_for('message', check=lambda m: m.author == interaction.user, timeout=60)
    await interaction.channel.send("Enter default channel to post message (mention the channel):")
    channel_input = await bot.wait_for('message', check=lambda m: m.author == interaction.user, timeout=60)
    await interaction.channel.send("Enter role ID to ping (enter 'none' for no role):")
    role_id_input = await bot.wait_for('message', check=lambda m: m.author == interaction.user, timeout=60)
    channel_id = int(channel_input.content[2:-1])
    if role_id_input.content.lower() == 'none':
        role_id = None
    else:
        role_id = int(role_id_input.content)
    try:
        color_decimal = int(colour.content[1:], 16)
    except ValueError:
        await interaction.channel.send("Invalid hex color format. Please use the format #RRGGBB.")
        return
    image_url = image_url_input.content.strip()
    if image_url.lower() == 'none':
        image_url = None
    if len(config.get(guild_id, {})) >= 5:
        await interaction.channel.send("Sorry, the server has reached the maximum limit of custom commands (5).")
        return
    config.setdefault(guild_id, {})[command_name] = {
        'title': title.content,
        'description': description.content,
        'colour': color_decimal,
        'channel': channel_id,
        'role': role_id,
        'image_url': image_url,
    }
    save_customcommand(config)
    embed = discord.Embed(title="Custom Command Created", description=f"Custom command '{command_name}' created successfully.", color=discord.Color.random())
    await interaction.channel.send(embed=embed)

async def delete_custom_command(interaction, command_name):
  config = load_customcommand()
  guild_id = str(interaction.guild.id)
  command_details = config.get(guild_id, {}).get(command_name)
  if command_details:
    del config[guild_id][command_name]
    save_customcommand(config)
    await interaction.channel.send(f"Custom command '{command_name}' deleted successfully.")
  else:
    await interaction.channel.send(f"Custom command '{command_name}' not found.")

@bot.tree.command()
async def pick(interaction: discord.Interaction, option1:str, option2:str):
  '''Pick between two options'''
  option = random.choice([option1, option2])
  await interaction.response.send_message(f"I pick {option}")

@bot.command(name='pick')
async def pick(ctx, option1, option2):
  option = random.choice([option1, option2])
  await ctx.send(f"I pick {option}")

@bot.tree.command()
async def catimage(interaction:discord.Interaction):
  '''Get Random Cat Image'''
  response = requests.get("https://api.thecatapi.com/v1/images/search")
  data = response.json()
  image_url = data[0]["url"]
  embed = discord.Embed(title="Random Cat Image", color=discord.Color.random())
  embed.set_image(url=image_url)
  await interaction.response.send_message(embed=embed)

@bot.tree.command()
async def dogimage(interaction: discord.Interaction):
    '''Get Random Dog Image'''
    response = requests.get("https://api.thedogapi.com/v1/images/search")
    data = response.json()
    image_url = data[0]["url"]
    embed = discord.Embed(title="Random Dog Image", color=discord.Color.random())
    embed.set_image(url=image_url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command()
async def getavatar(interaction: discord.Interaction, user: discord.User):
  '''Get any user avatar from server'''
  try:
    embed = discord.Embed(title=f"{user.name}'s Profile Photo", color=0x00FFFF)
    embed.set_image(url=user.avatar)
    await interaction.response.send_message(embed=embed)
  except Exception as error:
        await on_general_error(interaction, error)

@bot.event
async def on_general_error(ctx, error):
    file_path = 'cerror.json'
    existing_uids = get_existing_uids(file_path)
    error_uid = generate_error_uid(existing_uids)
    log_error(file_path, error, error_uid)
    if isinstance(ctx, discord.Interaction):
        embed = discord.Embed(
            title="❌ An error occurred",
            description=f"An error occurred (Error UID: `{error_uid}`). Please contact support.",
            color=0xFF0000
        )
        await ctx.channel.send(embed=embed)
    else:
        await ctx.channel.send(f"An error occurred (Error UID: `{error_uid}`). Please contact support.")

@bot.tree.command()
async def whois(interaction:discord.Interaction, user_info:str):
    guild_id = str(interaction.guild.id)
    server_config = get_server_config(guild_id)
    if user_info is None:
          member = interaction.user
    else:
          if user_info.startswith('<@') and user_info.endswith('>'):
              user_id = int(user_info[2:-1])
              member = interaction.guild.get_member(user_id)
          else:
              member = discord.utils.find(lambda m: m.name == user_info, interaction.guild.members)
    if member:
          support_server_id = 1152949579407442050
          support_server = bot.get_guild(support_server_id)
          user_emoji = discord.utils.get(support_server.emojis, id=1191057214727786598)
          cyni_emoji = discord.utils.get(support_server.emojis, id=1185563043015446558)
          discord_emoji = discord.utils.get(support_server.emojis, id=1191057244004044890)
          with open('staff.json', 'r') as file:
              staff_data = json.load(file)
          embed = discord.Embed(title="User Information", color=member.color)
          hypesquad_flags = member.public_flags
          hypesquad_values = [str(flag).replace("UserFlags.", "").replace("_", " ").title() for flag in hypesquad_flags.all()]
          if hypesquad_values:
              hypesquad_text = "\n".join(hypesquad_values)
              embed.add_field(name=f"{discord_emoji} Discord Flags", value=f"{hypesquad_text}", inline=True)
          user_flags = staff_data.get(member.name, "").replace("{cyni_emoji}", "")
          user_flags = [flag.strip() for flag in user_flags.split("\n") if flag.strip()]
          if user_flags:
              staff_text = "\n".join(user_flags)
              embed.add_field(name=f'{cyni_emoji} Staff Flags', value=f" {staff_text}", inline=True)
          embed.set_thumbnail(url=member.avatar.url)
          embed.add_field(name=f"{user_emoji} Username", value=member.name, inline=True)
          embed.add_field(name="User ID", value=member.id, inline=True)
          embed.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
          embed.add_field(name="Joined Discord", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
          if member == member.guild.owner:
              embed.add_field(name="Role", value="Server Owner", inline=True)
          elif member.guild_permissions.administrator:
              embed.add_field(name="Role", value="Administrator", inline=True)
          elif member.guild_permissions.manage_messages:
              embed.add_field(name="Role", value="Moderator", inline=True)
          else:
              embed.add_field(name="Role", value="Member", inline=True)
          embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.avatar.url)
          await interaction.response.send_message(embed=embed)
    else:
          await interaction.response.send_message("User not found.")

@bot.tree.command()
async def support(interaction:discord.Interaction):
  '''Join Cyni Support Server'''
  embed = discord.Embed(title="Cyni Support Server",description="Need any help?\nJoin Cyni Support Server.",color=0x00FF00)
  await interaction.response.send_message(embed=embed ,view=SupportBtn())

@bot.command()
async def support(interaction:discord.Interaction):
  '''Join Cyni Support Server'''
  embed = discord.Embed(title="Cyni Support Server",description="Need any help?\nJoin Cyni Support Server.",color=0x00FF00)
  await interaction.channel.send(embed=embed ,view=SupportBtn())

@bot.tree.command()
async def servermanage(interaction:discord.Interaction):
  '''Manage Your Server with Cyni'''
  try:
    if interaction.user.guild_permissions.administrator:
      embed = discord.Embed(title="Server Manage",description='''
                          **Staff Roles:**
                          - *Discord Staff Roles:* These roles grant permission to use Cyni's moderation commands.\n
                          - *Management Roles:* Users with these roles can utilize Cyni's management commands, including Application Result commands, Staff Promo/Demo command, and setting the Moderation Log channel.

                          **Mod Logger:**
                          - *Moderation Log Channel:* This channel is designated for Cyni to log all moderation actions taken on the server.

                          **Server Config:**
                          - Easily view and edit your server configuration settings.

                          **Anti-ping Module:**
                          - Messages are sent if a user with specific roles attempts to ping anyone. Bypass roles can be configured to allow certain users to ping others with that role.

                          **Support Server:**
                          - Need assistance? Join the Cyni Support Server for help.
                            '''
                            ,color=0x00FF00) 
      await interaction.response.send_message(embed=embed, view=SetupView(),ephemeral=True)
    else:
      await interaction.response.send_message("❌ You don't have permission to use this command.")
  except Exception as error:
          await on_general_error(interaction, error)

@bot.tree.command()
async def blocksearch(interaction:discord.Interaction, keyword: str):
  """Add blocked words from Cyni Search in server."""
  if await check_permissions_management(interaction, interaction.user):
    embed = discord.Embed(title="Blocked Search",description=f"**Keyword:** {keyword}\n**Blocked By:** {interaction.user.mention}",color=0x00FF00)
    await interaction.response.send_message("Blocked Search Added", ephemeral=True)
    with open("server_config.json", "r") as file:
        server_config = json.load(file)
        guild_id = str(interaction.guild.id)
        server_config[guild_id]["blocked_search"].append(keyword)
    with open("server_config.json", "w") as file:
        json.dump(server_config, file, indent=4)     
    await interaction.response.send_message(embed=embed)
  else:
    await interaction.response.send_message("❌ You don't have permission to use this command.")

@bot.tree.command()
async def websearch(interaction:discord.Interaction, topic: str):
  """Search on web using CYNI Search API"""
  guild_id = str(interaction.guild.id)
  server_config = get_server_config(guild_id)
  blocked_search = server_config.get('blocked_search', [])
  if topic in blocked_search:
      await interaction.response.send_message("Blocked word found in search query.")
      return
  result = search_api(topic)
  await interaction.response.send_message(f"{result}....")

@bot.tree.command()
async def birdimage(interaction: discord.Interaction):
    '''Get Random Bird Image'''
    response = requests.get("https://birbapi.astrobirb.dev/birb")
    data = response.json()
    image_url = data["image_url"]
    embed = discord.Embed(title="Random Bird Image", color=discord.Color.random())
    embed.set_image(url=image_url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command()
async def joke(interaction:discord.Interaction):
   joke = fetch_random_joke()
   await interaction.response.send_message(joke)

@bot.command()
async def help(ctx):
   embed = discord.Embed(title="Cyni Help",color=0x00FF00)
   embed.add_field(name="Cyni Docs",value="[Cyni Docs](https://qupr-digital.gitbook.io/cyni-docs/)",inline=False)
   embed.add_field(name="Support Server",value="[Join Cyni Support Server for help.](https://discord.gg/2D29TSfNW6)",inline=False)
   await ctx.channel.send(embed=embed,view = SupportBtn())

TOKEN = cynibeta_token()
def run_cynibot():
   bot.run(TOKEN)

def cyni():
    bot_thread = Thread(target=run_cynibot)
    #staff_bot_thread = Thread(target=run_hyme)
    bot_thread.start()
    #staff_bot_thread.start()
    bot_thread.join()
    #staff_bot_thread.join()