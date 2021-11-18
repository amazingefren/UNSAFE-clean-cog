from redbot.core import commands
from redbot.core.utils.mod import mass_purge
from datetime import datetime, timedelta
import asyncio
from threading import Timer
import discord


class Clean(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def test(self, ctx):
        await ctx.send("Gilbert is a bitch")
    
    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        loop = asyncio.get_event_loop()
        task1 = loop.create_task(self.delete_bot(ctx, 0.003))
        loop.run_until_complete(asyncio.gather(task1))

    async def delete_bot(self, ctx, delay):
        channel = ctx.channel

        prefixes = await self.bot.get_prefix(ctx.message)
        if isinstance(prefixes, str):
            prefixes = [prefixes]

        if "" in prefixes:
            prefixes.remove("")

        cc_cog = self.bot.get_cog("CustomCommands")
        if cc_cog is not None:
            command_names = await cc_cog.get_command_names(ctx.guild)
            is_cc = lambda name: name in command_names
        else:
            is_cc = lambda name: False

        alias_cog = self.bot.get_cog("Alias")
        
        if alias_cog is not None:
            alias_names = set(
                a.name for a in await alias_cog._aliases.get_global_aliases()
            ) | set(a.name for a in await alias_cog._aliases.get_guild_aliases(ctx.guild))
            is_alias = lambda name: name in alias_names
        else:
            is_alias = lambda name: False

        bot_id = self.bot.user.id

        def check(m):
            if m.author.id == bot_id:
                return True
            elif m == ctx.message:
                return True
            p = discord.utils.find(m.content.startswith, prefixes)
            if p and len(p) > 0:
                cmd_name = m.content[len(p) :].split(" ")[0]
                return (
                    bool(self.bot.get_command(cmd_name)) or is_alias(cmd_name) or is_cc(cmd_name)
                )
            return False

        to_delete = await self.get_messages_for_deletion(
            channel=channel,
            number=10,
            check=check,
            before=ctx.message,
            delete_pinned=False
        )

        to_delete.append(ctx.message)

        await asyncio.sleep(delay)
        await mass_purge(to_delete, channel)

    @staticmethod
    async def get_messages_for_deletion(
        *,
        channel,
        number = None,
        check = lambda x: True,
        limit = None,
        before = None,
        after = None,
        delete_pinned = False,
    ):
        two_weeks_ago = datetime.utcnow() - timedelta(days=14, minutes=-5)

        def message_filter(message):
            return (
                check(message)
                and message.created_at > two_weeks_ago
                and (delete_pinned or not message.pinned)
            )

        if after:
            if isinstance(after, discord.Message):
                after = after.created_at
            after = max(after, two_weeks_ago)

        collected = []
        async for message in channel.history(
            limit=limit, before=before, after=after, oldest_first=False
        ):
            if message.created_at < two_weeks_ago:
                break
            if message_filter(message):
                collected.append(message)
                if number is not None and number <= len(collected):
                    break

        return collected
