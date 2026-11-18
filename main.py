# main.py - Lixeira inteligente EcoSmart (ESP32 + HC-SR04) - MicroPython
# Alimentacao: USB (BATERIA_PRESENTE=False) ou 18650 (BATERIA_PRESENTE=True)
# Sensor:      direto no 5 V (MOSFET_PRESENTE=False) ou chaveado (MOSFET_PRESENTE=True)

import time

import network
import ujson
from machine import ADC, RTC, Pin, deepsleep, time_pulse_us

import config as C

try:
    import requests
except ImportError:
    import urequests as requests

rtc = RTC()


# Estado entre ciclos (RTC memory: sobrevive ao Deep Sleep, ~2 KB)
# Contagem de boots, o ultimo status e o ultimo nivel
# ==============================================
def estado_carregar():
    try:
        return ujson.loads(rtc.memory())
    except Exception:
        return {"boot": 0, "status": "NORMAL", "nivel": None}


def estado_salvar(est):
    try:
        rtc.memory(ujson.dumps(est))
    except Exception as e:
        print("Erro ao salvar estado:", e)


# Alimentacao do sensor
# Sem MOSFET: o sensor esta sempre ligado e estas funcoes nao fazem nada.
# Com MOSFET: liga o GND do HC-SR04 so durante a medicao.
# ==============================================
def sensor_ligar():
    if not C.MOSFET_PRESENTE:
        return None
    pwr = Pin(C.PIN_SENSOR_PWR, Pin.OUT, value=1)
    time.sleep_ms(C.SENSOR_AQUECIMENTO_MS)   # HC-SR04 estabiliza apos energizar
    return pwr


def sensor_desligar(pwr):
    if pwr is not None:
        pwr.value(0)


# Sensor ultrassonico HC-SR04
# ==============================================
def medir_distancia_cm():
    """Retorna a mediana de N leituras (cm) ou None se o sensor falhar."""
    trig = Pin(C.PIN_TRIG, Pin.OUT, value=0)
    echo = Pin(C.PIN_ECHO, Pin.IN)

    # Velocidade do som (cm/us) corrigida pela temperatura ambiente
    v_cm_us = (331.3 + 0.606 * C.TEMP_C) / 10000.0

    medidas = []
    for _ in range(C.AMOSTRAS):
        trig.value(0)
        time.sleep_us(5)
        trig.value(1)
        time.sleep_us(10)
        trig.value(0)
        dur = time_pulse_us(echo, 1, C.ECHO_TIMEOUT_US)
        if dur > 0:
            medidas.append(dur * v_cm_us / 2.0)
        time.sleep_ms(60)

    if len(medidas) < 3:
        return None
    medidas.sort()
    return medidas[len(medidas) // 2]         # mediana


def distancia_para_percentual(d):
    """Converte a distancia (cm) em % de preenchimento (0 a 100)."""
    faixa = C.DIST_VAZIA_CM - C.DIST_CHEIA_CM
    pct = (C.DIST_VAZIA_CM - d) / faixa * 100.0
    return max(0.0, min(100.0, pct))


def classificar(pct):
    """Classifica o nivel em NORMAL / ATENCAO / CRITICO."""
    if pct >= C.LIMIAR_CRITICO:
        return "CRITICO"
    if pct >= C.LIMIAR_ATENCAO:
        return "ATENCAO"
    return "NORMAL"


# Bateria 18650 (so e lida quando BATERIA_PRESENTE = True)
# ==============================================
def ler_bateria_v():
    adc = ADC(Pin(C.PIN_BAT))
    adc.atten(ADC.ATTN_11DB)
    n = 16
    soma = 0
    for _ in range(n):
        soma += adc.read_u16() / 65535.0 * 3.3
        time.sleep_ms(2)
    tensao_adc = soma / n                     # tensao lida no pino
    return tensao_adc * C.BAT_DIVISOR         # tensao real da bateria


def bateria_pct(v):
    """Mapa linear: BAT_V_MIN = 0%, BAT_V_MAX = 100%."""
    pct = (v - C.BAT_V_MIN) / (C.BAT_V_MAX - C.BAT_V_MIN) * 100.0
    return int(max(0, min(100, pct)))


def ler_alimentacao():
    """Retorna (tensao_V, percentual) da bateria, ou (None, None) no USB."""
    if not C.BATERIA_PRESENTE:
        return None, None
    v = ler_bateria_v()
    return v, bateria_pct(v)


# Rede Wi-Fi e envio
# ==============================================
def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(C.WIFI_SSID, C.WIFI_PASS)
        t0 = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), t0) > C.WIFI_TIMEOUT_MS:
                return None
            time.sleep_ms(200)
    return wlan


def verificar_servidor():
    """Em modo debug, verifica se o ESP32 alcanca o servidor pela rede."""
    base_url = C.API_URL.rsplit("/api/v1/telemetria", 1)[0]
    try:
        r = requests.get(base_url + "/health")
        try:
            print("Teste /health HTTP", r.status_code)
            print("Resposta /health:", r.text)
            return r.status_code == 200
        finally:
            r.close()
    except Exception as e:
        print("Falha ao acessar /health:", e)
        return False


def enviar(leitura):
    """Envia a leitura via HTTP POST. Retorna True se o servidor aceitou."""
    try:
        r = requests.post(
            C.API_URL,
            data=ujson.dumps(leitura),
            headers={"Content-Type": "application/json", "X-API-Key": C.API_KEY},
        )
        try:
            print("Servidor respondeu HTTP", r.status_code)
            print("Resposta:", r.text)
            return r.status_code == 201
        finally:
            r.close()
    except Exception as e:
        print("Falha no envio:", e)
        return False


def dormir(segundos):
    """Entra em Deep Sleep (com MOSFET, garante o sensor desligado antes)."""
    if C.MOSFET_PRESENTE:
        try:
            Pin(C.PIN_SENSOR_PWR, Pin.OUT, value=0, hold=True)
        except Exception:
            Pin(C.PIN_SENSOR_PWR, Pin.OUT, value=0)
    print("Dormindo por %d s" % segundos)
    deepsleep(int(segundos * 1000))


# Script principal (executado a cada despertar)
# ==============================================
def ciclo():
    est = estado_carregar()
    est["boot"] = est["boot"] + 1
    print("\n--- Boot #%d ---" % est["boot"])

    # 1) Checagem de alimentacao
    bat_v, bat_p = ler_alimentacao()
    if bat_v is None:
        print("Alimentacao: USB (leitura de bateria desativada)")
    else:
        print("Bateria: %.2f V (%d%%)" % (bat_v, bat_p))
        if bat_v < C.BAT_CORTE_V and not C.MODO_DEBUG:
            estado_salvar(est)
            return C.SONO_BAT_CORTE

    # 2) Medicao
    pwr = sensor_ligar()
    dist = medir_distancia_cm()
    sensor_desligar(pwr)

    if dist is None:
        pct, status = None, "ERRO_SENSOR"
    else:
        pct = distancia_para_percentual(dist)
        status = classificar(pct)
    print("Distancia:", dist, "cm | Nivel:", pct, "% | Status:", status)

    # 3) Deteccao de coleta
    coleta = 0
    if pct is not None and est["nivel"] is not None:
        if (est["nivel"] - pct) >= C.QUEDA_COLETA:
            coleta = 1
            print(">> Evento de COLETA detectado!")

    # 4) Monta o pacote de telemetria
    leitura = {
        "id": C.LIXEIRA_ID,
        "lat": C.LAT,
        "lon": C.LON,
        "dist_cm": None if dist is None else round(dist, 1),
        "nivel_pct": None if pct is None else round(pct, 1),
        "status": status,
        "fonte": "BATERIA" if C.BATERIA_PRESENTE else "USB",
        "bat_v": None if bat_v is None else round(bat_v, 2),
        "bat_pct": bat_p,
        "coleta": coleta,
        "boot": est["boot"],
        "rssi": None,
        "ts": None,          # o servidor carimba o horario ao receber
    }

    # 5) Conecta e envia
    wlan = conectar_wifi()
    if wlan:
        try:
            rede = wlan.ifconfig()
            print("Wi-Fi: IP=%s Gateway=%s" % (rede[0], rede[2]))
            leitura["rssi"] = wlan.status("rssi")
        except Exception:
            pass
        if C.MODO_DEBUG and not verificar_servidor():
            print("Servidor inacessivel; POST de telemetria nao executado.")
            enviado = False
        else:
            enviado = enviar(leitura)
        print("Enviado!" if enviado else "Nao enviou (segue o ciclo).")
        wlan.active(False)
    else:
        print("Wi-Fi indisponivel neste ciclo.")

    # 6) Atualiza o estado para o proximo ciclo
    if pct is not None:
        est["nivel"] = pct
    if status != "ERRO_SENSOR":
        est["status"] = status
    estado_salvar(est)

    # 7) Define quanto tempo dormir conforme o status
    sono = {
        "NORMAL": C.SONO_NORMAL,
        "ATENCAO": C.SONO_ATENCAO,
        "CRITICO": C.SONO_CRITICO,
        "ERRO_SENSOR": C.SONO_ERRO,
    }[status]
    if bat_v is not None and bat_v < C.BAT_BAIXA_V:
        sono *= 2            # economiza energia so quando ha bateria de verdade
    return sono


def main():
    while True:
        sono = ciclo()
        if C.MODO_DEBUG:
            # Em teste: nao dorme de verdade, so aguarda e repete o loop.
            print("MODO DEBUG: sono real desativado (dormiria %d s)" % sono)
            time.sleep(5)
        else:
            dormir(sono)     # ao acordar, o ESP32 reinicia e roda main() de novo


if __name__ == "__main__":
    main()
