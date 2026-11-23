# Painel de status da estufa

Placa: ESP32 DevKitC, alimentada pela USB.

- LED vermelho (queda de 2,0 V) no GPIO25, para alarme. Corrente desejada: 10 mA.
- LED verde (queda de 2,2 V) no GPIO26, para tudo certo. Corrente desejada: 8 mA.
- LED azul (queda de 3,0 V) no GPIO27, para irrigação ligada. Corrente desejada: 5 mA.

Os três LEDs são ligados entre o GPIO e o GND, cada um com o seu resistor em série.
