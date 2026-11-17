# Campus Viva — Backend

API em Python 3.12 e FastAPI para calcular rotas no campus e persistir o grafo no MongoDB Atlas. O controller de rotas chama `CampusMap.dijkstra()` do arquivo fornecido, preservado em `campus/campus_navigation.py`. O menu de console continua independente.

## Rodar localmente

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

No PowerShell, use `.\.venv\Scripts\Activate.ps1` e `Copy-Item .env.example .env`.

Edite o `.env` e rode `python -m uvicorn app:app --reload --port 8000`. Abra <http://localhost:8000/docs> para testar os endpoints. `GET /api/health` verifica somente a aplicação; `GET /api/graph` verifica o acesso ao MongoDB e inicializa o mapa se ainda não existir.

| Variável | Uso |
| --- | --- |
| `MONGODB_URI` | URI do cluster obtida no Atlas em **Connect → Drivers**. Deve ficar no backend. |
| `MONGODB_DB` | Banco utilizado; padrão: `campus_viva`. |
| `CAMPUS_DATASET` | `original` preserva os quatro pontos e distâncias do Python; `frontend` carrega os 24 locais e 71 conexões do protótipo React, com os mesmos IDs. |
| `CORS_ORIGINS` | Origens autorizadas, separadas por vírgula; informe protocolo, domínio e porta, sem caminho. Inclua a origem do React publicado e/ou local. |
| `ADMIN_TOKEN` | Opcional. Token do tipo Bearer com no mínimo 32 caracteres para habilitar alterações. Gere com `python -c "import secrets; print(secrets.token_urlsafe(32))"`. |

No Atlas, crie um usuário de banco com `readWrite` somente para o banco escolhido e permita na lista de acesso os IPs de saída do ambiente que executa a API. Para o Vercel, confirme a estratégia de saída disponível no seu plano; se usar IPs fixos, autorize somente os IPs atribuídos. A senha do usuário de banco deve estar codificada para uso em URI, quando contiver caracteres reservados.

## Endpoints

| Método e caminho | Finalidade |
| --- | --- |
| GET `/api/health` | Disponibilidade da API |
| GET `/api/graph` | Grafo completo: `revision`, `nodes` e `edges` |
| POST `/api/routes` | Menor rota por distância ou tempo |
| POST `/api/points` | Criar ponto |
| PUT / DELETE `/api/points/{point_id}` | Atualizar ou remover ponto; remoção exclui suas conexões |
| PUT / DELETE `/api/connections/{origin}/{destination}` | Criar/atualizar ou remover uma conexão direcionada |

As alterações exigem `Authorization: Bearer <token>`. Conexões são de mão única; cadastre os dois sentidos se necessário. `PUT` substitui os campos da entidade, então envie o objeto completo. Para interromper um trecho no cálculo, atualize a conexão com `blocked: true`, preservando os outros campos. A edição por token é adequada a uma ferramenta de gestão ou serviço confiável; não coloque o token no bundle do React. Uma área administrativa pública exige autenticação por usuário ou um intermediário autenticado de servidor.

Com o mapa original, teste:

```bash
curl -s http://localhost:8000/api/routes \
  -H "Content-Type: application/json" \
  -d '{"origin":"1","destination":"3","criterion":"distance"}'
```

A resposta traz `found: true`, os três pontos (Bloco A → Biblioteca → Laboratório de Informática), os trechos e `distance: 250` metros. Quando não há caminho, retorna HTTP 200 com `found: false`, listas vazias e custos nulos. Ponto inexistente retorna 404, entrada inválida retorna 422, conflito de edição retorna 409 e indisponibilidade do banco retorna 503.

O cálculo ignora trechos bloqueados. Para `criterion: "time"`, conexões sem tempo cadastrado são ignoradas; os trechos do mapa Python original só têm distância. Com `accessible: true`, são utilizadas apenas conexões que tenham `accessible: true` cadastrado explicitamente.

## Conectar ao React

Configure `CAMPUS_DATASET=frontend` no backend para começar com o mesmo mapa da interface. No frontend, defina `VITE_API_URL=http://localhost:8000` no `.env.local` e reinicie o Vite. Em produção, use a URL HTTPS da API e gere um novo build do React após configurar essa variável.

```js
const base = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

async function callApi(path, init) {
  const res = await fetch(`${base}/api${path}`, init);
  if (!res.ok) throw new Error(`Falha na API (${res.status}).`);
  return res.json();
}

const graph = await callApi("/graph");
const route = await callApi("/routes", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    origin: "PORT-S",
    destination: "BIB",
    criterion: "distance",
    accessible: false
  })
});
```

Carregue o mapa e os seletores a partir de `graph.nodes` e `graph.edges`. Substitua o botão de exemplo por esse POST usando os valores selecionados; represente o resultado com `route.path`, `route.segments`, `distance` (metros) e `time` (minutos, quando disponível). Trate `found: false` separadamente de falhas HTTP. As chamadas acima são um guia; o frontend publicado não é alterado por este pacote.

## Publicar no Vercel

1. Suba os arquivos do backend em um repositório Git e importe-o como projeto no Vercel. Em um monorepo, aponte **Root Directory** para a pasta que contém `app.py`.
2. Use o preset FastAPI e mantenha o build padrão. `app.py` exporta `app`, `.python-version` indica Python 3.12 e `requirements.txt` declara as dependências.
3. Configure as variáveis na seção **Environment Variables** do projeto, antes do deploy. Use outro banco para Preview se também habilitar esse ambiente. Não envie o arquivo `.env` ao Git.
4. Depois do deploy, verifique `/api/health`, `/api/graph` e a chamada de rota em `/docs`.

Referências: [FastAPI no Vercel](https://vercel.com/docs/frameworks/backend/fastapi) e [conexão ao MongoDB Atlas](https://www.mongodb.com/docs/atlas/connect-to-database-deployment/).

## Persistência e testes

O banco mantém um documento por mapa na coleção `graphs`, com listas limitadas de pontos e conexões no mesmo documento. Alterações no grafo são atômicas e exigem que a revisão lida ainda seja a atual. A carga inicial é feita uma vez por mapa; reiniciar a API não apaga as edições.

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Os testes HTTP usam um repositório em memória para validar o comportamento da API sem credenciais. O acesso ao Atlas remoto e a publicação dependem da configuração do ambiente.
