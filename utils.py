import json
from bs4 import BeautifulSoup
import wikipediaapi
from googlesearch import search
import requests
import traceback
import discord
import string
import random
import time
import mysql.connector
import json
from datetime import datetime
from mysql.connector import Error
from db import mycon as db, mycur as cursor

def create_or_get_server_config(guild_id):
    """Create or get server configuration for a specific guild."""
    config = get_server_config(guild_id)
    if not config:
        config = {
            "staff_roles": [],
            "management_role": [],
            "mod_log_channel": "null",
            "premium": "false",
            "report_channel": "null",
            "blocked_search": [],
            "anti_ping": "false",
            "anti_ping_roles":[],
            "bypass_anti_ping_roles":[],
            "loa_role": "null",
            "staff_management_channel": "null"
        }
        update_server_config(guild_id, config)
    return config

def modlogchannel(guild_id):
  """Get moderation log channel for a specific guild."""
  config = load_config()
  return config.get(str(guild_id), {}).get("mod_log_channel")

def save_custom_command(config):
    try:
        if db.is_connected():
            cursor = db.cursor()
            for guild_id, commands in config.items():
                for command_name, details in commands.items():
                    title = details.get('title', '')
                    description = details.get('description', '')
                    color = details.get('colour', '')
                    image_url = details.get('image_url', '')
                    cursor.execute("INSERT INTO custom_commands (guild_id, command_name, title, description, color, image_url) VALUES (%s, %s, %s, %s, %s, %s)", (guild_id, command_name, title, description, color, image_url))
            db.commit()
    except Error as e:
        print("Error while connecting to MySQL", e)
    finally:
        if 'connection' in locals() and db.is_connected():
            cursor.close()
            db.close()

def list_custom_commands_embeds(interaction):
    config = load_custom_command()
    guild_id = str(interaction.guild.id)
    custom_commands = config.get(guild_id, {})
    if not custom_commands:
        return [discord.Embed(description="No custom commands found for this server.")]
    embeds = []
    for name, details in custom_commands.items():
        color_value = details.get('colour', discord.Color.default().value)
        try:
            color = int(color_value)  # Attempt to convert color value to int
        except ValueError:
            async def send_error_message():
                await interaction.channel.send("Invalid color value found in database.")
                await send_error_message()
            continue  
        embed = discord.Embed(title=details.get('title', ''), description=details.get('description', ''), color=color)
        image_url = details.get('image_url')
        if image_url:
            embed.set_image(url=image_url)
        embeds.append(embed)
    return embeds


wiki_wiki = wikipediaapi.Wikipedia('english')

def search_api(topic):
    page_py = wiki_wiki.page(topic)
    if page_py.exists():
        return truncate_to_nearest_sentence(page_py.summary[:500], 500)
    time.sleep(2)
    google_results = list(search(f"{topic} site:wikipedia.org", num_results=1))
    if google_results:
        first_result = google_results[0]
        if first_result.startswith("https://en.wikipedia.org/"):
            return truncate_to_nearest_sentence("Result: " + get_wikipedia_data(first_result)[:1500], 1500)
        else:
            return {first_result}
    else:
        return "Sorry, no information found for this topic."

def get_wikipedia_data(url):
  try:
      response = requests.get(url)
      if response.status_code == 200:
          soup = BeautifulSoup(response.text, 'html.parser')
          content_div = soup.find('div', {'id': 'mw-content-text'})
          paragraphs = content_div.find_all('p')
          data = '\n'.join([p.get_text() for p in paragraphs])
          return data
      else:
          return f"Failed to retrieve data. Status code: {response.status_code}"
  except Exception as e:
      return f"Error: {str(e)}"

def truncate_to_nearest_sentence(data, max_length):
  if len(data) <= max_length:
      return data
  else:
      truncated_data = data[:max_length]
      last_period_index = truncated_data.rfind('.')

      if last_period_index != -1 and (len(truncated_data) - last_period_index) > 0:
          return truncated_data[:last_period_index + 1]
      else:
          return truncated_data

def load_custom_command():
    try:
        if db.is_connected():
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM custom_commands where guild_id = %s", (guild_id))
            rows = cursor.fetchall()
            config = {}
            for row in rows:
                guild_id = str(row['guild_id'])
                command_name = row['command_name']
                title = row['title']
                description = row['description']
                color = row['color']
                image_url = row['image_url']
                if guild_id not in config:
                    config[guild_id] = {}
                config[guild_id][command_name] = {
                    "Command Name": command_name,
                    'title': title,
                    'description': description,
                    'colour': color,
                    'image_url': image_url
                }
            return config
    except Error as e:
        print("Error while connecting to MySQL", e)
    finally:
        if 'connection' in locals() and db.is_connected():
            cursor.close()
    return {}

def get_existing_uids(file_path='cerror.json'):
    try:
        with open(file_path, 'r') as file:
            errors = json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        errors = []

    existing_uids = set(error['uid'] for error in errors)
    return existing_uids

def generate_error_uid(existing_uids):
    while True:
        error_uid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        full_uid = "err_" + error_uid
        if full_uid not in existing_uids:
            return full_uid

def log_error(error, error_uid):
    try:
        traceback.print_exception(type(error), error, error.__traceback__)
        insert_query = "INSERT INTO error_logs (uid, message, traceback) VALUES (%s, %s, %s)"
        values = (error_uid, str(error), traceback.format_exc())
        cursor.execute(insert_query, values)
        db.commit()
    except Exception as e:
        print("Failed to log error:", e)

async def check_permissions(ctx, user):
    staff_roles = get_staff_roles(str(ctx.guild.id))
    management_roles = get_management_roles(str(ctx.guild.id))
    is_staff = any(role.id in staff_roles for role in user.roles)
    is_management = any(role.id in management_roles for role in user.roles)
    return is_staff or is_management

async def check_permissions_management(ctx, user):
    management_roles = get_management_roles(ctx.guild.id)
    is_management = any(role.id in management_roles for role in user.roles)
    return is_management

def fetch_random_joke():
    url = 'https://official-joke-api.appspot.com/jokes/random'
    response = requests.get(url)
    data = response.json()
    joke_setup = data['setup']
    joke_punchline = data['punchline']
    return f"{joke_setup}\n{joke_punchline}"

#MYSQL

def get_staff_roles(guild_id):
    """Get staff roles for a specific guild."""
    sql = "SELECT staff_roles FROM server_config WHERE guild_id = %s"
    cursor.execute(sql, (guild_id,))
    result = cursor.fetchone()
    if result:
        staff_roles = json.loads(result[0]) if result[0] else []
        return staff_roles
    else:
        return []

def get_management_roles(guild_id):
    """Get management roles for a specific guild."""
    sql = "SELECT management_roles FROM server_config WHERE guild_id = %s"
    cursor.execute(sql, (guild_id,))
    result = cursor.fetchone()
    if result:
        management_roles = json.loads(result[0]) if result[0] else []
        return management_roles
    else:
        return []

def get_staff_or_management_roles(guild_id):
    """Get staff or management roles for a specific guild."""
    sql = "SELECT staff_roles, management_roles FROM server_config WHERE guild_id = %s"
    cursor.execute(sql, (guild_id,))
    result = cursor.fetchone()
    if result:
        staff_roles = json.loads(result[0]) if result[0] else []
        management_roles = json.loads(result[1]) if result[1] else []
        return staff_roles + management_roles  # Concatenate staff and management roles
    else:
        return []
    
def save_management_roles(guild_id, management_roles):
    serialized_management_roles = json.dumps(management_roles)
    sql = "INSERT INTO server_config (guild_id, management_roles) VALUES (%s, %s) ON DUPLICATE KEY UPDATE management_roles = VALUES(management_roles)"
    cursor.execute(sql, (guild_id, serialized_management_roles))
    db.commit()

def save_staff_roles(guild_id, staff_roles):
    serialized_staff_roles = json.dumps(staff_roles)
    sql = "INSERT INTO server_config (guild_id, staff_roles) VALUES (%s, %s) ON DUPLICATE KEY UPDATE staff_roles = VALUES(staff_roles)"
    cursor.execute(sql, (guild_id, serialized_staff_roles))
    db.commit()

def cleanup_guild_data(bot):
    try:
        cursor = db.cursor()
        cursor.execute("SELECT guild_id FROM server_config")
        stored_guild_ids = [row[0] for row in cursor.fetchall()]
        bot_guild_ids = {guild.id for guild in bot.guilds}
        for guild_id in stored_guild_ids:
            if guild_id not in bot_guild_ids:
                print(f"Bot is not a member of the guild {guild_id}. Removing data from server_config table.")
                cursor.execute("DELETE FROM server_config WHERE guild_id = %s", (guild_id,))
                db.commit()
    except Exception as e:
        print(f"An error occurred while cleaning up guild data: {e}")
    finally:
        cursor.close()

def load_config():
    """Load server configuration from server_config table in the MySQL database."""
    config = {}
    try:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM server_config")
        rows = cursor.fetchall()
        for row in rows:
            guild_id = row[0]
            data = json.loads(row[1])
            config[str(guild_id)] = data
    except Exception as e:
        print(f"An error occurred while loading server configuration: {e}")
    finally:
        cursor.close()
    return config

def save_config(config):
    """Save server configuration to server_config table in the MySQL database."""
    try:
        cursor = db.cursor()
        for guild_id, data in config.items():
            serialized_data = json.dumps(data)
            cursor.execute("INSERT INTO server_config (guild_id, staff_roles, management_roles) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE staff_roles = VALUES(staff_roles), management_roles = VALUES(management_roles)", (guild_id, serialized_data['staff_roles'], serialized_data['management_roles']))
        db.commit()
    except Exception as e:
        print(f"An error occurred while saving server configuration: {e}")
    finally:
        cursor.close()

def get_server_config(guild_id):
    """Get server configuration for a specific guild."""
    try:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM server_config WHERE guild_id = %s", (guild_id,))
        row = cursor.fetchone()
        if row:
            config = {
                "guild_id": row[0],
                "staff_roles": json.loads(row[1] or "[]"),
                "management_roles": json.loads(row[2] or "[]"),
                "mod_log_channel": row[3],
                "premium": row[4],
                "report_channel": row[5],
                "blocked_search": json.loads(row[6] or "[]"),
                "anti_ping": row[7],
                "anti_ping_roles": json.loads(row[8] or "[]"),
                "bypass_anti_ping_roles": json.loads(row[9] or "[]"),
                "loa_role": json.loads(row[10] or "[]"),
                "staff_management_channel": row[11]
            }
            return config
        else:
            return {}
    except Exception as e:
        print(f"An error occurred while getting server configuration: {e}")
    finally:
        cursor.close()

def update_server_config(guild_id, data):
    """Update server configuration for a specific guild."""
    try:
        cursor = db.cursor()
        serialized_data = json.dumps(data)
        cursor.execute("INSERT INTO server_config (guild_id, config_data) VALUES (%s, %s) ON DUPLICATE KEY UPDATE config_data = VALUES(config_data)", (guild_id, serialized_data))
        db.commit()
    except Exception as e:
        print(f"An error occurred while updating server configuration: {e}")
    finally:
        cursor.close()

def save_mod_log_channel(guild_id, mod_log_channel_id):
    try:
        cursor.execute("INSERT INTO server_config (guild_id, mod_log_channel) VALUES (%s, %s) ON DUPLICATE KEY UPDATE mod_log_channel = VALUES(mod_log_channel)", (guild_id, mod_log_channel_id))
        db.commit()
    except Exception as e:
        print(f"An error occurred while saving mod log channel: {e}")

def set_anti_ping_option(guild_id, enable):
    try:
        cursor.execute("INSERT INTO server_config (guild_id, anti_ping) VALUES (%s, %s) ON DUPLICATE KEY UPDATE anti_ping = VALUES(anti_ping)", (guild_id, enable))
        db.commit()
    except Exception as e:
        print(f"An error occurred while setting anti-ping option: {e}")
    
def save_anti_ping_roles(guild_id, anti_ping_roles):
    try:
        cursor.execute("INSERT INTO server_config (guild_id, anti_ping_roles) VALUES (%s, %s) ON DUPLICATE KEY UPDATE anti_ping_roles = VALUES(anti_ping_roles)", (guild_id, json.dumps(anti_ping_roles)))
        db.commit()
    except Exception as e:
        print(f"An error occurred while saving anti-ping roles: {e}")

def save_anti_ping_bypass_roles(guild_id, anti_ping_bypass_roles):
    try:
        cursor.execute("INSERT INTO server_config (guild_id, bypass_anti_ping_roles) VALUES (%s, %s) ON DUPLICATE KEY UPDATE bypass_anti_ping_roles = VALUES(bypass_anti_ping_roles)", (guild_id, json.dumps(anti_ping_bypass_roles)))
        db.commit()
    except Exception as e:
        print(f"An error occurred while saving anti-ping bypass roles: {e}")

def save_loa_roles(guild_id, loa_roles):
    try:
        cursor.execute("INSERT INTO server_config (guild_id, loa_role) VALUES (%s, %s) ON DUPLICATE KEY UPDATE loa_role = VALUES(loa_role)", (guild_id, json.dumps(loa_roles)))
        db.commit()
    except Exception as e:
        print(f"An error occurred while saving LOA roles: {e}")

def save_staff_management_channel(guild_id, staff_management_channel_id):
    try:
        cursor.execute("INSERT INTO server_config (guild_id, staff_management_channel) VALUES (%s, %s) ON DUPLICATE KEY UPDATE staff_management_channel = VALUES(staff_management_channel)", (guild_id, staff_management_channel_id))
        db.commit()
    except Exception as e:
        print(f"An error occurred while saving staff management channel: {e}")

def robloxusername(userid):
    api_url = f"https://users.roblox.com/v1/users/{userid}"
    avatar_api_url = f"https://www.roblox.com/avatar-thumbnails?params=[{{userId:{userid}}}]"
    response = requests.get(avatar_api_url)
    avatar_data = response.json()[0]
    thumbnail_url = avatar_data["thumbnailUrl"]
    response = requests.get(api_url)
    data = response.json()
    created_timestamp = datetime.strptime(data["created"], "%Y-%m-%dT%H:%M:%S.%fZ")
    created_unix_timestamp = int(created_timestamp.timestamp())
    created_str = f"<t:{created_unix_timestamp}:R>"
    embed = discord.Embed(title="User Info", color=0x2F3136)
    embed.add_field(name="User ID", value=data["id"], inline=True)
    embed.add_field(name="Username", value=data["name"], inline=True)
    embed.add_field(name="Display Name",value=data["displayName"],inline=True)
    embed.add_field(name="Description",value=data["description"],inline=True)
    embed.set_thumbnail(url=thumbnail_url)
    embed.add_field(name="Is Banned", value=data["isBanned"], inline=True)
    embed.add_field(name="Has Verified Badge",value=data["hasVerifiedBadge"],inline=True)
    embed.add_field(name="Created", value=created_str, inline=True)
    return embed