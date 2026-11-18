# Firmware EcoSmart para ESP32

Firmware em MicroPython para uma lixeira inteligente com ESP32 e sensor
ultrassônico HC-SR04. A placa mede o preenchimento, identifica possíveis coletas
e envia telemetria a um servidor EcoSmart pela rede Wi-Fi.

## Arquivos

- `main.py`: ciclo de medição, classificação do nível, conexão Wi-Fi e envio da telemetria.
- `config.py`: identificação, pinos, limites, intervalos e configuração da rede.

## Requisitos

- ESP32 com firmware MicroPython compatível.
- Sensor ultrassônico HC-SR04.
- Computador ou servidor EcoSmart acessível pela mesma rede da ESP32.
- ID da lixeira cadastrado no servidor e chave de API individual do dispositivo.
- Thonny ou outra ferramenta capaz de transferir arquivos para a ESP32.

O firmware tenta importar `requests` e, se não estiver disponível, usa `urequests`.
Garanta que a biblioteca usada esteja disponível na instalação MicroPython da placa.

## Segurança antes de publicar ou instalar

`config.py` contém configurações específicas da instalação. **Antes de enviar esta
pasta ao GitHub, revise o arquivo e substitua/remova qualquer SSID, senha Wi-Fi,
chave de API, endereço interno ou outro dado privado.** Não publique chaves reais
nem senhas, mesmo em repositórios privados. Se algum segredo já tiver sido
publicado, troque a senha correspondente e revogue/regenere a chave da API.

Configure pelo menos `WIFI_SSID`, `WIFI_PASS`, `LIXEIRA_ID`, `API_URL` e `API_KEY`
com valores da sua própria instalação. O endereço `API_URL` deve apontar para o
servidor, por exemplo:

```text
http://IP_DO_SERVIDOR:8000/api/v1/telemetria
```

Não use `localhost` ou `127.0.0.1`: na ESP32 eles apontariam para a própria placa,
não para o computador servidor. O firmware fornecido usa HTTP; opere-o somente em
uma rede confiável e não exponha a porta do servidor diretamente à internet.

## Ligação do protótipo configurado

Os pinos abaixo correspondem aos valores iniciais de `config.py`. Confira a
montagem física antes de energizar:

| ESP32 | HC-SR04 / circuito |
| --- | --- |
| GPIO 12 | TRIG |
| GPIO 14 | ECHO, através de divisor resistivo para reduzir 5 V a 3,3 V |
| 5 V e GND | Alimentação do HC-SR04 no modo sem MOSFET |
| GPIO 27 | Controle do MOSFET, somente quando `MOSFET_PRESENTE = True` |
| GPIO 34 | Leitura do divisor da bateria, somente quando `BATERIA_PRESENTE = True` |

O pino ECHO do HC-SR04 pode fornecer 5 V. **Não conecte ECHO diretamente ao
GPIO da ESP32**; use o divisor resistivo adequado. GPIO 12 é um pino de
configuração de boot: se a placa não iniciar com o sensor conectado, verifique a
fiação e o circuito antes de alterar os pinos.

Por padrão, `MOSFET_PRESENTE = False` (sensor sempre alimentado) e
`BATERIA_PRESENTE = False` (alimentação USB; leitura e proteção da bateria
desativadas). Ajuste esses parâmetros somente quando o circuito correspondente
estiver instalado e validado.

## Configuração

Edite `config.py` para ajustar:

- **Identificação e localização:** `LIXEIRA_ID`, `LAT` e `LON`. O ID deve
  corresponder ao dispositivo cadastrado no servidor.
- **Rede e API:** `WIFI_SSID`, `WIFI_PASS`, `API_URL` e `API_KEY`. Use uma chave
  individual válida para o dispositivo.
- **Sensor e geometria:** `PIN_TRIG`, `PIN_ECHO`, `TEMP_C`, `AMOSTRAS`,
  `DIST_VAZIA_CM` e `DIST_CHEIA_CM`. Calibre as distâncias com o sensor montado
  na posição final; a distância vazia deve ser maior que a distância cheia.
- **Estados:** `LIMIAR_ATENCAO`, `LIMIAR_CRITICO` e `QUEDA_COLETA`. Uma queda de
  nível igual ou superior a `QUEDA_COLETA` entre dois ciclos é reportada como
  coleta.
- **Energia:** `BATERIA_PRESENTE`, `BAT_DIVISOR`, limites de tensão e intervalos
  `SONO_*`. Confira se o divisor e os limites correspondem a bateria e ao
  circuito reais antes de habilitar a leitura.
- **Teste:** `MODO_DEBUG = True` evita Deep Sleep e repete o ciclo apos 5 segundos.
  Com `False`, a placa usa os intervalos configurados e entra em Deep Sleep.

Com os parâmetros fornecidos, o firmware usa 5 amostras e exige pelo menos 3
ecos válidos. Os estados são `NORMAL`, `ATENCAO`, `CRITICO` ou `ERRO_SENSOR`.
Os intervalos padrão são 300 s, 120 s, 60 s e 180 s, respectivamente. Com bateria
abaixo de `BAT_BAIXA_V`, o intervalo é duplicado; abaixo de `BAT_CORTE_V`, em modo
de campo, a placa dorme pelo período `SONO_BAT_CORTE`.

## Instalar na ESP32

1. Instale e abra o Thonny; selecione o interpretador MicroPython para ESP32 e a
   porta serial correta.
2. Revise e edite `config.py` com os valores da sua instalação.
3. Envie `main.py` e `config.py` para o diretorio raiz do sistema de arquivos da
   ESP32, mantendo exatamente esses nomes.
4. Reinicie a placa ou execute `main.py` pelo Thonny.
5. Durante os testes, acompanhe o console serial para verificar a medição, o
   estado, a conexão e a resposta HTTP.

## Comunicação com o servidor

Em cada ciclo, a ESP32 monta um JSON com o ID, coordenadas, distância, nível,
estado, fonte de alimentação, bateria (quando habilitada), indicador de coleta,
contador de inicializações e RSSI. O envio usa:

- Método `POST` para `API_URL`.
- Cabeçalho `Content-Type: application/json`.
- Cabeçalho `X-API-Key` com a chave configurada.

O firmware considera o envio aceito quando recebe HTTP `201`. Em modo debug,
antes do POST, ele consulta `/health`; se essa verificação falhar, o POST é
ignorado naquele ciclo. Falhas de Wi-Fi ou de envio não impedem o firmware de
continuar para o próximo ciclo.

O servidor deve estar em execução, acessível pela rede da placa, e ter o ID e a
chave do dispositivo configurados. Este diretório contém apenas o firmware: não
inclui nem inicia o servidor EcoSmart.

O `main.py` atual nao envia `temp_c` e nao aplica o campo `config` que o servidor
devolve na resposta. Portanto, os parametros usados pela placa sao os valores
locais de `config.py`.

## Verificação e diagnóstico

- **Sem conexão Wi-Fi:** confira SSID, senha, sinal e se a rede permite
  comunicação entre dispositivos.
- **Sem resposta do servidor:** confirme `API_URL`, IP/porta, disponibilidade do
  servidor e acesso a partir da mesma rede. Não use `localhost` na ESP32.
- **Resposta diferente de HTTP 201:** confira se o ID esta cadastrado e se a
  chave individual corresponde a ele.
- **`ERRO_SENSOR` ou distância ausente:** confira alimentação, TRIG, ECHO, divisor
  de tensão, orientação do sensor, timeout e se há ao menos 3 ecos válidos.
- **Leitura de nível incoerente:** confira a montagem e calibre `DIST_VAZIA_CM` e
  `DIST_CHEIA_CM` com a lixeira vazia e cheia.
- **Placa não inicia:** confira a fiação, especialmente GPIO 12, que também é pino
  de boot.

No console serial, `Enviado!` indica que a API respondeu HTTP 201. A verificação
`/health` confirma apenas que o servidor está acessível; não substitui o teste de
envio de telemetria.
