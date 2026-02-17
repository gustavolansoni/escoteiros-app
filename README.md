# escoteiros-app

Bot Discord para monitorar artigos do Discord Help Center e publicar atualizações em um canal.

## Estrutura

- `src/bot.py`: ponto de entrada do bot, comando `/latest_article`, scheduler e modo `RUN_ONCE`.
- `src/discord_help_center.py`: cliente da API paginada com retry/backoff.
- `src/state_store.py`: persistência do último artigo publicado (`data/last_seen.json`).
- `.github/workflows/publish-discord-updates.yml`: execução automática no GitHub Actions.

## Variáveis de ambiente

- `DISCORD_TOKEN` (obrigatória): token do bot no Discord.
- `CHANNEL_ID` (obrigatória): ID do canal onde publicar.
- `CHECK_INTERVAL_MINUTES` (opcional): intervalo do scheduler local (default `10`).
- `RUN_ONCE` (opcional): quando `true`, roda um ciclo e encerra (ideal para Actions).

## Desenvolvimento local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DISCORD_TOKEN="..."
export CHANNEL_ID="..."
python src/bot.py
```

## Produção com GitHub Actions (sem `.env`)

### 1) Configurar Secrets
No repositório em **Settings → Secrets and variables → Actions → Secrets**:

- `DISCORD_TOKEN`
- `CHANNEL_ID`

### 2) Configurar Variables
No repositório em **Settings → Secrets and variables → Actions → Variables**:

- `CHECK_INTERVAL_MINUTES` (ex.: `10`)

> O workflow usa `RUN_ONCE=true`, então cada execução processa um único ciclo e encerra.

### 3) Workflow automático
Arquivo: `.github/workflows/publish-discord-updates.yml`

Disparos:
- `schedule`: a cada 10 minutos
- `workflow_dispatch`: manual

O job:
1. Faz checkout do repositório
2. Instala Python e dependências
3. Injeta `secrets`/`vars` em `env`
4. Executa `python src/bot.py` em modo ciclo único

## Formato de mensagem publicada

```text
### Artigo Atualizado
- {title}
{html_url}
```

Exemplo:

```text
### Artigo Atualizado
- Age Assurance Update FAQ
https://support.discord.com/hc/en-us/articles/38332670254231-Age-Assurance-Update-FAQ
```
