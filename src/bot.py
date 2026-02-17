import logging
import os
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import tasks

from discord_help_center import DiscordHelpCenterClient, filter_articles_newer_than, filter_recent_articles
from state_store import LastSeenStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("discord-help-bot")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID_RAW = os.getenv("CHANNEL_ID")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "10"))
RUN_ONCE = os.getenv("RUN_ONCE", "false").lower() in {"1", "true", "yes"}
RECENT_WINDOW_MINUTES = int(os.getenv("RECENT_WINDOW_MINUTES", os.getenv("CHECK_INTERVAL_MINUTES", "10")))

if not DISCORD_TOKEN:
    raise RuntimeError("Variável DISCORD_TOKEN não configurada")

if not CHANNEL_ID_RAW:
    raise RuntimeError("Variável CHANNEL_ID não configurada")

CHANNEL_ID = int(CHANNEL_ID_RAW)


class DiscordHelpBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.store = LastSeenStore()
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.help_client: Optional[DiscordHelpCenterClient] = None

    async def setup_hook(self) -> None:
        self.http_session = aiohttp.ClientSession()
        self.help_client = DiscordHelpCenterClient(self.http_session, logger)

        @self.tree.command(name="latest_article", description="Publica o artigo mais recente do Discord Help Center")
        async def latest_article(interaction: discord.Interaction) -> None:
            await interaction.response.defer(thinking=True)
            article = await self.get_latest_article()
            if not article:
                await interaction.followup.send("Não encontrei artigos no momento.")
                return

            await self.publish_article(CHANNEL_ID, article.title, article.html_url)
            self.store.save(article.article_id, article.updated_at)
            await interaction.followup.send("Artigo mais recente publicado com sucesso.")

    async def on_ready(self):
        logger.info("Bot conectado como %s", self.user)

        if RUN_ONCE:
            logger.info("RUN_ONCE ativo: executando um único ciclo e encerrando")
            await run_check_cycle()
            await self.close()
            return

        await self.tree.sync()
        if not periodic_check.is_running():
            periodic_check.start()

    async def close(self):
        if self.http_session:
            await self.http_session.close()
        await super().close()

    async def get_latest_article(self):
        if not self.help_client:
            raise RuntimeError("Cliente HTTP não inicializado")

        articles = await self.help_client.fetch_all_articles()
        if not articles:
            return None

        return sorted(articles, key=lambda a: (a.updated_datetime(), a.article_id), reverse=True)[0]

    async def publish_article(self, channel_id: int, title: str, url: str) -> None:
        channel = self.get_channel(channel_id)
        if channel is None:
            channel = await self.fetch_channel(channel_id)

        message = f"### Artigo Atualizado\n- {title}\n{url}"
        await channel.send(message)
        logger.info("Artigo publicado no canal %s: %s", channel_id, title)


bot = DiscordHelpBot()


async def run_check_cycle() -> None:
    logger.info("Iniciando ciclo de checagem")

    if not bot.help_client:
        logger.warning("Cliente da API ainda não disponível")
        return

    last_seen = bot.store.load()
    logger.info("Último estado conhecido: %s", last_seen)

    try:
        all_articles = await bot.help_client.fetch_all_articles()
    except Exception as exc:
        logger.exception("Falha ao ler API do Help Center: %s", exc)
        return

    last_updated_at = last_seen.get("updated_at")
    last_article_id = last_seen.get("article_id")

    if last_updated_at:
        new_articles = filter_articles_newer_than(
            all_articles,
            last_updated_at=last_updated_at,
            last_article_id=last_article_id,
        )
    else:
        new_articles = filter_recent_articles(
            all_articles,
            recent_minutes=RECENT_WINDOW_MINUTES,
        )
        logger.info(
            "Sem estado anterior. Aplicando janela de recentes: últimos %s minutos (%s artigos)",
            RECENT_WINDOW_MINUTES,
            len(new_articles),
        )

    if not new_articles:
        logger.info("Nenhum artigo novo para publicar")
        return

    logger.info("Encontrados %s artigos novos", len(new_articles))
    # Publica do mais antigo para o mais novo entre os novos
    for article in reversed(new_articles):
        try:
            await bot.publish_article(CHANNEL_ID, article.title, article.html_url)
            bot.store.save(article.article_id, article.updated_at)
        except Exception as exc:
            logger.exception("Falha ao publicar artigo %s: %s", article.article_id, exc)
            break


@tasks.loop(minutes=CHECK_INTERVAL_MINUTES)
async def periodic_check():
    await run_check_cycle()


@periodic_check.before_loop
async def before_periodic_check():
    await bot.wait_until_ready()
    logger.info("Scheduler iniciado com intervalo de %s minutos", CHECK_INTERVAL_MINUTES)


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
