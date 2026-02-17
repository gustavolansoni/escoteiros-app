# escoteiros-app

Bot Discord para monitorar artigos do Discord Help Center e publicar atualizações em um canal.

## Estrutura

- `src/bot.py`: ponto de entrada do bot, comando `/latest_article` e rotina automática.
- `src/discord_help_center.py`: cliente da API paginada do Help Center com retry/backoff.
- `src/state_store.py`: persistência de último artigo publicado (`data/last_seen.json`).
- `.env.example`: variáveis necessárias para execução.

## Variáveis de ambiente

Copie `.env.example` para `.env` e preencha:

- `DISCORD_TOKEN`: token do bot no Discord Developer Portal.
- `CHANNEL_ID`: ID do canal onde as mensagens serão publicadas.
- `CHECK_INTERVAL_MINUTES`: intervalo do scheduler em minutos (default: `10`).

## Execução local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export $(cat .env | xargs)
python src/bot.py
```

## O que o bot faz

1. Consome `https://support.discord.com/api/v2/help_center/en-us/articles.json`.
2. Lê paginação com `page=1..page_count` e `per_page=100`.
3. Usa campos `count`, `page_count`, `next_page` e `articles` para log/controle.
4. Filtra artigos usando `updated_at` e estado local em `data/last_seen.json` para evitar duplicatas.
5. Publica mensagens no formato:

```text
### Artigo Atualizado
- {title}
{html_url}
```

6. Disponibiliza comando slash `/latest_article` para publicar manualmente o artigo mais recente.
7. Executa checagem automática periódica (`CHECK_INTERVAL_MINUTES`) com logs básicos e retry/backoff HTTP.

## Exemplo de saída

```text
### Artigo Atualizado
- How to Report Content to Discord
https://support.discord.com/hc/en-us/articles/360000291932
```
