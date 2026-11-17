# Campus Viva — roteiro e envio

## Seminário de 18 minutos

| Tempo | Tópico e ação |
| --- | --- |
| 0–2 min | Identificar integrantes, explicar o problema e o objetivo do Campus Viva. |
| 2–5 min | Mostrar o grafo inicial. Explicar vértices, sentido, pesos e o ciclo 1 → 2 → 3 → 1. |
| 5–8 min | Justificar Dijkstra com a Matriz da Parte 3 em mãos. Explicar por que BFS ignora pesos e quando Bellman-Ford seria necessário. |
| 8–11 min | Mostrar React, controller FastAPI, repositório e Dijkstra; explicar lista de adjacência, heap e predecessores. Distinguir modo local e Atlas. |
| 11–15 min | Com a tela compartilhada, calcular Bloco A → Laboratório de Informática (250 m) e Bloco A → Laboratório de Carcanhas (sem caminho). Mostrar também a origem igual ao destino (0 m). |
| 15–18 min | Discutir os resultados, o que ficou demonstrativo e os próximos passos. |

Distribuir as falas entre todos os integrantes e pedir que cada pessoa se identifique no início da sua fala. Gravar com o software em execução; conferir áudio, legibilidade, duração de 15–20 minutos e acesso do professor. Este arquivo é um roteiro; não substitui a gravação.

## O que enviar no Teams em 24/11/2026

1. PDF do Caderno Técnico.
2. Link acessível do vídeo ou arquivo conforme a atividade.
3. URL do repositório com fontes, dados, dependências e instruções.
4. PDF do Documento de Casos de Teste, também dentro do repositório.

## Pendências antes do envio

- [ ] Inserir nomes completos e RAs reais no README e nos PDFs. Não havia lista validada da equipe para preencher.
- [ ] Conferir Parte 2 e Matriz da Parte 3: confirmar Dijkstra como aplicável ou registrar ao professor a mudança com justificativa. A Matriz não foi fornecida; RT-02 permanece pendente de evidência.
- [ ] Gravar e disponibilizar o seminário com todos os integrantes (Produto 2).
- [ ] Publicar a cópia final no repositório da equipe, conceder acesso ao professor, verificar o link e registrar tag ou commit (Produto 3).
- [ ] Fazer uma instalação limpa em outra máquina e realizar a demonstração no navegador.
- [ ] Enviar os quatro itens no Teams.

## Mapa de aderência técnica

| Critério | Evidência |
| --- | --- |
| RT-01, RT-05 | Núcleo Python original da equipe preservado; FastAPI chama CampusMap.dijkstra. |
| RT-02 | Justificativa técnica no caderno; falta a Matriz original para confirmar coerência documental. |
| RT-03, RT-04 | Dados do campus carregados pelo repositório; arestas convertidas em lista de adjacência. |
| RT-06 | API fornece nomes, custo e trechos. Planejador React consome a resposta e destaca o caminho real. |
| RT-07, RT-08 | Testes de ponto inválido, peso negativo rejeitado, ausência de caminho e origem igual ao destino. |
| RT-09 | Separação entre frontend, controllers, repositório e algoritmo. |
| RT-10 | Execução local sem credenciais descrita no README; falta URL do repositório e ensaio em outra máquina. |

Atlas e Vercel não foram homologados e não são exigidos para reproduzir a entrega local. Administração, favoritos e avisos continuam demonstrativos; o escopo funcional entregue é o planejamento de rotas.
