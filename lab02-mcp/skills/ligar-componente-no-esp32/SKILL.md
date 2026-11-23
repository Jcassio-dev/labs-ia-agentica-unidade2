---
name: ligar-componente-no-esp32
description: Planeja a ligação de um sensor, LED ou módulo num ESP32, conferindo nos datasheets se pode ligar direto e calculando o resistor ou o divisor de tensão. Use quando o usuário perguntar como ligar, conectar ou montar um componente no ESP32, ou se um componente pode ir direto num pino.
---

# Ligar um componente no ESP32

## 1. Ler o pedido

Anote o componente, o pino do ESP32 (se o usuário disse) e a alimentação disponível. Se o pedido citar um arquivo em `circuitos/`, leia o arquivo com `arquivos_read_text_file` antes de seguir.

## 2. Consultar os datasheets

Faça duas buscas com `bancada_buscar_datasheet`, em inglês e com o filtro `documento`:

1. a alimentação e o nível do sinal do componente, ex.: `bancada_buscar_datasheet("power supply working voltage", documento="hc-sr04")`;
2. o limite de entrada e a corrente dos GPIOs do ESP32: `bancada_buscar_datasheet("DC characteristics input voltage source current", documento="esp32-datasheet")`.

Se uma busca não trouxer o valor, reformule com outros termos do datasheet (ex.: "electric parameter", "absolute maximum ratings") e busque mais uma vez. Se ainda assim não achar, diga que o valor não está nos documentos e não invente.

O componente fora dos documentos (ex.: um LED comum): use os valores que o usuário deu ou os típicos que a ferramenta `bancada_resistor_led` explica, dizendo que são típicos.

## 3. Decidir e calcular

- Componente que aceita 3,3 V: alimente no 3V3.
- Componente que só trabalha em 5 V e devolve sinal de 5 V: alimente no 5V e calcule um divisor para o sinal com `bancada_divisor_tensao(tensao_entrada=5, tensao_saida=3.3)`.
- LED: calcule o resistor com `bancada_resistor_led(tensao_fonte=3.3, tensao_led=..., corrente_ma=...)`. A corrente pedida não pode passar da corrente do GPIO que veio do datasheet.
- Pino do usuário que é só de entrada (GPIO34 a GPIO39) e o componente precisa de saída: avise e sugira outro pino.

Se uma ferramenta devolver erro, corrija o argumento indicado na mensagem e chame de novo uma vez.

## 4. Responder

Responda neste formato:

```
Ligação do <componente> no ESP32

| Pino do componente | Liga em | Observação |
|---|---|---|
| ... | ... | ... |

Componentes extras: <resistores com valor, ou "nenhum">
Fontes: <documento, p. N> para cada valor usado
```

Termine com uma frase dizendo se pode ligar direto ou o que é obrigatório para não danificar o ESP32.
