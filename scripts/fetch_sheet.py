"""
fetch_sheet.py — baixa a planilha e salva um snapshot limpo em
data/raw_ensaios.csv, com UMA AMOSTRA POR LINHA.

- Fonte: link "Publicar na Web" da planilha (CSV, primeira aba = DADOS).
- Formato V3 (firmware V0.06): cada linha da planilha é um bloco de uma
  condição (sentido + frequência) com N amostras por canal nas colunas
  "<canal>_001" ... "<canal>_N" (hoje N = 200, a cada 15 ms). Aqui o bloco é
  "esticado": cada amostra vira uma linha, com `amostra` (1..N dentro da
  condição) e `t_s` (tempo desde o início da condição).
- Separador decimal: a planilha está em locale BR ("32,353"). Tudo é
  convertido para ponto antes de salvar.
- `sentido` é normalizado para "H" (horário) / "AH" (anti-horário).
- Aba MOTORES: pelo Apps Script (?acao=listar) ou link publicado da aba.

Uso:
    python scripts/fetch_sheet.py              # planilha real
    python scripts/fetch_sheet.py --exemplo    # dados sintéticos de demonstração
    python scripts/fetch_sheet.py --dados DADOS.tsv --motores MOTORES.tsv
                                               # exportações da planilha (offline)
"""
import argparse
import io
import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    DATA_DIR, EXEMPLO_MOTORES_TSV, EXEMPLO_TSV, ID_COLUMNS, IMU_COLUMNS,
    LIVE_URL, LONG_COLUMNS, MOTORES_API_URL, MOTORES_PATH, MOTORES_URL,
    PERIODO_AMOSTRA_S, RAW_PATH, SIGNAL_COLUMNS, normaliza_sentido,
)


def _baixa_texto(url: str) -> str:
    # O Google serve o link publicado por vários servidores de borda (CDN);
    # o parâmetro que muda a cada chamada evita pegar uma resposta em cache.
    sep = "&" if "?" in url else "?"
    with urllib.request.urlopen(f"{url}{sep}_={int(time.time())}", timeout=60) as resp:
        return resp.read().decode("utf-8")


def _para_numero(df: pd.DataFrame) -> pd.DataFrame:
    texto = df.apply(lambda c: c.astype(str).str.strip().str.replace(",", ".", regex=False))
    return texto.apply(pd.to_numeric, errors="coerce")


def colunas_amostras(colunas, canal: str) -> list[str]:
    """Colunas "<canal>_NNN" em ordem numérica. "audio1_dbfs_007" não pode
    casar com "audio1_peak_dbfs", por isso o padrão é ancorado."""
    pad = re.compile(rf"^{re.escape(canal)}_(\d+)$")
    achadas = [(int(m.group(1)), c) for c in colunas if (m := pad.match(c))]
    return [c for _, c in sorted(achadas)]


def parse_tabela(texto: str, sep: str) -> pd.DataFrame:
    larga = pd.read_csv(io.StringIO(texto), sep=sep, dtype=str, keep_default_na=False)
    larga.columns = [c.strip() for c in larga.columns]

    faltando = [c for c in ID_COLUMNS if c not in larga.columns]
    if faltando:
        raise ValueError(f"Colunas ausentes na planilha: {faltando}")
    cols = {canal: colunas_amostras(larga.columns, canal) for canal in SIGNAL_COLUMNS}
    sem = [c for c, v in cols.items() if not v]
    if sem:
        raise ValueError(f"Canais sem colunas de amostras (<canal>_001…): {sem}")
    n = min(len(v) for v in cols.values())
    if len({len(v) for v in cols.values()}) > 1:
        print(f"[fetch_sheet] AVISO: canais com nº de amostras diferente; usando {n}")

    ids = larga[ID_COLUMNS].copy()
    ids["ensaio"] = pd.to_numeric(ids["ensaio"].str.strip(), errors="coerce")
    ids["frequencia_hz"] = pd.to_numeric(ids["frequencia_hz"].str.replace(",", "."), errors="coerce")
    ids["bloco"] = pd.to_numeric(ids["segundo"].str.replace(",", "."), errors="coerce")
    ids["sentido"] = ids["sentido"].map(normaliza_sentido)
    ok = ids["ensaio"].notna() & ids["frequencia_hz"].notna() & (ids["sentido"] != "")
    larga, ids = larga[ok].reset_index(drop=True), ids[ok].reset_index(drop=True)
    ids["ensaio"] = ids["ensaio"].astype(int)
    ids["frequencia_hz"] = ids["frequencia_hz"].round().astype(int)
    ids["linha"] = np.arange(len(ids))

    # Matriz linhas × amostras de cada canal -> formato longo (uma amostra por linha).
    longo = pd.DataFrame({
        canal: _para_numero(larga[cols[canal][:n]]).to_numpy().ravel()
        for canal in SIGNAL_COLUMNS
    })
    rep = ids.loc[ids.index.repeat(n)].reset_index(drop=True)
    rep["pos"] = np.tile(np.arange(n), len(ids))
    df = pd.concat([rep, longo], axis=1)

    # Blocos vazios (célula em branco) não viram amostra.
    df = df.dropna(subset=SIGNAL_COLUMNS, how="all")

    # Se uma condição tiver mais de um bloco, os blocos ficam em sequência
    # (ordem: coluna "segundo", depois ordem de chegada).
    df = df.sort_values(["ensaio", "sentido", "frequencia_hz", "bloco", "linha", "pos"])
    df["amostra"] = df.groupby(["ensaio", "sentido", "frequencia_hz"]).cumcount() + 1
    df["t_s"] = ((df["amostra"] - 1) * PERIODO_AMOSTRA_S).round(4)

    # IMU inteiro zerado = falha de leitura -> ausente.
    falha_imu = (df[IMU_COLUMNS] == 0).all(axis=1)
    df.loc[falha_imu, IMU_COLUMNS] = np.nan
    if falha_imu.any():
        print(f"[fetch_sheet] {int(falha_imu.sum())} amostras com falha do IMU tratadas como ausentes")

    # Timestamp vem como "dd/mm/aaaa" ou "dd/mm/aaaa hh:mm:ss"; guarda também em ISO.
    ts = pd.to_datetime(df["timestamp"].str.strip(), format="%d/%m/%Y %H:%M:%S", errors="coerce")
    so_data = pd.to_datetime(df["timestamp"].str.strip(), format="%d/%m/%Y", errors="coerce")
    df["timestamp_iso"] = ts.fillna(so_data).dt.strftime("%Y-%m-%dT%H:%M:%S")
    return df[LONG_COLUMNS].reset_index(drop=True)


COLS_MOTORES = ["ensaio", "motor", "observacao", "classificacao", "atualizado_em"]


def parse_motores(texto: str, sep: str) -> pd.DataFrame:
    """Aba MOTORES (ensaio | motor | observacao | classificacao | atualizado_em).
    Se a aba não existir o Google
    pode devolver a primeira aba — só aceitamos se houver a coluna 'motor'."""
    df = pd.read_csv(io.StringIO(texto), sep=sep, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    if not {"ensaio", "motor"} <= set(df.columns):
        return pd.DataFrame(columns=COLS_MOTORES)
    for c in COLS_MOTORES:
        if c not in df.columns:
            df[c] = ""
    df = df[COLS_MOTORES].apply(lambda c: c.str.strip())
    df["ensaio"] = pd.to_numeric(df["ensaio"], errors="coerce")
    df = df.dropna(subset=["ensaio"])
    df = df[(df["motor"] != "") | (df["observacao"] != "") | (df["classificacao"] != "")]
    df["ensaio"] = df["ensaio"].astype(int)
    return df.drop_duplicates("ensaio", keep="last")


def _sep(caminho: Path) -> str:
    """Exportação do Google: .tsv separa por tabulação, .csv por vírgula."""
    return "\t" if caminho.suffix.lower() in (".tsv", ".txt") else ","


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exemplo", action="store_true",
                        help="Usa data/exemplo/raw_exemplo.tsv em vez da planilha")
    parser.add_argument("--dados", type=Path,
                        help="Arquivo exportado da aba DADOS (.tsv ou .csv) em vez da planilha")
    parser.add_argument("--motores", type=Path,
                        help="Arquivo exportado da aba MOTORES (.tsv ou .csv); usado com --dados")
    args = parser.parse_args()
    if args.exemplo:
        args.dados, args.motores = EXEMPLO_TSV, EXEMPLO_MOTORES_TSV

    if args.dados:
        df = parse_tabela(args.dados.read_text(encoding="utf-8-sig"), _sep(args.dados))
        origem = str(args.dados)
    else:
        df = parse_tabela(_baixa_texto(LIVE_URL), ",")
        origem = "planilha (aba DADOS, ao vivo)"

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_PATH, index=False)

    try:
        if args.dados:
            if not args.motores:
                raise ValueError("sem --motores")
            motores = parse_motores(args.motores.read_text(encoding="utf-8-sig"), _sep(args.motores))
        else:
            try:
                if not MOTORES_API_URL:
                    raise ValueError("MOTORES_API_URL vazio em config.py")
                r = json.loads(_baixa_texto(MOTORES_API_URL))
                if not (r.get("ok") and isinstance(r.get("linhas"), list)):
                    raise ValueError("Apps Script sem 'listar' (reimplante a nova versão)")
                linhas = pd.DataFrame(r["linhas"], columns=COLS_MOTORES).fillna("")
                motores = parse_motores(linhas.to_csv(index=False), ",")
            except Exception as err:
                if not MOTORES_URL:
                    raise
                print(f"[fetch_sheet] MOTORES via Apps Script falhou ({err}); usando o link publicado.")
                motores = parse_motores(_baixa_texto(MOTORES_URL), ",")
    except Exception as err:
        print(f"[fetch_sheet] Aba MOTORES indisponível ({err}).")
        motores = parse_motores(",".join(COLS_MOTORES) + "\n", ",")
    motores.to_csv(MOTORES_PATH, index=False)
    sem_motor = sorted(set(df["ensaio"]) - set(motores["ensaio"]))
    print(f"[fetch_sheet] {len(motores)} motores cadastrados -> {MOTORES_PATH}")
    if sem_motor:
        print(f"[fetch_sheet] AVISO: ensaios sem motor na aba MOTORES: {sem_motor}")

    desconhecidos = sorted(set(df["sentido"]) - {"H", "AH"})
    blocos = df.groupby(["ensaio", "sentido", "frequencia_hz"]).size()
    print(
        f"[fetch_sheet] {len(df)} amostras ({len(blocos)} condições, "
        f"{df['ensaio'].nunique()} ensaios) de {origem} -> {RAW_PATH} — "
        f"{datetime.now(timezone.utc).isoformat()}"
    )
    if desconhecidos:
        print(f"[fetch_sheet] AVISO: valores de 'sentido' não reconhecidos: {desconhecidos}")
    freqs = sorted(df["frequencia_hz"].unique())
    if set(freqs) - {15000, 20000}:
        print(f"[fetch_sheet] AVISO: frequências fora do roteiro encontradas: {freqs}")


if __name__ == "__main__":
    main()
