import discord
import asyncio
import os
import datetime
import ast
import time
import traceback
from discord.ext import commands
from pymongo import MongoClient, InsertOne
import motor.motor_asyncio

client = commands.Bot(command_prefix = ',', intents=discord.Intents.all())
cluster = motor.motor_asyncio.AsyncIOMotorClient('mongodb+srv://layz:8TtxtxOQrxDZKgUm@layzbot.avrfvch.mongodb.net/?retryWrites=true&w=majority')
collection = cluster.ecodb.coldb
client.remove_command('help')

def insert_returns(body):
  if isinstance(body[-1], ast.Expr):
    body[-1] = ast.Return(body[-1].value)
    ast.fix_missing_locations(body[-1])
    if isinstance(body[-1], ast.If):
      insert_returns(body[-1].body)
      insert_returns(body[-1].orelse)
    if isinstance(body[-1], ast.With):
      insert_returns(body[-1].body)


async def execute_python_code(code, env: dict = None):
  fn_name = "_eval_expr"
  cmd = "\n".join(f" {i}" for i in code.splitlines())
  body = f"async def {fn_name}():\n{cmd}"
  parsed = ast.parse(body)
  body = parsed.body[0].body
  insert_returns(body)
  env = {'__import__': __import__, **env}
  exec(compile(parsed, filename="<ast>", mode="exec"), env)
  result = (await eval(f"{fn_name}()", env))
  return result

@client.command()
async def e(ctx, *, code):
    if ctx.author.id in [749310266625228921]:
        try:
            result = await execute_python_code(code, {
                "discord": discord,
                "disnake": discord,
                "commands": commands,
                "ctx": ctx,
                "client": client,
                "bot": client,
                "cluster": cluster,
                "collection": cluster.ecodb.coldb,
                })
            if not "await ctx." in code:
                embed = discord.Embed(title='Eval', description=f'```{result}```', color=discord.Color.blue())
                await ctx.send(embed=embed)
        except Exception as error:
            embed = discord.Embed(title='Error eval', description=f'```{error}```', color=discord.Color.red())
            await ctx.send(embed=embed)
    else:
        pass

@client.tree.command(name="ping", description="Bot's latency/ping")
async def ping(interaction: discord.Interaction):
    bot_latency = round(client.latency * 1000)
    await interaction.response.send_message(f"{bot_latency} ms.")

@commands.is_owner()
@client.command()
async def reload(ctx):
    reloaded_cogs = []
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                await client.unload_extension(f'cogs.{filename[:-3]}')
                await client.load_extension(f'cogs.{filename[:-3]}')
                reloaded_cogs.append(f':white_check_mark: {filename[:-3]}\n')
            except Exception as e:
                error = traceback.format_exc()
                reloaded_cogs.append(f':x: {filename[:-3]} {e}\n')
    await ctx.send(''.join(reloaded_cogs))

@commands.is_owner()
@client.command()
async def unload(ctx, extension):
    if str(ctx.author.id) == '749310266625228921':
        await client.unload_extension(f'cogs.{extension}')
        await ctx.send(f'Ког {extension} выключен')
    else:
        pass

@client.command()
async def load(ctx, extension):
    try:
        if str(ctx.author.id) == '749310266625228921':
            await client.load_extension(f'cogs.{extension}')
            await ctx.send(f'Ког {extension} загружен')
        else:
            pass
    except Exception as error:
        await ctx.reply(error)  

@client.event
async def on_ready():
    await client.tree.sync()
    start = time.time()
    try:
        requests = []
        for guild in client.guilds:
            members = [member for member in guild.members if not member.bot]
            for member in members:
                existing_doc = await collection.find_one({'_id': member.id})
                if existing_doc is None:
                    post = {
                        '_id': member.id,
                        'coin': 100,
                        'voda': 0,
                        'rep': 0,
                        'job': 'jobless',
                        'exp': 0
                    }
                    requests.append(InsertOne(post))
                else:
                    update = {
                        '$set': {
                            'coin': existing_doc['coin'] + 100,
                            'voda': existing_doc['voda'],
                            'rep': existing_doc['rep'],
                            'job': existing_doc['job'],
                            'exp': existing_doc['exp']
                        }
                    }
                    requests.append(UpdateOne({'_id': member.id}, update))
            await collection.bulk_write(requests)
    except Exception as error:
        print(error)
    end = time.time() - start
    print(f'connected, заносение в бд {end}')


@client.event
async def on_member_join(member):
    post = {
        '_id': member.id,
        'coin': 100,
        'voda': 0,
        'rep': 0,
        'job': 'jobless',
        'exp': 0
    }
    if client.get_user(member.id).bot:
        pass
    if await collection.count_documents({'_id': member.id}) == 0 and not client.get_user(member.id).bot:
        await collection.insert_one(post)
    
@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.CommandOnCooldown):
        em = discord.Embed(title=f"Ошибка", description=f"Попробуй через {error.retry_after:.2f}s.", color=discord.Color.red())
        await ctx.send(embed=em)
    elif isinstance(error, commands.MissingArgument):
        em = discord.Embed(title="Ошибка", description=f"Вы не указали аргумент.", color=discord.Color.red())
        await ctx.send(embed=em)
    elif isinstance(error, commands.MissingPermissions):
        em = discord.Embed(title="Ошибка", description=f"У вас недостаточно прав.", color=discord.Color.red())
        await ctx.send(embed=em)
    elif isinstance(error, commands.NotOwner):
        em = discord.Embed(title="Ошибка", description=f"Вы не создатель бота :rage:.", color=discord.Color.red())
        await ctx.send(embed=em)
    else:
        await ctx.send(f'ошибка {error}')

async def load():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await client.load_extension(f"cogs.{filename[:-3]}")
            print(f'{filename[:-3]} загрузился')

async def main():
    async with client:
        await load()
        await client.start('Nzg2NjM1OTg5OTY3MDQ0NjU4.GHbZw2.VzmBxBdeITMv3ZypRob3lAfqVFd6kMZ710YiwU', reconnect=True)

asyncio.run(main())
