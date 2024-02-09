import discord
from discord import app_commands
from discord.ext import tasks
import sqlite3
from dotenv import load_dotenv
import os
import typing
import datetime, time
import random
from PIL import Image, ImageDraw, ImageFont
import io
import os

load_dotenv()
botToken = os.getenv("BOT_TOKEN")

# Create a connection to the database
conn = sqlite3.connect('database.db')
cur = conn.cursor()

# Create the table if it doesn't exist
cur.execute('''
    CREATE TABLE IF NOT EXISTS ServerSettings (
        serverId INTEGER PRIMARY KEY,
        actionLogChannelId INTEGER DEFAULT 0,
        joinLeaveLogChannelId INTEGER DEFAULT 0,
        approvalLogChannelId INTEGER DEFAULT 0,
        inviteLogChannelId INTEGER DEFAULT 0,
        messageLogChannelId INTEGER DEFAULT 0,
        approvalChannelId INTEGER DEFAULT 0,
        approvalMessageChannelId INTEGER DEFAULT 0,
        levelUpChannelId INTEGER DEFAULT 0,
        modRole INTEGER DEFAULT 0,
        adminRole INTEGER DEFAULT 0,
        muteRole INTEGER DEFAULT 0,
        approvalRole INTEGER DEFAULT 0,
        trialRole INTEGER DEFAULT 0,
        bumpRemindRole INTEGER DEFAULT 0
    )
''')

cur.execute('''
    CREATE TABLE IF NOT EXISTS UserLevels (
        userId INTEGER,
        serverId INTEGER,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 0,
        lastMessageTime INTEGER DEFAULT 0
    )
''')

cur.execute('''
    CREATE TABLE IF NOT EXISTS Warns (
        warnId INTEGER PRIMARY KEY AUTOINCREMENT,
        userId INTEGER,
        serverId INTEGER,
        reason TEXT,
        time INTEGER
    )
''')

cur.execute('''
    CREATE TABLE IF NOT EXISTS Kicks (
        kickId INTEGER PRIMARY KEY AUTOINCREMENT,
        userId INTEGER,
        serverId INTEGER,
        reason TEXT,
        time INTEGER
    )
''')

cur.execute('''
    CREATE TABLE IF NOT EXISTS Bans (
        banId INTEGER PRIMARY KEY AUTOINCREMENT,
        userId INTEGER,
        serverId INTEGER,
        reason TEXT,
        time INTEGER
    )
''')

cur.execute('''
    CREATE TABLE IF NOT EXISTS JoinRoles (
        roleId INTEGER,
        serverId INTEGER
    )
    ''')

cur.execute('''
    CREATE TABLE IF NOT EXISTS UserApprovals (
        userId INTEGER,
        serverId INTEGER,
        messageId INTEGER,
        threadId INTEGER,
        time INTEGER,
        stage INTEGER DEFAULT 0
    )
''')

cur.execute('''
    CREATE TABLE IF NOT EXISTS BumpReminder (
        serverId INTEGER PRIMARY KEY,
        lastBumpTime INTEGER DEFAULT 0
    )
''')

conn.commit()


class aclient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(intents=intents)
        self.synced = False
        
    async def on_ready(self):
        await bot.change_presence(activity = discord.Game(name = "with mod tools"))
        if not self.synced:
            await tree.sync()
            self.synced = True
        
        for guild in bot.guilds:
            cur.execute("SELECT * FROM ServerSettings WHERE serverId = ?", (guild.id,))
            result = cur.fetchone()
            if result == None:
                cur.execute("INSERT INTO ServerSettings (serverId) VALUES (?)", (guild.id,))
                conn.commit()

        await self.wait_until_ready()
        print(f"We are ready for moderation as {bot.user}!")
        await self.approvalReminder.start()

    @tasks.loop(seconds=15)
    async def approvalReminder(self):
        if True == False:
            cur.execute(f"SELECT * FROM UserApprovals WHERE stage = 0 AND curTime < {int(time.time()) - 86400}")
            result = cur.fetchall()
            for approval in result:
                print(result)
                try:
                    user = bot.get_user(approval[0])
                    print(user)
                    if user != None:
                        await user.send(f"It has been 24 hours since you joined! Please answer the questions in <#{approval[3]}> to be approved! If you do not approve within the next 24 hours, you will be automatically kicked from the server. If you have any questions, please contact a staff member.")
                    else:
                        break
                    channel = bot.get_channel(approval[3])
                    print(channel)
                    if channel != None:
                        await channel.send(f"24 hour reminder sent to {user.display_name}")
                    else:
                        break
                except:
                    channel = bot.get_channel(approval[3])
                    print(channel)
                    if channel != None:
                        await channel.send(f"<@{approval[0]}> It has been 24 hours since you joined! Please answer the questions above to be approved! If you do not approve within the next 24 hours, you will be automatically kicked from the server. If you have any questions, please contact a staff member.")
                print("doing this")
                cur.execute("UPDATE UserApprovals SET stage = 1 WHERE userId = ? AND serverId = ?", (approval[0], approval[1]))
                conn.commit()

            cur.execute(f"SELECT * FROM UserApprovals WHERE stage = 1 AND curTime < {int(time.time()) - 172800} AND curTime != 0")
            result = cur.fetchall()
            for approval in result:
                print(result)
                try:
                    user = bot.get_user(approval[0])
                    print(user)
                    if user != None:
                        await user.send("You have been inactive for 48 hours, you have been removed from the server. If you would like to rejoin, please use the invite link again and answer the questions in the approval channel!")
                    else:
                        pass
                except:
                    pass
                channel = bot.get_channel(approval[3])
                print(channel)
                if channel != None:
                    await channel.send(f"User has been inactive for 48 hours, they will be removed from the server")
                try:
                    guild = bot.get_guild(approval[1])
                    user = bot.get_user(approval[0])
                    await guild.kick(user = user)
                except Exception as e:
                    print(e)
                    if channel != None:
                        await channel.send("Unable to kick user, please do so manually")
                        cur.execute("UPDATE UserApprovals SET stage = 2 WHERE userId = ? AND serverId = ?", (approval[0], approval[1]))
                        conn.commit()

# Initialize the bot
bot = aclient()
tree = app_commands.CommandTree(bot)

@tree.command(name="purge", description="Delete a number of messages from a channel")
@app_commands.describe(limit = "The number of messages to delete")
async def self(interaction: discord.Interaction, limit: int):
    if interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message(f"Deleted {limit} messages", ephemeral=True)
        await interaction.channel.purge(limit=limit, check=lambda msg: not msg.pinned)
    else:
        await interaction.response.send_message(f"⚠️ You do not have permission to use this command. You must have manage messages privileges ⚠️", ephemeral=True)

@tree.command(name = "kick", description = "Kick a user from the server")
@app_commands.describe(user = "The user to kick", reason = "The reason for kicking the user")
async def self(interaction: discord.Interaction, user: discord.Member, reason: str):
    if interaction.user.guild_permissions.kick_members:
        await user.kick(reason = reason)
        await interaction.response.send_message(f"Kicked {user} for {reason}")
        cur.execute("INSERT INTO Kicks (userId, serverId, reason, curTime) VALUES (?, ?, ?)", (user.id, interaction.guild.id, reason, int(time.time())))
        conn.commit()
    else:
        await interaction.response.send_message(f"⚠️ You do not have permission to use this command. You must have kick privileges ⚠️", ephemeral=True)

@tree.command(name = "ban", description = "Ban a user from the server")
@app_commands.describe(user = "The user to ban", reason = "The reason for banning the user", delete_message_minutes = "The number of days of messages to delete")
async def self(interaction: discord.Interaction, user: discord.Member, reason: str, delete_message_minutes: int = 0):
    if interaction.user.guild_permissions.ban_members:
        await user.ban(reason = reason, delete_message_seconds=delete_message_minutes*60)
        await interaction.response.send_message(f"Banned {user} for {reason}")
        cur.execute("INSERT INTO Bans (userId, serverId, reason, curTime) VALUES (?, ?, ?)", (user.id, interaction.guild.id, reason, int(time.time())))
        conn.commit()
    else:
        await interaction.response.send_message(f"⚠️ You do not have permission to use this command. You must have ban privileges ⚠️", ephemeral=True)

@tree.command(name="unban", description="Unban a user from the server")
@app_commands.describe(userid = "The id of the user to unban", reason = "The reason for unbanning the user")
async def self(interaction: discord.Interaction, userid: str, reason: str):
    if interaction.user.guild_permissions.ban_members:
        await interaction.guild.unban(discord.Object(id = userid), reason = reason)
        await interaction.response.send_message(f"Unbanned {userid} for {reason}")
        cur.execute("DELETE FROM Bans WHERE userId = ? AND serverId = ?", (userid, interaction.guild.id))
        conn.commit()
    else:
        await interaction.response.send_message(f"⚠️ You do not have permission to use this command. You must have ban privileges ⚠️", ephemeral=True)

@tree.command(name="warn", description="Warn a user")
@app_commands.describe(user = "The user to warn", reason = "The reason for warning the user")
async def self(interaction: discord.Interaction, user: discord.Member, reason: str):
    if interaction.user.guild_permissions.kick_members:
        cur.execute("INSERT INTO Warns (userId, serverId, reason, curTime) VALUES (?, ?, ?)", (user.id, interaction.guild.id, reason, int(time.time())))
        conn.commit()
        await interaction.response.send_message(f"Warned {user} for {reason}")

    else:
        await interaction.response.send_message(f"⚠️ You do not have permission to use this command. You must have kick privileges ⚠️", ephemeral=True)

@tree.command(name="timeout", description="Timeout a user")
@app_commands.describe(user = "The user to timeout", reason = "The reason for timing out the user", minutes = "The amount of time to timeout the user for")
async def self(interaction: discord.Interaction, user: discord.Member, minutes: int, reason: str):
    if interaction.user.guild_permissions.kick_members:
        curTime = datetime.datetime.now()
        endTime = curTime + datetime.timedelta(minutes=minutes)
        await user.timeout(endTime, reason = reason)
        await interaction.response.send_message(f"Timed out {user} for {reason} for {minutes} minutes")
    else:
        await interaction.response.send_message(f"⚠️ You do not have permission to use this command. You must have kick privileges ⚠️", ephemeral=True)

@tree.command(name = "untimeout", description = "Untimeout a user")
@app_commands.describe(user = "The user to untimeout")
async def self(interaction: discord.Interaction, user: discord.Member):
    if interaction.user.guild_permissions.kick_members:
        await user.timeout(None)
        await interaction.response.send_message(f"Untimed out {user}")
    else:
        await interaction.response.send_message(f"⚠️ You do not have permission to use this command. You must have kick privileges ⚠️", ephemeral=True)


@tree.command(name="approve", description="Approve a user")
@app_commands.describe(user = "The user to approve", trial = "Whether to approve the user as a trial member")
async def self(interaction: discord.Interaction, user: discord.Member, trial: bool = False):
    if interaction.user.guild_permissions.kick_members:
        cur.execute("SELECT approvalRole,trialRole FROM ServerSettings WHERE serverId = ?", (interaction.guild.id,))
        result = cur.fetchone()
        if trial:
            for role in user.roles:
                if role.id == result[1]:
                    await interaction.response.send_message(f"User is already a trial member")
                    return
            if result[1] != None and result[1] != 0:
                await user.add_roles(discord.Object(id = result[1]))
            else:
                await interaction.response.send_message(f"Trial role not set")
                return
        else:
            for role in user.roles:
                if role.id == result[0]:
                    await interaction.response.send_message(f"User is already a member")
                    return
            if result[0] != None and result[0] != 0:
                await user.add_roles(discord.Object(id = result[0]))
            else:
                await interaction.response.send_message(f"Approval role not set")
                return
            for role in user.roles:
                if role.id == result[1]:
                    print("User is a trial member")
                    await user.remove_roles(discord.Object(id = result[1]))
        await interaction.response.send_message(f"Approved {user}")
        cur.execute("SELECT threadId, messageId FROM UserApprovals WHERE userId = ? AND serverId = ? AND (stage = 0 OR stage = 1)", (user.id, interaction.guild.id))
        result = cur.fetchone()
        thread = bot.get_channel(result[0])
        cur.execute("SELECT approvalLogChannelId FROM ServerSettings WHERE serverId = ?", (interaction.guild.id,))
        channel = bot.get_channel(cur.fetchone()[0])
        await thread.delete()
        try:
            message = await channel.fetch_message(result[1])
            await message.delete()
        except:
            pass
        cur.execute("UPDATE UserApprovals SET stage = 3 WHERE userId = ? AND serverId = ?", (user.id, interaction.guild.id))
        conn.commit()
        await channel.send(f"{user} was approved", file=discord.File(f"./{thread.id}.txt"))
        os.remove(f"./{thread.id}.txt")
        cur.execute("SELECT approvalMessageChannelId FROM ServerSettings WHERE serverId = ?", (interaction.guild.id,))
        result = cur.fetchone()
        if result[0] != None and result[0] != 0:
            channel = bot.get_channel(result[0])
            embed = discord.Embed(title="New Member Alert!", description=f"Give a warm welcome to {user.mention}!", color=0xffa500, timestamp=datetime.datetime.now())
            await channel.send(embed=embed)
            
    else:
        await interaction.response.send_message(f"⚠️ You do not have permission to use this command. You must have kick privileges ⚠️", ephemeral=True)

@tree.command(name="setchannels", description="Set the channels for the bot to use")
@app_commands.describe(setting = "The setting to change", channel = "The channel to set the setting to")
async def self(interaction: discord.Interaction, setting:typing.Literal["Mod Action Log Channel", "Join/Leave Log Channel", "Approval Log Channel", "Invite Log Channel", "Message Log Channel", "Approval Channel", "Approved Message Channel", "Level Up Channel"], channel: discord.TextChannel):
    if interaction.user.guild_permissions.administrator:
        if setting == "Mod Action Log Channel":
            cur.execute("UPDATE ServerSettings SET actionLogChannelId = ? WHERE serverId = ?", (channel.id, interaction.guild.id))
            conn.commit()
            await interaction.response.send_message(f"Set the mod action log channel to {channel.mention}")
        elif setting == "Join/Leave Log Channel":
            cur.execute("UPDATE ServerSettings SET joinLeaveLogChannelId = ? WHERE serverId = ?", (channel.id, interaction.guild.id))
            conn.commit()
            await interaction.response.send_message(f"Set the join/leave log channel to {channel.mention}")
        elif setting == "Approval Log Channel":
            cur.execute("UPDATE ServerSettings SET approvalLogChannelId = ? WHERE serverId = ?", (channel.id, interaction.guild.id))
            conn.commit()
            await interaction.response.send_message(f"Set the approval log channel to {channel.mention}")
        elif setting == "Invite Log Channel":
            cur.execute("UPDATE ServerSettings SET inviteLogChannelId = ? WHERE serverId = ?", (channel.id, interaction.guild.id))
            conn.commit()
            await interaction.response.send_message(f"Set the invite log channel to {channel.mention}")
        elif setting == "Message Log Channel":
            cur.execute("UPDATE ServerSettings SET messageLogChannelId = ? WHERE serverId = ?", (channel.id, interaction.guild.id))
            conn.commit()
            await interaction.response.send_message(f"Set the message log channel to {channel.mention}")
        elif setting == "Approval Channel":
            cur.execute("UPDATE ServerSettings SET approvalChannelId = ? WHERE serverId = ?", (channel.id, interaction.guild.id))
            conn.commit()
            await interaction.response.send_message(f"Set the approval channel to {channel.mention}")
        elif setting == "Approved Message Channel":
            cur.execute("UPDATE ServerSettings SET approvalMessageChannelId = ? WHERE serverId = ?", (channel.id, interaction.guild.id))
            conn.commit()
            await interaction.response.send_message(f"Set the approval message channel to {channel.mention}")
        elif setting == "Level Up Channel":
            cur.execute("UPDATE ServerSettings SET levelUpChannelId = ? WHERE serverId = ?", (channel.id, interaction.guild.id))
            conn.commit()
            await interaction.response.send_message(f"Set the level up channel to {channel.mention}")
    else:
        await interaction.response.send_message(f"⚠️ You do not have permission to use this command. You must have administrator privileges ⚠️", ephemeral=True)

@tree.command(name="setroles", description="Set the roles for the bot to use")
@app_commands.describe(setting = "The setting to change", role = "The role to set the setting to")
async def self(interaction: discord.Interaction, setting:typing.Literal["Mod Role", "Admin Role", "Mute Role", "Approval Role", "Trial Role"], role: discord.Role):
    if interaction.user.guild_permissions.administrator:
        if setting == "Mod Role":
            cur.execute("UPDATE ServerSettings SET modRole = ? WHERE serverId = ?", (role.id, interaction.guild.id))
            conn.commit()
            await interaction.response.send_message(f"Set the mod role to {role.name}")
        elif setting == "Admin Role":
            cur.execute("UPDATE ServerSettings SET adminRole = ? WHERE serverId = ?", (role.id, interaction.guild.id))
            conn.commit()
            await interaction.response.send_message(f"Set the admin role to {role.name}")
        elif setting == "Mute Role":
            cur.execute("UPDATE ServerSettings SET muteRole = ? WHERE serverId = ?", (role.id, interaction.guild.id))
            conn.commit()
            await interaction.response.send_message(f"Set the mute role to {role.name}")
        elif setting == "Approval Role":
            cur.execute("UPDATE ServerSettings SET approvalRole = ? WHERE serverId = ?", (role.id, interaction.guild.id))
            conn.commit()
            await interaction.response.send_message(f"Set the approval role to {role.name}")
        elif setting == "Trial Role":
            cur.execute("UPDATE ServerSettings SET trialRole = ? WHERE serverId = ?", (role.id, interaction.guild.id))
            conn.commit()
            await interaction.response.send_message(f"Set the trial role to {role.name}")
    else:
        await interaction.response.send_message(f"⚠️ You do not have permission to use this command. You must have administrator privileges ⚠️", ephemeral=True)

@tree.command(name="setjoinroles", description="Set the roles for the bot to give to users when they join")
@app_commands.describe(roles = "Comma separated list of roles to give to users when they join")
async def self(interaction: discord.Interaction, roles: str):
    if interaction.user.guild_permissions.administrator:
        roles = roles.replace("<@&","").replace(">","").replace(" ", "").split(",")
        for role in roles:
            cur.execute("INSERT INTO JoinRoles (roleId, serverId) VALUES (?, ?)", (role, interaction.guild.id))
            conn.commit()
        await interaction.response.send_message(f"Set the join roles to {roles}")
    else:
        await interaction.response.send_message(f"⚠️ You do not have permission to use this command. You must have administrator privileges ⚠️", ephemeral=True)

@tree.command(name="settings", description="View the current settings")
async def self(interaction: discord.Interaction):
    if interaction.user.guild_permissions.administrator:
        cur.execute("SELECT * FROM ServerSettings WHERE serverId = ?", (interaction.guild.id,))
        result = cur.fetchone()
        embed = discord.Embed(title="Current Server Settings", description=f"Mod Action Log Channel: <#{result[1]}>\nJoin/Leave Log Channel: <#{result[2]}>\nApproval Log Channel: <#{result[3]}>\nInvite Log Channel: <#{result[4]}>\nApproval Channel: <#{result[5]}>\nApproval Message Channel: <#{result[6]}>\nLevel Up Channel: <#{result[7]}>\nMod Role: <@&{result[8]}>\nAdmin Role: <@&{result[9]}>\nMute Role: <@&{result[10]}>\nApproval Role: <@&{result[11]}>\nTrial Role: <@&{result[12]}>\n\nTo set these, use /setchannels or /setroles".replace("<#0>", "Unset").replace("<@&0>","Unset"), color=0xffa500)
        await interaction.response.send_message(embed=embed)

class HelpMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Moderation", description="Commands for moderating your server", emoji="🛠️"),
            discord.SelectOption(label="Levels", description="Commands for the level system", emoji="📈"),
            discord.SelectOption(label="Settings", description="Commands for setting up the bot", emoji="⚙️"),
            discord.SelectOption(label="Miscellaneous", description="Commands that don't fit into any other category", emoji="❓")
            ]
        super().__init__(placeholder="Select a category", options=options, row=0)
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Moderation":
            embed = discord.Embed(title="Moderation Commands", description="**/purge (limit)** - This command is used for deleting many messages at a time!\n**/kick (user) (reason)** - This command is used for kicking members from the server\n**/ban (user) (reason)** - This command is used for banning members from the server\n**/unban (userid) (reason)** - This command will allow you to pardon a user from a prior ban\n**/warn (user) (reason)** - This command will store a warn about the user for moderator's future use\n**/approve (user) [trial]** - This will give the user a dedicated approval or trial role set in the /setroles command", color=0xffa500)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif self.values[0] == "Settings":
            embed = discord.Embed(title="Settings Commands", description="**/setchannels (setting) (channel)** - This command will set the channel for a specific setting\n**/setroles (setting) (role)** - This command will set the role for a specific setting\n**/setjoinroles (roles)** - This command will set the roles that the bot will give to users when they join\n**/settings** - This command will show the current settings for the server", color=0xffa500)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif self.values[0] == "Miscellaneous":
            embed = discord.Embed(title="Miscellaneous Commands", description="**/help** - This command will show the help menu", color=0xffa500)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif self.values[0] == "Levels":
            embed = discord.Embed(title="Level Commands", description="**/level [user]** - This command will show your level\n**/leaderboard** - This command will show the server's leaderboard\n**/background [image]** - This command will allow you to upload or reset your /level background! Leaving blank will reset the image to default", color=0xffa500)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
class SelectView(discord.ui.View):
    def __init__(self, *, timeout = 180):
        super().__init__(timeout=timeout)
        self.add_item(HelpMenu())

@tree.command(name="help", description="View the help menu")
async def self(interaction:discord.Interaction):
    view = SelectView()
    embed = discord.Embed(title=f"A Furry Neighbor Help Center", description=f"Select the category of commands that you would like to see!\n\n**Categories**\n\n**Moderation**\nCommands for moderating your server\n\n**Levels**\nCommands for the leveling system\n\n**Settings**\nCommands for setting up the bot\n\n**Miscellaneous**\nCommands that don't fit into any other category", color=0xffa500)
    await interaction.response.send_message(embed=embed, view=view)

async def approval(member):
    cur.execute("SELECT approvalChannelId, modRole FROM ServerSettings WHERE serverId = ?", (member.guild.id,))
    result = cur.fetchone()
    if result[0] != None and result[0] != 0:
        channel = bot.get_channel(result[0])
        message = await channel.send(f"Approval for {member.display_name}")
        thread = await message.create_thread(name=f"Approval for {member.display_name}")
        cur.execute("INSERT INTO UserApprovals (userId, serverId, messageId, threadId, curTime) VALUES (?, ?, ?, ?, ?)", (member.id, member.guild.id, message.id, thread.id, int(time.time())))
        conn.commit()
        with open(f"./{thread.id}.txt", "w") as f:
            f.write(f"Approval for {member.name}\n\n")
        await thread.send("<@&" + str(result[1]) + ">")
        await thread.add_user(member)
        await thread.send("```Welcome to The Furry Neighborhood! In order to verify, please make sure you thoroughly read the rules then answer these questions below! Admins have full right to not allow you into the server even if they deem you \"Sketchy\" so please answer genuinely and as non robotic as you can lol\n\n1. What is your legal age?\n\n2. Where did you find the server?\n\n3. What do you hope to find within here?\n\n4. Tell us about yourself, things like who are you, hobbies and likings and such.\n\n5. Tell us a bit about your fursona!\n\n6. Please answer the secret question in the rules\n\n\nPlease be patient while a staff member becomes available!```")


@bot.event
async def on_member_join(member):
    cur.execute("SELECT * FROM JoinRoles WHERE serverId = ?", (member.guild.id,))
    result = cur.fetchall()
    discordRoles = []
    for role in result:
        discordRole = member.guild.get_role(role[0])
        discordRoles.append(discordRole)
    await member.add_roles(*discordRoles)

    cur.execute("SELECT joinLeaveLogChannelId FROM ServerSettings WHERE serverId = ?", (member.guild.id,))
    result = cur.fetchone()
    if result[0] != None and result[0] != 0:
        channel = member.guild.get_channel(result[0])
        embed = discord.Embed(title = "Join Notification", description = f"<@{member.id}> (`{member}`) has joined the server!\n\n**Creation Date**\n`{member.created_at.strftime('%Y-%m-%d %H:%M:%S')}`", timestamp=datetime.datetime.now(), color=0xffa500)
        try:
            embed.set_thumbnail(url = member.avatar.url)
        except:
            pass
        embed.set_footer(text=f"There are now {member.guild.member_count} members.")
        await channel.send(embed=embed)

    await approval(member)

@bot.event
async def on_member_remove(member):
    cur.execute("SELECT * FROM UserApprovals WHERE userId = ? AND serverId = ? AND (stage = 0 OR stage = 1)", (member.id, member.guild.id))
    result = cur.fetchone()
    if result != None:
        cur.execute("UPDATE UserApprovals SET stage = 2 WHERE userId = ? AND serverId = ?", (member.id, member.guild.id))
        conn.commit()
        thread = bot.get_channel(result[3])
        await thread.delete()
        cur.execute("SELECT approvalLogChannelId FROM ServerSettings WHERE serverId = ?", (member.guild.id,))
        result = cur.fetchone()
        channel = bot.get_channel(result[0])
        await channel.send(f"{member.name} left the server, approval cancelled", file=discord.File(f"./{thread.id}.txt"))
        os.remove(f"./{thread.id}.txt")
    cur.execute("SELECT joinLeaveLogChannelId FROM ServerSettings WHERE serverId = ?", (member.guild.id,))
    result = cur.fetchone()
    if result[0] != None and result[0] != 0:
        channel = member.guild.get_channel(result[0])
        roles = ""
        for role in member.roles:
            roles = roles + ", " + role.name
        embed = discord.Embed(title= "Leave Notification", description=f"<@{member.id}> (`{member}`) has left the server!\n\n**Roles**\n" + roles, timestamp=datetime.datetime.now(), color=0xff5500)
        try:
            embed.set_thumbnail(url = member.avatar.url)
        except:
            pass
        embed.set_footer(text=f"There are now {member.guild.member_count} members.")
        await channel.send(embed=embed)
        channel = bot.get_channel(1070455145877491902)

@bot.event
async def on_guild_join(guild):
    cur.execute("INSERT INTO ServerSettings (serverId) VALUES (?)", (guild.id,))
    conn.commit()
    if guild.system_channel != None:
        channel = guild.system_channel
    else:
        channel = guild.text_channels[0]
    await channel.send(f"Thanks for adding me to your server! To get started, use /help to see the commands that I have to offer! I recommend checking out the settings section first to set up the logging and approval channels, as well as the role settings! If you need any help, contact @felix.dev")

@tree.command(name="dev", description="Developer commands")
async def self(interaction: discord.Interaction, command: typing.Literal["Immitate Join"]):
    if interaction.user.id == 546917684810481665:
        if command == "Immitate Join":
            await on_guild_join(interaction.guild)
            await interaction.response.send_message(f"Immitated join", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ You do not have permission to use this command. You must be Felix.Dev lol ⚠️", ephemeral=True)

def approvalLogging(message):
    cur.execute("SELECT * FROM UserApprovals WHERE ThreadId = ? AND (stage = 0 OR stage = 1)", (message.channel.id,))
    result = cur.fetchone()
    if result != None:
        with open(f"./{message.channel.id}.txt", "a") as f:
            try:
                f.write(f"{message.author.name}: {message.content}\n\n")
            except:
                split = message.content.split
                f.write(f"{message.author.name}: ")
                for word in split:
                    try:
                        f.write(f"{word} ")
                    except:
                        f.write(f"(emoji?) ")

async def levelSystem(message):
    if not message.author.bot:
        cur.execute("SELECT * FROM UserLevels WHERE userId = ? AND serverId = ?", (message.author.id, message.guild.id))
        userLevelData = cur.fetchone()
        if userLevelData == None:
            xp = random.randint(15,25)
            cur.execute("INSERT INTO UserLevels (userId, serverId, xp, level, lastMessageTime) VALUES (?, ?, ?, ?, ?)", (message.author.id, message.guild.id, xp, 1, int(time.time())))
            conn.commit()
            userLevelData = (message.author.id, message.guild.id, xp, 0, int(time.time()))
        else:
            cur.execute("SELECT levelUpChannelId FROM ServerSettings WHERE serverId = ?", (message.guild.id,))
            result = cur.fetchone()
            if result[0] != None and result[0] != 0:
                channel = bot.get_channel(result[0])
            else:
                channel = message.channel
            if int(time.time()) - userLevelData[4] > 60:
                xp = random.randint(15,25)
                nextLevelXp = 5 * (userLevelData[3] * userLevelData[3]) + 50 * userLevelData[3] + 100 - userLevelData[2]
                if nextLevelXp <= xp:
                    cur.execute("UPDATE UserLevels SET xp = ?, level = ?, lastMessageTime = ? WHERE userId = ? AND serverId = ?", (0 + (xp-nextLevelXp), userLevelData[3] + 1, int(time.time()), message.author.id, message.guild.id))
                    conn.commit()
                    await channel.send(f"Congratulations {message.author.mention}! You have leveled up to level {userLevelData[3] + 1}!")
                else:
                    cur.execute("UPDATE UserLevels SET xp = ?, lastMessageTime = ? WHERE userId = ? AND serverId = ?", (userLevelData[2] + xp, int(time.time()), message.author.id, message.guild.id))
                    conn.commit()

@tree.command(name="level", description="View your level")
@app_commands.describe(user = "The user to view the level of if not yourself")
async def self(interaction: discord.Interaction, user: discord.Member = None):
    if user == None:
        user = interaction.user
        
    # Load the background image
    try:
        background = Image.open(f"./userbackgrounds/{user.id}.png").convert("RGBA")
    except:
        background = Image.open("background.png").convert("RGBA")
    background = background.resize((500, 150))  # Resize background to match desired dimensions

    # Create a transparent overlay image
    overlay_width = 470
    overlay_height = 120
    overlay = Image.new("RGBA", (overlay_width, overlay_height), (0, 0, 0, 99))  # 85% transparent black overlay

    # Paste the overlay onto the background image
    paste_x = (background.width - overlay_width) // 2
    paste_y = (background.height - overlay_height) // 2
    background.paste(overlay, (paste_x, paste_y), overlay)

    # Load the user's profile picture
    avatar = await user.avatar.read()
    pfp = Image.open(io.BytesIO(avatar)).convert("RGBA")

    # Resize and round the profile picture
    pfp = pfp.resize((100, 100))
    mask = Image.new("L", pfp.size, 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, 100, 100), fill=255)
    pfp.putalpha(mask)

    # Calculate the position to place the profile picture
    pfp_x = 20
    pfp_y = (background.height - pfp.height) // 2

    # Paste the profile picture onto the background image
    background.paste(pfp, (pfp_x, pfp_y), pfp)

    # Draw text on the image
    draw = ImageDraw.Draw(background)

    # Define the font and font size for the text
    font = ImageFont.truetype("arial.ttf", 18)

    # Define the text to display
    
    cur.execute("SELECT xp, level FROM UserLevels WHERE userId = ? AND serverId = ?", (user.id, user.guild.id))
    result = cur.fetchone()
    if result == None:
        xp = 0
        level = 0
    else:
        xp = result[0]
        level = result[1]
    xp_remaining = 5 * (level * level) + 50 * level + 100 - xp

    # Calculate the position to place the text
    text_x = 150
    text_y = 20

    # Draw the text on the image
    draw.text((text_x + 220, text_y + 30), f"Level: {level}", font=font, fill="white")
    draw.text((text_x, text_y + 30), f"XP Remaining: {xp_remaining}", font=font, fill="white")

    # Calculate the progress percentage
    progress_percentage = (xp / (5 * (level * level) + 50 * level + 100)) * 100

    # Calculate the dimensions of the progress bar
    progress_bar_width = 300
    progress_bar_height = 15
    progress_width = int(progress_bar_width * (progress_percentage / 100))

    # Calculate the position of the progress bar
    progress_bar_x = text_x
    progress_bar_y = text_y + 60

    # Draw the filled portion of the progress bar
    border_radius = progress_bar_height // 2
    draw.rounded_rectangle([progress_bar_x, progress_bar_y, progress_bar_x + progress_width, progress_bar_y + progress_bar_height],
                            radius=border_radius, fill=(100, 100, 255))  # Blue color with RGB values

    # Draw the outline of the progress bar
    draw.rounded_rectangle([progress_bar_x, progress_bar_y, progress_bar_x + progress_bar_width, progress_bar_y + progress_bar_height],
                        radius=border_radius, outline="white", width=1)

    # Save the modified image
    buffer = io.BytesIO()
    background.resize((250, 75), resample=Image.LANCZOS)
    background.save(buffer, format="PNG")
    buffer.seek(0)
    file = discord.File(buffer, filename="output.png")
    await interaction.response.send_message(file=file)

@tree.command(name="background", description="Set your background")
@app_commands.describe(image = "The image to set as your background, will fit to 500x150, centered")
async def self(interaction: discord.Interaction, image: discord.Attachment = None):
    if image != None:
        image = await image.read()
        with open(f"./userbackgrounds/{interaction.user.id}.png", "wb") as f:
            f.write(image)
        loaded = Image.open(f"./userbackgrounds/{interaction.user.id}.png")
        newImage = Image.new("RGBA", (500, 150), (0, 0, 0, 0))
        loaded = loaded.resize((500, int(loaded.height * (500 / loaded.width))))
        x = (newImage.width - loaded.width) // 2
        y = (newImage.height - loaded.height) // 2
        newImage.paste(loaded, (x, y))
        newImage.save(f"./userbackgrounds/{interaction.user.id}.png")
        await interaction.response.send_message(f"Set your background to the image you provided")
    else:
        try:
            os.remove(f"./userbackgrounds/{interaction.user.id}.png")
            await interaction.response.send_message(f"Image reset to default. If you'd like to upload a new image, please provide a file", ephemeral=True)
        except:
            await interaction.response.send_message(f"You don't have a custom background set, to upload a new image, please provide a file", ephemeral=True)

@tree.command(name = "leaderboard", description = "View the server's leaderboard")
async def self(interaction: discord.Interaction):
    cur.execute("SELECT * FROM UserLevels WHERE serverId = ? ORDER BY level DESC, xp DESC", (interaction.guild.id,))
    result = cur.fetchall()
    embed = discord.Embed(title = "Server Leaderboard", description = "", color = 0xffa500)
    count = 1
    for user in result:
        member = interaction.guild.get_member(user[0])
        if member != None:
            embed.description += f"{count}. {member.mention} - Level {user[3]} - {user[2]}xp\n"
            count += 1
    
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_message(message):
    approvalLogging(message)
    await levelSystem(message)

@bot.event
async def on_member_ban(guild, member):
    cur.execute("SELECT actionLogChannelId FROM ServerSettings WHERE serverId = ?", (guild.id,))
    result = cur.fetchone()
    if result[0] != None and result[0] != 0:
        channel = guild.get_channel(result[0])
        await channel.send(f"{member.name} was banned")

@bot.event
async def on_member_unban(guild, user):
    cur.execute("SELECT actionLogChannelId FROM ServerSettings WHERE serverId = ?", (guild.id,))
    result = cur.fetchone()
    if result[0] != None and result[0] != 0:
        channel = guild.get_channel(result[0])
        await channel.send(f"{user.name} was unbanned")

@bot.event
async def on_member_kick(guild, member):
    cur.execute("SELECT actionLogChannelId FROM ServerSettings WHERE serverId = ?", (guild.id,))
    result = cur.fetchone()
    if result[0] != None and result[0] != 0:
        channel = guild.get_channel(result[0])
        await channel.send(f"{member.name} was kicked")

@bot.event
async def on_message_delete(message):
    if message.author.bot == False:
        cur.execute("SELECT messageLogChannelId FROM ServerSettings WHERE serverId = ?", (message.guild.id,))
        result = cur.fetchone()
        print(result)
        if result[0] != None and result[0] != 0:
            channel = message.guild.get_channel(result[0])
            embed = discord.Embed(title = f"{message.author} deleted a message in {message.channel.name}", description=f"Message {message.id} deleted from <#{message.channel.id}>\n**Content:** {message.content}", timestamp=datetime.datetime.now(), color=0xFF0000)
            attachmentNumber = 1
            for attachment in message.attachments:
                embed.add_field(name="Attachment " + str(attachmentNumber),value=f"[{attachment.filename}]({attachment.url})")
                attachmentNumber += 1
            await channel.send(embed=embed)

@bot.event
async def on_bulk_message_delete(messages):
    cur.execute("SELECT messageLogChannelId FROM ServerSettings WHERE serverId = ?", (messages[0].guild.id,))
    result = cur.fetchone()
    if result[0] != None and result[0] != 0:
        channel = messages[0].guild.get_channel(result[0])
        allofmessages = ""
        for message in messages:
            if message.author.bot == False:
                allofmessages += f"[{message.created_at.strftime('%m/%d/%Y,  %H:%M:%S%Z')}] ({str(message.author)} - {str(message.author.id)}) [{str(message.id)}]: {message.content}\n\n"
        with open('log.txt', 'w') as f:
            try:
                f.write(allofmessages)
            except:
                allofmessages = allofmessages.replace("\n", " newline ")
                split = allofmessages.split()
                for word in split:
                    try:
                        if word == "newline":
                            f.write("\n")
                        else:
                            f.write(f"{word} ")
                    except:
                        f.write("(emoji?) ")
        await channel.send("Bulk message deletion:", file=discord.File("./log.txt", filename="log.txt"))
        os.remove("./log.txt")

@bot.event
async def on_message_edit(before, after):
    if before.author.bot == False:
        cur.execute("SELECT messageLogChannelId FROM ServerSettings WHERE serverId = ?", (before.guild.id,))
        result = cur.fetchone()
        if result[0] != None and result[0] != 0:
            if before.content != after.content:
                channel = before.guild.get_channel(result[0])
                embed = discord.Embed(title = f"{before.author} edited a message in {before.channel.name}", description=f"Message {before.id} edited in <#{before.channel.id}>\n`Before:` {before.content}\n`After: ` {after.content}", timestamp=datetime.datetime.now(), color=0xffa500)
                await channel.send(embed=embed)

bot.run(botToken)
