# Campus Viva — entrega final de Estrutura de Dados

Navegação em campus com React, FastAPI e Dijkstra em Python. Equipe: preencher nome completo e RA de cada integrante antes do envio. Prazo indicado na especificação: 24/11/2026, no Teams.

## Repositórios

Clone os dois projetos na mesma pasta, com os nomes locais abaixo:

```bash
git clone https://github.com/SchiavoEnzo/campus-universitario-estruturas-de-dados-frontend.git frontend
git clone https://github.com/SchiavoEnzo/campus-universitario-estruturas-de-dados-backend.git backend
```

## Execução local sem credenciais

Use Python 3.12 e Node.js compatível com Vite 7 (Linux: ambiente usado para verificação). Na raiz:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
CAMPUS_STORAGE=memory CAMPUS_DATASET=original python -m uvicorn app:app --port 8000
```

No PowerShell, ative com `./.venv/Scripts/Activate.ps1`; antes de iniciar Uvicorn, defina `$env:CAMPUS_STORAGE='memory'` e `$env:CAMPUS_DATASET='original'`.

Em outro terminal, a partir da raiz:

```bash
cd frontend
npm ci
npm run dev
```

Abra o endereço Local informado pelo Vite. Em **Planejar rota**, selecione **Bloco A → Laboratório de Informática** por distância e clique em **Calcular rota**. Resultado esperado: Bloco A → Biblioteca → Laboratório de Informática, 250 m. Selecione **Bloco A → Laboratório de Carcanhas** para ver a mensagem de ausência de caminho. No mesmo mapa, **Bloco A → Bloco A** retorna 0 m. Use `CAMPUS_DATASET=frontend` no backend para iniciar com o mapa expandido. Reiniciar o modo em memória descarta alterações. As demais telas React usam dados de demonstração.

Swagger: http://localhost:8000/docs. API: `GET /api/graph`, `POST /api/routes`. Os endpoints administrativos estão documentados em backend/docs/README_API.md.

## Testes e entrega

No ambiente virtual, na pasta backend:

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Dados: backend/data/frontend.json e backend/campus/campus_navigation.py. Casos, entradas e saídas: backend/docs/CampusViva_Casos_de_Teste.pdf. As duas pastas frontend/ e backend/ contêm fontes e dependências. backend/docs/ contém caderno, testes, roteiro e checklist. Não inclua arquivos .env, tokens ou URIs privadas no Git.

## Vercel e MongoDB Atlas

Para publicar, use a pasta backend/ como raiz do projeto Vercel. Configure MONGODB_URI, MONGODB_DB, CAMPUS_DATASET e CORS_ORIGINS. O modo em memória não é usado no Vercel. Para o React hospedado separadamente, informe VITE_API_URL no build e autorize a origem do frontend na API. Valide /api/graph após provisionar o Atlas. A nuvem é opcional para a avaliação local; não foi homologada nesta entrega.


## Configuração local com Atlas

A API carrega `.env` da pasta do backend. Defina `MONGODB_URI`, `MONGODB_DB=campus_viva`, `CAMPUS_DATASET=frontend` e `CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`. Não defina `CAMPUS_STORAGE=memory` para consultar o Atlas. O arquivo `.env` é ignorado pelo Git e deve permanecer privado.

```bash
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

O frontend local encaminha `/api` para essa API por meio do proxy do Vite. Em produção, `VITE_API_URL` seleciona a API na Vercel. O navegador nunca recebe a URI ou a senha do MongoDB: `GET /api/graph` consulta `campus_viva.graphs`, e `POST /api/routes` calcula rotas com esse grafo.

`ADMIN_TOKEN` autoriza criação, edição e exclusão de locais/conexões. Use uma credencial com pelo menos 32 caracteres e informe-a somente no formulário administrativo. Definir essa variável localmente não a configura na Vercel: produção precisa de configuração própria e redeploy. O banco local configurado pode ser o mesmo de produção; as alterações autorizadas nesse banco afetam o site publicado.


## Login e sessões

As contas de aplicação ficam em `campus_viva.users`, separadas dos usuários de acesso ao Atlas. Senhas são armazenadas com Argon2. `auth_sessions` contém apenas o hash do identificador de sessão, com expiração de 8 horas e revogação no logout/troca de senha; índices TTL removem registros vencidos. `auth_attempts` limita tentativas por conta em janelas de 15 minutos.

Endpoints: `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout` e `POST /api/auth/password`. O login envia cookie HttpOnly/Secure em produção. Edições por sessão validam origem, token CSRF, perfil administrativo e troca da senha inicial. O `ADMIN_TOKEN` continua disponível para automação previamente configurada; o frontend usa somente a sessão.

No frontend da Vercel, `VITE_API_URL` fica vazio e `vercel.json` encaminha `/api/*` para o backend. Isso mantém o cookie no domínio do site. Localmente, o proxy do Vite encaminha para a porta 8000. `CORS_ORIGINS` deve conter a origem exata do frontend.

Para provisionar as contas solicitadas, execute `.venv/bin/python scripts/create_demo_users.py` da pasta backend. O script preserva contas existentes e grava senhas iniciais somente em `.env.demo-users.json`, com permissão 600 e ignorado pelo Git. Veríssimo (`verissimo`, também aceita acento no login) e Enzo (`enzo`) são administradores e devem trocar a senha no primeiro acesso. Não há cadastro público nem recuperação de senha por email nesta implementação.
