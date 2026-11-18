# config.py - Configuracoes do no IoT EcoSmart (Grupo 2)

# --- Identificacao e localizacao da lixeira (fixa) ---
LIXEIRA_ID = "INSIRA_O_ID_DA_LIXEIRA"
LAT = 0.0  # substitua pela latitude da lixeira
LON = 0.0  # substitua pela longitude da lixeira

# --- Fonte de alimentacao ---
# False -> prototipo atual: ESP32 alimentado pelo USB (TP4056 / 18650 / painel
#          solar / MT3608 ainda nao chegaram). Leitura de bateria, corte por
#          tensao e economia de energia ficam DESATIVADOS. PIN_BAT fica livre.
# True  -> versao final com bateria 18650: ativa a leitura no PIN_BAT, o corte
#          de protecao da celula e o sono dobrado com bateria baixa.
BATERIA_PRESENTE = False

# --- Chaveamento do sensor ---
# False -> sem MOSFET: HC-SR04 ligado direto no 5 V e no GND, sempre alimentado.
#          PIN_SENSOR_PWR fica livre e nao e usado.
# True  -> com MOSFET (2N7000) no GND do sensor, controlado pelo PIN_SENSOR_PWR;
#          o sensor so recebe energia durante a medicao (economia na bateria).
MOSFET_PRESENTE = False

# --- Pinos GPIO ---
PIN_TRIG = 12        # J7  -> TRIG do HC-SR04
                     #        (GPIO12 e pino de boot; se a placa nao subir com o
                     #        sensor ligado, troque para 13)
PIN_ECHO = 14        # J8  -> ECHO via divisor 1k / 2k (5 V -> 3,3 V)
PIN_SENSOR_PWR = 27  # J9  -> Gate do MOSFET (so usado se MOSFET_PRESENTE=True)
PIN_BAT = 34         # J15 -> divisor da bateria (so usado se BATERIA_PRESENTE=True)

# --- Modo de teste ---
# True  -> nao entra em Deep Sleep (loop com time.sleep); bom no USB/serial
# False -> comportamento real de campo (dorme entre as leituras)
MODO_DEBUG = True

# --- Sensor e dimensoes da lixeira ---
TEMP_C = 30.0           # temperatura ambiente estimada (corrige a velocidade do som)
AMOSTRAS = 5            # numero de leituras por ciclo (pegamos a mediana)
SENSOR_AQUECIMENTO_MS = 100  # tempo apos ligar o MOSFET antes da 1a leitura
ECHO_TIMEOUT_US = 30000      # espera maxima pelo eco (30 ms ~ 5 m)
DIST_VAZIA_CM = 80.0   # distancia do sensor ate o fundo  <- AJUSTE para a altura real
DIST_CHEIA_CM = 20.0    # distancia do sensor ao topo (lixeira cheia)
LIMIAR_ATENCAO = 60.0   # a partir desta %, status = ATENCAO
LIMIAR_CRITICO = 80.0   # a partir desta %, status = CRITICO (dispara alerta)
QUEDA_COLETA = 30.0     # queda minima de % entre ciclos = houve coleta

# --- Bateria 18650 (ignorado enquanto BATERIA_PRESENTE = False) ---
BAT_DIVISOR = 2.0       # fator do divisor de tensao (100k / 100k = 2)
BAT_V_MAX = 4.20        # tensao de bateria cheia -> 100%
BAT_V_MIN = 3.30        # tensao de bateria vazia -> 0%
BAT_CORTE_V = 3.20      # abaixo disso, protege a celula e dorme por muito tempo
BAT_BAIXA_V = 3.50      # bateria baixa: dobra o tempo de sono para economizar

# --- Rede Wi-Fi e API ---
WIFI_SSID = "INSIRA_O_NOME_DA_REDE_WIFI"
WIFI_PASS = "INSIRA_A_SENHA_DA_REDE_WIFI"
WIFI_TIMEOUT_MS = 10000
API_URL = "http://IP_DO_SERVIDOR:8000/api/v1/telemetria"
# API_URL = "http://exemplo.com/api/v1/telemetria" # endpoint de envio (real)
API_KEY = "INSIRA_A_CHAVE_DE_API_DESTE_DISPOSITIVO"

# --- Intervalos de Deep Sleep (em segundos) ---
SONO_NORMAL = 300       # 5 min
SONO_ATENCAO = 120      # 2 min
SONO_CRITICO = 60       # 1 min
SONO_ERRO = 180         # 3 min
SONO_BAT_CORTE = 3600   # 1 h (bateria em reserva critica)
