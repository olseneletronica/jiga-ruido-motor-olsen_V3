# Jiga Ruído Motor V3 — Olsen

Análise dos ensaios da jiga de motores (Bosch) — versão 3. Mesma estrutura do
[V2](https://github.com/olseneletronica/jiga-ruido-motor-olsen_V2) (dashboard
estático no GitHub Pages + pipeline Python), adaptada ao **firmware V0.06**,
que coleta **200 amostras a cada 15 ms** por condição de ensaio.

Este repositório cobre **front-end (dashboard) e análise de dados**. Firmware
do ESP32 e o script que recebe os dados na planilha ficam fora do escopo.

## O que mudou em relação ao V2

| | V2 (firmware V0.04) | V3 (firmware V0.06) |
|---|---|---|
| Condições por ensaio | 15/20 kHz × horário/anti-horário | igual |
| Amostragem | 1 leitura por segundo, ~20 s por condição | **200 amostras a cada 15 ms** (3 s por condição) |
| Linhas na planilha | uma por leitura (~80 por ensaio) | **uma por condição — 4 por ensaio** |
| Colunas | uma por canal (`tensao_v`, …) | **200 por canal** (`tensao_v_001` … `tensao_v_200`) |
| Leitura ao vivo | gviz pela aba `DADOS` | link **Publicar na Web** (CSV) |
| Eixo dos gráficos | segundo | **tempo (s)** dentro da condição |

O desvio-padrão (vibração, giroscópio, instabilidade do áudio) agora é medido
sobre 200 amostras rápidas: capta vibração que a leitura de 1/s não via, e por
isso **os limites do V2 não valem aqui** — eles são reaprendidos com os motores
aprovados do V3.

## Fonte de dados

- Link público (Publicar na Web, CSV, primeira aba = DADOS):
  `https://docs.google.com/spreadsheets/d/e/2PACX-1vT2wsrlEcMIWu9sEjRpumG7rGKjUGYPdmNSlArK2f8QZb9VDq3FYmK4DIwLRZM-sFhDSZ3P9OJfvgK0/pub?output=csv`
- Configurado em `scripts/config.py` (`LIVE_URL`) e `dashboard/app.js`
  (`CONFIG.LIVE_URL`).

> O link `pub?output=csv` sem `gid` publica **a primeira aba** da planilha.
> Mantenha a aba DADOS como primeira aba. Se ela mudar de posição, publique
> só a aba DADOS (`pub?gid=<gid>&single=true&output=csv`) e troque o link nos
> dois arquivos.

O botão **⟳ Atualizar dados** busca a planilha de novo sem recarregar a página.
O link publicado é atualizado pelo Google com alguns minutos de atraso.

### Formato da aba DADOS

Cada **linha** é um bloco de amostras de uma condição:

| Coluna | Descrição |
|---|---|
| `timestamp` | Data (e, se houver, hora) do ensaio: `dd/mm/aaaa` ou `dd/mm/aaaa hh:mm:ss` |
| `firmware` | Versão do firmware (ex.: `V0.06_200SAMPLES_CADA`) |
| `ensaio` | Número do ensaio (mesmo motor = mesmo número) |
| `sentido` | `HORARIO` / `ANTIHORARIO` (aceita também `H`, `AH`, `CW`, `CCW`, com ou sem acento/hífen) |
| `frequencia_hz` | `15000` ou `20000` |
| `segundo` | Identificador do bloco (hoje sempre `3` = 3 s amostrados) |
| `<canal>_001` … `<canal>_200` | As 200 amostras de cada canal, a cada 15 ms |

Canais: `tensao_v`, `corrente_a`, `potencia_w`, `accel_x_g`, `accel_y_g`,
`accel_z_g`, `accel_resultante_g`, `gyro_x_dps`, `gyro_y_dps`, `gyro_z_dps`,
`audio1_dbfs`, `audio1_peak_dbfs`, `audio2_dbfs`, `audio2_peak_dbfs`.

- O número de amostras é detectado pelo cabeçalho: se o firmware passar a
  mandar 100 ou 400 amostras, o código se ajusta sozinho. Só o **período**
  (15 ms) é fixo: `PERIODO_AMOSTRA_S` em `config.py` e
  `CONFIG.PERIODO_AMOSTRA_S` em `app.js`.
- Se uma condição vier em mais de uma linha, os blocos são emendados em
  sequência (ordem da coluna `segundo`, depois ordem de chegada).
- Números com vírgula decimal (locale BR) são convertidos automaticamente.
- Amostras com o IMU inteiro zerado, ou com `accel_z_g` < 0,2 g (sem a
  gravidade), são falha de leitura do sensor: os canais do IMU daquela amostra
  viram ausentes.

### Aba MOTORES — qual motor foi testado em cada ensaio

Mesma aba do V2, na planilha V3, com o cabeçalho na linha 1:

| ensaio | motor | observacao | classificacao | atualizado_em |
|---|---|---|---|---|
| 44 | BOSCH-0451 | Lote 2026-10 | Aprovado | 13/10/2026 15:20:00 |

`classificacao`: `Aprovado`, `Reprovado`, `Em análise` ou vazio (classificação
**manual**, de quem inspecionou o motor). É ela que alimenta a indicação
automática do dashboard.

O dashboard lê essa aba pelo Apps Script de cadastro (abaixo). Enquanto ele
não estiver implantado, os ensaios aparecem sem nome de motor e a indicação
automática fica "Base insuficiente".

### Formulário de cadastro (Apps Script)

1. Na planilha V3, crie a aba **`MOTORES`** com o cabeçalho acima (ou deixe o
   script criar no primeiro cadastro).
2. https://script.google.com → **Novo projeto**. Cole o conteúdo de
   `apps-script/cadastro_motores.gs` e troque `PLANILHA_ID` pelo ID da planilha
   V3 (o trecho entre `/d/` e `/edit` no endereço da planilha). Salve.
3. **Configurações do projeto** → **Propriedades do script** → adicionar
   `TOKEN` = a senha de cadastro.
4. **Implantar → Nova implantação → App da Web**. Executar como: **Eu**. Quem
   pode acessar: **Qualquer pessoa**. Autorize o acesso.
5. Copie a URL (termina em `/exec`) e cole em `CONFIG.MOTORES_WRITE_URL`
   (`dashboard/app.js`) e em `MOTORES_API_URL` (`scripts/config.py`, com
   `?acao=listar` no fim). Commit/push.

A senha não vai para o repositório (que é público). Ao alterar o `.gs`, use
**Gerenciar implantações → editar → Nova versão** para manter a mesma URL.

Opcional (reserva): publique **só** a aba MOTORES em CSV
(`pub?gid=<gid>&single=true&output=csv`) e cole o link em
`CONFIG.MOTORES_URL` / `MOTORES_URL`.

## Estrutura

```
index.html                 redireciona para dashboard/ (GitHub Pages na raiz)
dashboard/
  index.html               página
  app.js                   lógica e gráficos (Chart.js + PapaParse)
  styles.css               tema escuro (padrão) e claro
  assets/olsen-logo.png
apps-script/
  cadastro_motores.gs      lê/grava a aba MOTORES (formulário do dashboard)
scripts/
  config.py                colunas, período de amostragem, limites — fonte única
  fetch_sheet.py           baixa a planilha e "estica" as 200 amostras -> data/raw_ensaios.csv
  features.py              resumo por condição e por ensaio
  sentido.py               comparação horário × anti-horário
  discriminantes.py        indicadores por motor, limites dos aprovados, validação
  baseline.py              referência de motor bom por condição
  classify.py              status por ensaio (OK / ATENCAO / FALHA_PROVAVEL)
  gerar_dados_exemplo.py   dados sintéticos no formato V3
  run_pipeline.py          roda tudo em sequência
data/
  exemplo/                 dados sintéticos (8 motores)
  amostra_2026-10-13/      exportação dos ensaios 44 e 45 (primeiros do firmware V0.06)
```

## Dashboard

GitHub Pages servindo a **raiz** do repositório (Settings → Pages → Branch
`main`, pasta `/ (root)`). Endereço:
`https://olseneletronica.github.io/jiga-ruido-motor-olsen_V3/`.

Abas (iguais às do V2):

1. **Ensaio individual** — data, tempo amostrado, firmware, amostras por
   condição; tabela-resumo por condição; gráficos com as 200 amostras de cada
   condição no tempo (cor = frequência, contínuo = horário, tracejado =
   anti-horário); formulário de cadastro do motor.
2. **Horário × Anti-horário** — diferença AH − H por canal nas duas
   frequências, tabela de valores e mapa de calor de todos os ensaios.
3. **Comparar ensaios** — até 8 ensaios numa condição, com filtro por
   classificação.
4. **Visão geral** — indicação automática (aprende com os Aprovados, mínimo 5),
   tabela de ensaios e média de cada grandeza por ensaio/condição.

Fontes fixas (sem ler a planilha):

- `dashboard/?fonte=exemplo` — 8 motores sintéticos: 1–6 bons, 7 com
  vibração/ruído só no anti-horário a 20 kHz, 8 com falha geral.
- `dashboard/?fonte=amostra_2026-10-13` — ensaios 44 e 45 reais.

Teste local (o `fetch` não funciona abrindo o arquivo direto):

```bash
python -m http.server 8000
# http://localhost:8000/dashboard/?fonte=exemplo
```

## Pipeline Python

```bash
pip install -r requirements.txt

python scripts/run_pipeline.py                         # planilha real
python scripts/run_pipeline.py --good 44 45 …          # + baseline/classify com motores bons
python scripts/run_pipeline.py --exemplo --good 1 2 3 4 5 6
python scripts/run_pipeline.py --dados data/amostra_2026-10-13/dados.tsv \
    --motores data/amostra_2026-10-13/motores.tsv      # a partir de exportação
```

`data/raw_ensaios.csv` tem **uma amostra por linha** (colunas `bloco`,
`amostra`, `t_s` + os 14 canais), então os demais scripts funcionam como no V2.

## Como funciona a análise

### Horário × anti-horário (não precisa de baseline)

| Canal | Estatística | Diferença | Limite inicial |
|---|---|---|---|
| Tensão, corrente, potência | média | % relativa | 10 % |
| Vibração e giroscópio | desvio-padrão das amostras | % relativa | 40 % |
| Áudio (médio e pico) | média | dB (AH − H) | 3 dB |

Assimetria = SIM quando ≥ 3 canais passam do limite na mesma frequência.

> Nos ensaios 44 e 45 o áudio no horário ficou ~3 dB **acima** do anti-horário
> nos dois microfones. Se isso se repetir em motores bons, é característica da
> montagem (e não do motor) e o limite de 3 dB precisa subir, senão todo motor
> sai com "assimetria".

### Indicação automática / discriminantes

Mesma regra do V2: 4 indicadores por motor (média das 4 condições) — nível de
áudio, instabilidade do áudio, vibração dinâmica e vibração lateral Y — com
limite = média + 3σ dos motores **Aprovado**. Recalculado a cada carga no
dashboard (`recalcAuto()`) e em `scripts/discriminantes.py`.

### Parâmetros a calibrar com dados reais do V3

| Onde | Parâmetro |
|---|---|
| `scripts/config.py` + `dashboard/app.js` | `LIMITE_ASSIMETRIA_REL_PCT`, `LIMITE_ASSIMETRIA_DB`, `MIN_CANAIS_ASSIMETRIA` |
| `scripts/classify.py` | `Z_THRESHOLD`, `FALHA_FRACAO` |

## Próximos passos

- Implantar o Apps Script de cadastro na planilha V3 e classificar os motores.
- Gravar a hora no `timestamp` (hoje só vem a data).
- Juntar ≥ 5 aprovados para a indicação automática e recalibrar limites.
- Com 15 ms de amostragem, avaliar o **espectro** (FFT) da vibração e do
  áudio — o eixo Z alterna alto/baixo em ~80% das amostras seguidas, sinal de vibração
  periódica que hoje só aparece como desvio-padrão.
