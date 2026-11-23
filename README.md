# Laboratórios da Unidade II

**Dupla:** José Cássio e Felipe Baraúna

Os quatro laboratórios avaliados da Unidade II da disciplina de IA Agêntica, feitos sobre os notebooks de [silvaan/agentic-ai](https://github.com/silvaan/agentic-ai/tree/main/labs). Todos usam o mesmo domínio do nosso projeto da unidade, o [Assistente de Bancada](https://github.com/Jcassio-dev/assistente-bancada): montar circuitos com ESP32, consultando datasheets e fazendo os cálculos de bancada.

| pasta | laboratório | o que tem |
|---|---|---|
| `lab01-rag/` | 01 - RAG | RAG sobre os datasheets do ESP32, DHT22, HC-SR04 e as capacidades da JLCPCB, com benchmark de 14 perguntas |
| `lab02-mcp/` | 02 - MCP | servidor MCP `bancada` (`server.py`), skill `ligar-componente-no-esp32` e agente com o servidor de arquivos da comunidade |
| `lab03-seguranca/` | 03 - Segurança | ataques ao assistente da Loja Aurora e a defesa em camadas |
| `lab04-workflow-agente/` | 04 - Workflow ou Agente | atendimento técnico de bancada feito como workflow do LangGraph e como agente, comparados em 12 casos |

Cada notebook está executado e tem a análise dos resultados no fim.

## Como rodar

Requisitos: Python 3.12 e Node.js (o laboratório de MCP roda o servidor da comunidade com `npx`).

```bash
python3.12 -m venv .venv
.venv/bin/pip install langchain "langchain[mcp]" fastmcp langchain-community langchain-chroma langgraph \
    langchain-google-genai pdfplumber beautifulsoup4 fastembed pandas pyyaml python-dotenv rank-bm25 jupyter
```

Crie um `.env` nesta pasta (ele fica fora do git):

```
MODELO=google_genai:gemini-3.5-flash-lite
GOOGLE_API_KEY=<sua chave>
```

Os notebooks rodam pelo Jupyter ou pelo `rodar.sh`, que executa um notebook no lugar e grava o log em `logs/`:

```bash
./rodar.sh lab01-rag "01 - RAG.ipynb"
```

Rode o laboratório 01 primeiro: ele cria o índice em `lab01-rag/indice/`, que os laboratórios 02 e 04 copiam. O modelo de embedding (`intfloat/multilingual-e5-small`, cerca de 470 MB) é baixado para `modelos/` na primeira execução.

### Documentos do RAG

Os PDFs não estão no repositório, só no zip da entrega. Para rodar do zero, baixe para `lab01-rag/documentos/`:

| arquivo | origem |
|---|---|
| `esp32-datasheet.pdf` | [ESP32 Series Datasheet](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf) (Espressif) |
| `dht22.pdf` | [AM2302 (DHT22)](https://cdn-shop.adafruit.com/datasheets/Digital+humidity+and+temperature+sensor+AM2302.pdf) (cópia da Adafruit) |
| `hc-sr04.pdf` | [HC-SR04](https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf) (Elecfreaks, cópia da SparkFun) |
| `jlcpcb.html` | [JLCPCB Rigid PCB Manufacturing Capabilities](https://jlcpcb.com/capabilities/pcb-capabilities), página salva |

## Modelo usado

Todos os notebooks foram executados com o `gemini-3.5-flash-lite` (o mesmo do nosso projeto), no nível gratuito da API do Gemini. O custo do laboratório 04 é calculado com o preço do nível pago desse modelo (US$ 0,30 por milhão de tokens de entrada e US$ 2,50 por milhão de saída, [tabela de preços](https://ai.google.dev/gemini-api/docs/pricing), consultada em 23/11/2026), ou seja, é o que as chamadas custariam se não fossem gratuitas. No laboratório 03, o modelo do enunciado (`openai:gpt-4o-mini`) foi trocado pelo Gemini porque a dupla não tem chave da OpenAI.

## Resultados

### 01 - RAG

Benchmark de 14 perguntas: 10 fáceis, 2 com a resposta espalhada em mais de um documento e 2 sem resposta nos documentos.

| configuração | retrieval | respostas |
|---|---|---|
| `chunk_size=1000`, busca densa, pergunta em português | 0,54 | 0,57 |
| `chunk_size=500` | 0,54 | 0,50 |
| consulta reescrita em inglês e busca híbrida (densa + BM25) | **0,77** | **0,71** |

O sistema nunca inventou valores: todos os erros são respostas "não encontrei" de quando a busca não trouxe a tabela certa. Mudar o `k` (3, 5 ou 8) não alterou nada; o que melhorou foi buscar com os termos do datasheet em inglês, como já fazemos no projeto.

### 02 - MCP

Servidor `bancada` com 4 ferramentas (o retriever do laboratório 01 e três cálculos do servidor do nosso projeto), 2 recursos (um fixo e um template) e 1 prompt, usado junto com o servidor de arquivos da comunidade (`@modelcontextprotocol/server-filesystem`). Nas 7 perguntas, o agente usou o servidor certo em todas, carregou a skill só na pergunta que pedia o passo a passo e recusou a pergunta que nenhum servidor responde. Os problemas encontrados foram de conteúdo: uma recomendação sem fonte e uma página trocada.

### 03 - Segurança

Antes da defesa, 2 dos 9 ataques vazaram a chave inteira (a dúvida do Pix com o pedido dos "12 caracteres" e o conto de ficção). Com a defesa em quatro camadas (regex, classificador, regras na mensagem de sistema e guardrail de saída), nenhum ataque vazou, e as 6 perguntas de cliente continuaram sendo respondidas. O ataque novo, escrito para escapar da regex, foi barrado pelo classificador.

### 04 - Workflow ou Agente

| versão | acerto | chamadas por caso | latência mediana | custo dos 12 casos |
|---|---|---|---|---|
| workflow (roteamento, encadeamento e avaliador com otimizador) | 8/12 | 3,75 | 10,2 s | US$ 0,0095 |
| agente (`create_agent`) | 11/12 | 2,58 | 4,8 s | US$ 0,0239 |

O agente acertou mais e respondeu mais rápido, mas gastou 3,7 vezes mais tokens de entrada, e no único erro inventou um valor (12 mA, tirado do histórico de revisões do datasheet). O workflow errou por roteamento e por não ter rota para pedidos mistos, mas nunca inventou um valor.
