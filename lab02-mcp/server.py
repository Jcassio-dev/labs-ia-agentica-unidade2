from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

PASTA = Path(__file__).resolve().parent
E5 = "intfloat/multilingual-e5-small"
DOCUMENTOS = {
    "esp32-datasheet": "ESP32 Series Datasheet",
    "dht22": "AM2302 (DHT22) Datasheet",
    "hc-sr04": "HC-SR04 Ultrasonic Ranging Module",
    "jlcpcb": "JLCPCB Rigid PCB Manufacturing Capabilities",
}
SERIE_E12 = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]

mcp = FastMCP(
    "bancada",
    instructions="Datasheets do ESP32, DHT22, HC-SR04 e capacidades da JLCPCB, e cálculos de resistor de LED, "
                 "divisor de tensão e largura de trilha.",
)

_colecao = None


def colecao():
    """Índice do laboratório de RAG (Chroma em indice/, embeddings multilingual-e5-small)."""
    global _colecao
    if _colecao is None:
        import chromadb
        from fastembed import TextEmbedding
        from fastembed.common.model_description import ModelSource, PoolingType

        if E5 not in {m["model"] for m in TextEmbedding.list_supported_models()}:
            TextEmbedding.add_custom_model(model=E5, pooling=PoolingType.MEAN, normalization=True,
                                           sources=ModelSource(hf=E5), dim=384, model_file="onnx/model.onnx")
        modelo = TextEmbedding(E5, cache_dir=str(PASTA / "modelos"))
        cliente = chromadb.PersistentClient(path=str(PASTA / "indice"))
        _colecao = (cliente.get_collection("trechos-1000"), modelo)
    return _colecao


def _e12_acima(valor):
    decada = 1.0
    while decada * 10 <= valor:
        decada *= 10
    while True:
        for base in SERIE_E12:
            candidato = round(base * decada, 6)
            if candidato >= valor - 1e-9:
                return candidato
        decada *= 10


@mcp.tool
def buscar_datasheet(consulta: str, documento: str | None = None, k: int = 5) -> list[dict]:
    """Busca trechos nos datasheets indexados e devolve o texto com documento e página para citar.

    Use para qualquer valor técnico (tensão, corrente, pino, tempo, limite de fabricação) do ESP32, do sensor
    DHT22, do sensor ultrassônico HC-SR04 ou da fabricante de placas JLCPCB. Os documentos estão em inglês:
    a consulta funciona melhor em inglês, com os termos do datasheet (ex.: "DC characteristics source current",
    "absolute maximum ratings", "power supply voltage").

    documento: restringe a busca a um documento: "esp32-datasheet", "dht22", "hc-sr04" ou "jlcpcb".
    k: quantos trechos devolver (1 a 10).
    Se os trechos não responderem, reformule a consulta ou troque o filtro e busque de novo.
    """
    if documento is not None and documento not in DOCUMENTOS:
        raise ToolError(f"documento desconhecido: {documento!r}. Use um destes: {', '.join(DOCUMENTOS)}.")
    if not 1 <= k <= 10:
        raise ToolError("k precisa estar entre 1 e 10.")
    col, modelo = colecao()
    vetor = next(iter(modelo.embed([f"query: {consulta}"]))).tolist()
    r = col.query(query_embeddings=[vetor], n_results=k, where={"documento": documento} if documento else None)
    return [
        {"documento": m["documento"], "titulo": m["titulo"], "pagina": m.get("pagina"), "secao": m.get("secao"),
         "distancia": round(d, 3), "texto": t}
        for t, m, d in zip(r["documents"][0], r["metadatas"][0], r["distances"][0])
    ]


@mcp.tool
def resistor_led(tensao_fonte: float, tensao_led: float = 2.0, corrente_ma: float = 10.0) -> dict:
    """Calcula o resistor em série de um LED, R = (tensão da fonte - queda do LED) / corrente.

    tensao_fonte: tensão que alimenta o LED, em volts (num GPIO do ESP32, 3.3).
    tensao_led: queda direta do LED em volts (vermelho cerca de 2.0, verde 2.2, azul e branco 3.0).
    corrente_ma: corrente desejada no LED, em mA.
    Devolve o valor ideal, o valor comercial da série E12 logo acima, a corrente real com ele e a potência no resistor.
    """
    if corrente_ma <= 0:
        raise ToolError("corrente_ma precisa ser maior que zero.")
    if tensao_fonte <= tensao_led:
        raise ToolError("tensao_fonte precisa ser maior que tensao_led.")
    ideal = (tensao_fonte - tensao_led) / (corrente_ma / 1000)
    comercial = _e12_acima(ideal)
    corrente = (tensao_fonte - tensao_led) / comercial * 1000
    return {"resistor_ideal_ohms": round(ideal, 1), "resistor_comercial_ohms": comercial,
            "corrente_real_ma": round(corrente, 2), "potencia_mw": round((tensao_fonte - tensao_led) * corrente, 1)}


@mcp.tool
def divisor_tensao(tensao_entrada: float, tensao_saida: float, r2_ohms: float = 10000) -> dict:
    """Dimensiona um divisor resistivo para baixar um sinal, Vsaída = Ventrada * R2 / (R1 + R2).

    Use quando um sinal de 5 V precisa entrar num GPIO de 3,3 V (ex.: o pino Echo do HC-SR04).
    tensao_entrada e tensao_saida em volts; r2_ohms é o resistor ligado ao GND.
    Calcula R1 e arredonda para o valor comercial E12 de cima, então a saída real nunca passa da pedida.
    """
    if not 0 < tensao_saida < tensao_entrada:
        raise ToolError("tensao_saida precisa estar entre 0 e tensao_entrada.")
    if r2_ohms <= 0:
        raise ToolError("r2_ohms precisa ser maior que zero.")
    r1 = _e12_acima(r2_ohms * (tensao_entrada - tensao_saida) / tensao_saida)
    return {"r1_ohms": r1, "r2_ohms": r2_ohms, "tensao_saida_real": round(tensao_entrada * r2_ohms / (r1 + r2_ohms), 3)}


@mcp.tool
def largura_trilha(corrente_a: float, espessura_cobre_oz: float = 1.0, elevacao_temperatura_c: float = 10.0,
                   camada: str = "externa") -> dict:
    """Largura mínima de uma trilha de placa de circuito impresso pela norma IPC-2221.

    corrente_a: corrente na trilha, em ampères. espessura_cobre_oz: cobre em oz/ft² (1 oz = 35 µm).
    elevacao_temperatura_c: aquecimento aceito, em °C. camada: "externa" ou "interna".
    O resultado é o mínimo pela norma; compare com a largura mínima que o fabricante consegue fazer.
    """
    if min(corrente_a, espessura_cobre_oz, elevacao_temperatura_c) <= 0:
        raise ToolError("corrente, espessura e elevação de temperatura precisam ser maiores que zero.")
    if camada not in ("externa", "interna"):
        raise ToolError("camada deve ser 'externa' ou 'interna'.")
    k = 0.048 if camada == "externa" else 0.024
    area = (corrente_a / (k * elevacao_temperatura_c**0.44)) ** (1 / 0.725)
    largura_mils = area / (espessura_cobre_oz * 1.378)
    return {"largura_mm": round(largura_mils * 0.0254, 3), "largura_mils": round(largura_mils, 1)}


@mcp.resource("esp32://restricoes-gpio", mime_type="text/markdown")
def restricoes_gpio() -> str:
    """Restrições dos GPIOs do ESP32 que valem conferir antes de ligar qualquer componente."""
    return """# Restrições dos GPIOs do ESP32 (ESP32 Series Datasheet v5.3)

- 34 GPIOs programáveis; 6 são só de entrada (GPIO34 a GPIO39) e 5 são strapping pins (p. 4).
- Strapping pins e nível padrão no boot: GPIO0 pull-up, GPIO2 pull-down, MTDI (GPIO12) pull-down,
  MTDO (GPIO15) pull-up, GPIO5 pull-up. Carga externa que mude esses níveis muda o boot (p. 22).
- Alimentação: máximo absoluto de 3,6 V (p. 51).
- Entrada em nível alto vai até VDD + 0,3 V; um sinal de 5 V direto num GPIO passa do limite (p. 52).
- Cada GPIO fornece cerca de 40 mA (VDD3P3_CPU e VDD3P3_RTC), caindo para cerca de 29 mA por pino
  quando muitos pinos fornecem corrente ao mesmo tempo (p. 52).
"""


@mcp.resource("datasheet://{documento}/{pagina}", mime_type="text/plain")
def pagina_datasheet(documento: str, pagina: int) -> str:
    """Texto completo de uma página de um datasheet indexado (documento: esp32-datasheet, dht22 ou hc-sr04)."""
    if documento not in DOCUMENTOS:
        raise ToolError(f"documento desconhecido: {documento!r}")
    col, _ = colecao()
    r = col.get(where={"$and": [{"documento": documento}, {"pagina": int(pagina)}]}, include=["documents", "metadatas"])
    if not r["documents"]:
        raise ToolError(f"página {pagina} não encontrada em {documento}")
    trechos = sorted(zip(r["metadatas"], r["documents"]), key=lambda x: x[0]["start_index"])
    texto, fim = "", 0
    for m, t in trechos:
        inicio = m["start_index"]
        texto += t[max(0, fim - inicio):]
        fim = max(fim, inicio + len(t))
    return texto


@mcp.prompt
def ligar_componente(componente: str, pino: str) -> str:
    """Pede ao agente para conferir como ligar um componente num GPIO do ESP32."""
    return (f"Quero ligar o componente {componente} no pino {pino} do ESP32. Consulte o datasheet do componente e do "
            f"ESP32, diga se posso ligar direto e, se precisar, calcule o resistor ou o divisor de tensão. "
            f"Cite as páginas.")


if __name__ == "__main__":
    mcp.run(show_banner=False)
