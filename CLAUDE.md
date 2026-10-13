# Contexto do projeto — Jiga Ruído Motor V3 (Olsen)

Sucessor de `olseneletronica/jiga-ruido-motor-olsen_V2`, com a mesma estrutura:
dashboard estático (GitHub Pages, Chart.js + PapaParse, sem build step) lendo
Google Sheets publicado, e pipeline Python. Muda o formato dos dados
(firmware V0.06).

- Escopo: front-end e análise de dados. Firmware ESP32 e script que recebe os
  dados na planilha estão fora.
- Ensaio = 4 condições: {15 kHz, 20 kHz} × {horário "H", anti-horário "AH"}.
  Chave de condição `"{sentido}_{frequencia_hz}"` (ex: `AH_20000`).
- **Formato largo**: cada linha da planilha = 1 bloco de 1 condição, com
  `timestamp | firmware | ensaio | sentido | frequencia_hz | segundo` +
  `<canal>_001…<canal>_200` para os 14 canais (2806 colunas). Hoje 4 linhas
  por ensaio, 200 amostras a cada 15 ms. N é detectado pelo cabeçalho; o
  período é `PERIODO_AMOSTRA_S` (config.py) / `CONFIG.PERIODO_AMOSTRA_S` (app.js).
- O formato largo é "esticado" para uma amostra por linha logo na leitura:
  `fetch_sheet.parse_tabela()` (Python, colunas `bloco`, `amostra`, `t_s`) e
  `expandeLinhas()` (JS, campos `amostra`, `t`). O resto do código é o do V2
  trabalhando amostra a amostra. Regex de colunas ancorado
  (`^canal_(\d+)$`) para `audio1_dbfs` não casar com `audio1_peak_dbfs`.
- Vários blocos na mesma condição são emendados (ordem de `segundo`, depois
  de chegada).
- `timestamp` hoje vem só com a data (`13/10/2026`): `parseTimestamp()` marca
  `soData` e os formatadores não mostram hora falsa. Duração = tempo amostrado
  (nº de amostras × período), não diferença de timestamps.
- Fonte ao vivo: link "Publicar na Web" `pub?output=csv` (primeira aba). Vírgula
  decimal. MOTORES: Apps Script `?acao=listar` (`CONFIG.MOTORES_WRITE_URL` /
  `MOTORES_API_URL`, vazios até ser implantado) e reserva opcional por link
  publicado da aba (`MOTORES_URL`). Não há gviz neste projeto (ID da planilha
  não está no repo).
- `scripts/config.py` é a fonte única; `CONFIG`/`METRICS` em app.js espelham.
  `normaliza_sentido()` (Py) e `normalizaSentido()` (JS) aceitam as mesmas grafias.
- Falha do IMU por amostra: só quando os 7 canais = 0 -> NaN. A regra do V2
  (`accel_z_g` < 0,2 g = falha) foi REMOVIDA: no V3 ela apagava amostras reais
  do ensaio 2 (13/10), cujo Z oscila de ~0 a 1,8 g por vibração forte.
- Vibração e giroscópio comparados pelo desvio-padrão (média do acelerômetro
  tem a gravidade). Desvio agora é de 200 amostras rápidas: limites do V2 não
  se aplicam; indicação automática reaprende com os Aprovados (mínimo 5).
- Fontes fixas `?fonte=`: `exemplo` (sintético, `gerar_dados_exemplo.py`,
  8 motores) e `amostra_2026-10-13` (ensaios reais 44 e 45).
- Observado em 44/45: áudio horário ~3 dB acima do anti-horário nos 2 mics
  (provável efeito de montagem); eixo Z alterna alto/baixo em ~80% das amostras seguidas (vibração periódica com alias).
- Cache do Pages: `VERSAO` no app.js + `?v=` no index.html, incrementar juntos.
- Repo público (plano Free; privado quebraria o Pages).
- O ambiente do Claude não acessa docs.google.com nem script.google.com: para
  reanalisar, o usuário exporta a aba DADOS (.tsv) ou cola o conteúdo.
