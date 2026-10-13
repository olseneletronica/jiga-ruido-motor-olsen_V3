"""
gerar_dados_exemplo.py — gera um TSV sintético no MESMO formato da planilha
V3 (firmware V0.06: tabulação, vírgula decimal, uma linha por condição com
200 amostras de cada canal nas colunas "<canal>_001" ... "<canal>_200").

Roteiro simulado por ensaio: 15 kHz H -> 15 kHz AH -> 20 kHz H -> 20 kHz AH,
200 amostras a cada 15 ms (3 s) em cada condição.

Motores simulados:
    1–6  saudáveis (Aprovado)
    7    saudável em horário, mas vibração/ruído maiores em anti-horário a 20 kHz
    8    com falha: corrente e vibração acima do normal nas 4 condições

Uso:
    python scripts/gerar_dados_exemplo.py
"""
from datetime import datetime, timedelta

import numpy as np

from config import EXEMPLO_DIR, EXEMPLO_MOTORES_TSV, EXEMPLO_TSV, ID_COLUMNS, SIGNAL_COLUMNS

BLOCOS = [("HORARIO", 15000), ("ANTIHORARIO", 15000), ("HORARIO", 20000), ("ANTIHORARIO", 20000)]
N_AMOSTRAS = 200
DT = 0.015
FIRMWARE = "V0.06_200SAMPLES_CADA"


def br(x: float, casas: int) -> str:
    return f"{x:.{casas}f}".replace(".", ",")


def cabecalho() -> list[str]:
    return ID_COLUMNS + [f"{c}_{i:03d}" for c in SIGNAL_COLUMNS for i in range(1, N_AMOSTRAS + 1)]


def gerar():
    rng = np.random.default_rng(42)
    t = np.arange(N_AMOSTRAS) * DT
    linhas = []
    dia = datetime(2026, 10, 13)
    for ensaio in range(1, 9):
        ganho = rng.normal(1.0, 0.03) if ensaio != 7 else 1.0
        for sentido, freq in BLOCOS:
            corr = (1.30 if freq == 15000 else 1.27) * ganho
            vib = 0.06 if freq == 15000 else 0.065
            audio = -22.8 if sentido == "HORARIO" else -24.5
            if ensaio == 7 and sentido == "ANTIHORARIO" and freq == 20000:
                vib *= 2.2
                audio += 5.0
            if ensaio == 8:
                corr *= 1.25
                vib *= 2.6
                audio += 4.0
            sinal = 1 if sentido == "HORARIO" else -1
            v = 32.39 + rng.normal(0, 0.03, N_AMOSTRAS)
            i = corr + 0.08 * np.sin(2 * np.pi * 1.3 * t) + rng.normal(0, 0.08, N_AMOSTRAS)
            p = v * i + rng.normal(0, 1.5, N_AMOSTRAS)
            # Vibração: componente que alterna a cada amostra (alias de rotação
            # rápida) + ruído; Z carrega a gravidade (~1 g).
            alt = np.where(np.arange(N_AMOSTRAS) % 2 == 0, 1, -1)
            ax = -0.04 + 0.4 * vib * rng.normal(0, 1, N_AMOSTRAS)
            ay = 0.03 + 0.3 * vib * rng.normal(0, 1, N_AMOSTRAS)
            az = 1.0 + vib * alt + 0.3 * vib * rng.normal(0, 1, N_AMOSTRAS)
            res = np.sqrt(ax ** 2 + ay ** 2 + az ** 2)
            gx = -2.55 + rng.normal(0, 8 * vib, N_AMOSTRAS)
            gy = sinal * 0.35 + rng.normal(0, 3 * vib, N_AMOSTRAS)
            gz = -0.35 + rng.normal(0, 3 * vib, N_AMOSTRAS)
            a1 = audio + 1.2 * np.sin(2 * np.pi * 0.7 * t) + rng.normal(0, 0.5, N_AMOSTRAS)
            a2 = a1 + rng.normal(0, 0.4, N_AMOSTRAS)
            canais = {
                "tensao_v": (v, 3), "corrente_a": (i, 4), "potencia_w": (p, 3),
                "accel_x_g": (ax, 5), "accel_y_g": (ay, 5), "accel_z_g": (az, 5),
                "accel_resultante_g": (res, 5),
                "gyro_x_dps": (gx, 4), "gyro_y_dps": (gy, 4), "gyro_z_dps": (gz, 4),
                "audio1_dbfs": (a1, 2), "audio1_peak_dbfs": (a1 + 8 + rng.normal(0, 0.8, N_AMOSTRAS), 2),
                "audio2_dbfs": (a2, 2), "audio2_peak_dbfs": (a2 + 9 + rng.normal(0, 0.8, N_AMOSTRAS), 2),
            }
            linha = [dia.strftime("%d/%m/%Y"), FIRMWARE, str(ensaio), sentido, str(freq), "3"]
            for c in SIGNAL_COLUMNS:
                serie, casas = canais[c]
                linha += [br(x, casas) for x in serie]
            linhas.append(linha)
        if ensaio % 4 == 0:
            dia += timedelta(days=1)
    return linhas


def main():
    EXEMPLO_DIR.mkdir(parents=True, exist_ok=True)
    linhas = gerar()
    with open(EXEMPLO_TSV, "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(cabecalho()) + "\n")
        for l in linhas:
            f.write("\t".join(l) + "\n")
    with open(EXEMPLO_MOTORES_TSV, "w", encoding="utf-8", newline="\n") as f:
        f.write("ensaio\tmotor\tobservacao\tclassificacao\tatualizado_em\n")
        cadastro = [(e, "Aprovado", "Lote 2026-10" if e == 1 else "") for e in range(1, 7)]
        cadastro += [(7, "Em análise", "Ruído só no anti-horário"), (8, "Reprovado", "Ruído e vibração altos")]
        for e, cls, obs in cadastro:
            f.write(f"{e}\tBOSCH-{1000 + e}\t{obs}\t{cls}\t13/10/2026 10:00:00\n")
    print(f"[exemplo] {len(linhas)} linhas ({N_AMOSTRAS} amostras cada) -> {EXEMPLO_TSV}")


if __name__ == "__main__":
    main()
