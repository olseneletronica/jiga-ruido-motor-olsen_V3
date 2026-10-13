"""
config.py — constantes compartilhadas por todos os scripts do pipeline V3.

Qualquer mudança no cabeçalho da planilha, nas frequências do roteiro ou nos
limites de assimetria deve ser feita AQUI (e espelhada em dashboard/app.js,
seção CONFIG, para o dashboard continuar coerente com o pipeline).
"""
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
EXEMPLO_DIR = DATA_DIR / "exemplo"

RAW_PATH = DATA_DIR / "raw_ensaios.csv"
POINT_PATH = DATA_DIR / "features_por_condicao.csv"
ENSAIO_PATH = DATA_DIR / "features_por_ensaio.csv"
SENTIDO_PATH = DATA_DIR / "assimetria_sentido.csv"
BASELINE_PATH = DATA_DIR / "baseline.json"
CLASSIF_PATH = DATA_DIR / "classificacao.csv"
EXEMPLO_TSV = EXEMPLO_DIR / "raw_exemplo.tsv"
EXEMPLO_MOTORES_TSV = EXEMPLO_DIR / "motores_exemplo.tsv"
MOTORES_PATH = DATA_DIR / "motores.csv"

# Leitura AO VIVO: planilha "Publicar na Web" (primeira aba = DADOS), CSV.
# Números com vírgula decimal (locale BR), campos entre aspas.
LIVE_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vT2wsrlEcMIWu9sEjRpumG7rGKjUGYPdmNSlArK2f8QZb9VDq3FYmK4DIwLRZM-sFhDSZ3P9OJfvgK0/"
    "pub?output=csv"
)

# Apps Script de cadastro (apps-script/cadastro_motores.gs) implantado como
# app da Web. Com ?acao=listar devolve a aba MOTORES em JSON. Vazio = ainda
# não implantado (os motores ficam sem nome/classificação).
MOTORES_API_URL = ""

# Reserva para a aba MOTORES: link "Publicar na Web" SÓ dessa aba, em CSV
# (pub?gid=<gid da aba MOTORES>&single=true&output=csv). Vazio = sem reserva.
MOTORES_URL = ""

# --- Formato da planilha V3 (firmware V0.06) ------------------------------
# Cada LINHA da planilha é um bloco de amostras de UMA condição (sentido +
# frequência): 6 colunas de identificação + N amostras de cada canal, nas
# colunas "<canal>_001" ... "<canal>_200". Hoje: 1 linha por condição,
# 4 linhas por ensaio, 200 amostras a cada 15 ms (3 s por condição).
ID_COLUMNS = ["timestamp", "firmware", "ensaio", "sentido", "frequencia_hz", "segundo"]

# Período entre amostras (firmware V0.06: 15 ms). Usado só para o eixo de tempo.
PERIODO_AMOSTRA_S = 0.015

SIGNAL_COLUMNS = [
    "tensao_v", "corrente_a", "potencia_w",
    "accel_x_g", "accel_y_g", "accel_z_g", "accel_resultante_g",
    "gyro_x_dps", "gyro_y_dps", "gyro_z_dps",
    "audio1_dbfs", "audio1_peak_dbfs", "audio2_dbfs", "audio2_peak_dbfs",
]

# Depois de "esticar" a planilha (fetch_sheet.py), cada linha de
# data/raw_ensaios.csv é UMA amostra, com estas colunas:
#   bloco = valor da coluna "segundo" da planilha (identifica o bloco)
#   amostra = índice 1..N dentro da condição; t_s = tempo desde o início da condição
LONG_COLUMNS = (["timestamp", "timestamp_iso", "firmware", "ensaio", "sentido",
                 "frequencia_hz", "bloco", "amostra", "t_s"] + SIGNAL_COLUMNS)

TEXT_COLUMNS = ["timestamp", "firmware", "sentido"]

# Canais do IMU. Amostra com TODOS zerados, ou com o eixo Z abaixo de
# IMU_Z_MIN_G (sem a gravidade de ~1 g que ele sempre carrega), é falha de
# leitura do sensor: os 7 canais do IMU daquela amostra viram ausentes.
IMU_COLUMNS = [
    "accel_x_g", "accel_y_g", "accel_z_g", "accel_resultante_g",
    "gyro_x_dps", "gyro_y_dps", "gyro_z_dps",
]
IMU_Z_MIN_G = 0.2

# Roteiro: só 15 kHz e 20 kHz, cada uma nos dois sentidos.
FREQUENCIAS_HZ = [15000, 20000]
SENTIDOS = ["H", "AH"]  # H = horário, AH = anti-horário
SENTIDO_LABEL = {"H": "Horário", "AH": "Anti-horário"}

# Condição de ensaio = sentido + frequência (ex: "H_15000").
GROUP_KEYS = ["ensaio", "sentido", "frequencia_hz"]


def normaliza_sentido(valor) -> str:
    """Aceita as grafias mais prováveis vindas do firmware/planilha e devolve
    'H' ou 'AH'. Valores desconhecidos voltam em maiúsculas, sem alteração,
    para aparecerem no dashboard e serem corrigidos na origem."""
    if valor is None:
        return ""
    s = str(valor).strip().upper()
    s = (s.replace("Á", "A").replace("-", "").replace("_", "").replace(" ", ""))
    if s in {"H", "HORARIO", "CW", "HOR"}:
        return "H"
    if s in {"AH", "ANTIHORARIO", "CCW", "AHOR", "ANTI"}:
        return "AH"
    return s


# --- Comparação horário × anti-horário ----------------------------------
#
# Para cada canal, qual estatística comparar entre os sentidos e como medir a
# diferença:
#   "rel" -> diferença relativa em %:  (AH - H) / média(|H|, |AH|) * 100
#   "db"  -> diferença absoluta em dB: AH - H (áudio já é logarítmico)
#
# Vibração e giroscópio usam o DESVIO-PADRÃO dentro do bloco (componente
# dinâmica), porque a média do acelerômetro carrega a gravidade e mascara a
# vibração real do motor.
ASSIMETRIA_CANAIS = [
    ("corrente_a", "mean", "rel"),
    ("potencia_w", "mean", "rel"),
    ("tensao_v", "mean", "rel"),
    ("accel_x_g", "std", "rel"),
    ("accel_y_g", "std", "rel"),
    ("accel_z_g", "std", "rel"),
    ("accel_resultante_g", "std", "rel"),
    ("gyro_x_dps", "std", "rel"),
    ("gyro_y_dps", "std", "rel"),
    ("gyro_z_dps", "std", "rel"),
    ("audio1_dbfs", "mean", "db"),
    ("audio1_peak_dbfs", "mean", "db"),
    ("audio2_dbfs", "mean", "db"),
    ("audio2_peak_dbfs", "mean", "db"),
]

# Limites iniciais (herdados do V2) — recalibrar com motores bons do V3.
# O desvio-padrão agora vem de 200 amostras a 15 ms (antes: ~20 leituras a
# 1/s), então capta vibração mais rápida e tende a ser maior que no V2.
LIMITE_ASSIMETRIA_REL_PCT = {"mean": 10.0, "std": 40.0}
LIMITE_ASSIMETRIA_DB = 3.0

# Um ensaio só é marcado com assimetria de sentido quando pelo menos este
# número de canais passa do limite NA MESMA frequência (um canal isolado
# costuma ser ruído de medição).
MIN_CANAIS_ASSIMETRIA = 3
