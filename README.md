# escoteiros-app

Aplicação que consulta periodicamente uma API de artigos e publica no Discord os itens novos/atualizados recentemente.

## Pré-requisitos

- **Runtime**: Node.js **18+** (recomendado Node.js 20 LTS).
- **Gerenciador de pacotes**: `npm` (ou compatível, como `pnpm`/`yarn`, se preferir).
- **Acesso de rede**:
  - Saída HTTPS para a API de artigos.
  - Acesso à API do Discord.
- **Credenciais e IDs**:
  - Token de bot do Discord válido.
  - ID do canal de destino no Discord.

## Instalação

1. Clone o repositório:

   ```bash
   git clone <url-do-repositorio>
   cd escoteiros-app
   ```

2. Instale as dependências:

   ```bash
   npm install
   ```

3. Configure as variáveis de ambiente (ver seção [Configuração](#configuração)).

## Execução

Com variáveis já exportadas no shell (ou carregadas via arquivo `.env` conforme seu fluxo):

```bash
npm start
```

> Se o projeto usar um script alternativo (por exemplo `npm run dev`), ajuste de acordo com o `package.json`.

## Configuração

A aplicação depende das variáveis abaixo:

- `DISCORD_TOKEN` (**obrigatória**): token do bot do Discord.
- `CHANNEL_ID` (**obrigatória**): ID do canal onde as mensagens serão publicadas.
- `POLLING_INTERVAL_MS` (**obrigatória/recomendada**): intervalo de polling em milissegundos.
- `LOCALE` (**obrigatória/recomendada**): locale usado na consulta da API (ex.: `pt-BR`).
- `PER_PAGE` (**obrigatória/recomendada**): quantidade de artigos por página na API (ex.: `100`).

Exemplo:

```bash
export DISCORD_TOKEN="seu_token_aqui"
export CHANNEL_ID="123456789012345678"
export POLLING_INTERVAL_MS="60000"
export LOCALE="pt-BR"
export PER_PAGE="100"
```

## Paginação e critério de “atualizado recentemente”

### Paginação

A API é consultada por páginas. Com:

- `PER_PAGE=100`
- total de `476` artigos

o sistema precisa percorrer **5 páginas**:

1. Página 1 → 100 artigos
2. Página 2 → 100 artigos
3. Página 3 → 100 artigos
4. Página 4 → 100 artigos
5. Página 5 → 76 artigos

Total: 476 artigos processados no ciclo.

### Como o sistema decide “artigo atualizado recentemente”

Em cada ciclo de polling, o sistema compara o campo de atualização do artigo (normalmente `updated_at`) com a janela temporal de interesse (baseada no último polling bem-sucedido / intervalo configurado).

Regra prática:

- Se `updated_at` estiver dentro da janela recente, o artigo é considerado “atualizado recentemente” e pode ser publicado.
- Se estiver fora da janela, ele é ignorado naquele ciclo.

## Exemplo de mensagem no Discord

Formato sugerido da publicação:

```text
📰 Novo artigo atualizado
Title: Como organizar um acampamento escoteiro
URL: https://exemplo.org/artigos/como-organizar-um-acampamento
```

Ou, em formato direto com `title` e `html_url`:

```text
{title} — {html_url}
```

Exemplo:

```text
Como organizar um acampamento escoteiro — https://exemplo.org/artigos/como-organizar-um-acampamento
```

## Troubleshooting

### 1) Token inválido (`DISCORD_TOKEN`)

**Sintomas**
- Erros de autenticação (401) ao inicializar cliente/bot.
- Bot não conecta.

**Verificações**
- Confirme se o token foi copiado corretamente (sem espaços extras/aspas indevidas).
- Gere um novo token no Discord Developer Portal, se necessário.
- Reinicie a aplicação após atualizar o token.

### 2) Falta de permissão no canal (`CHANNEL_ID`)

**Sintomas**
- Bot conecta, mas não envia mensagens.
- Erros de permissão (`Missing Access`, `Missing Permissions`, 403).

**Verificações**
- Confirme se o `CHANNEL_ID` está correto.
- Verifique se o bot está no servidor.
- Garanta permissões de `View Channel` e `Send Messages` no canal alvo.

### 3) Falha HTTP na API de artigos

**Sintomas**
- Timeouts, erros 4xx/5xx, ou ausência de novos dados.

**Verificações**
- Valide conectividade de rede e DNS.
- Confira status e disponibilidade da API.
- Revise parâmetros enviados (`locale`, `per_page`, paginação).
- Implemente/ajuste retry com backoff e logs para diagnóstico.

## Boas práticas operacionais

- Defina `POLLING_INTERVAL_MS` com valor que equilibre atualização e limite de requisições.
- Monitore logs para detectar falhas de autenticação, permissão e instabilidade da API.
- Evite publicar duplicados mantendo controle do último processamento (timestamp/ID).
