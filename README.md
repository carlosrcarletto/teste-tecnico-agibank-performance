# Teste Técnico de Performance – BlazeDemo (JMeter)

Script de **teste de carga** e **teste de pico** em Apache JMeter para o cenário de
**compra de passagem aérea** em <https://www.blazedemo.com>.

## Critério de aceitação

| Métrica | Alvo |
|---|---|
| Vazão | **≥ 250 requisições por segundo** |
| Tempo de resposta (percentil 90) | **< 2 segundos** |

## Resumo dos resultados

| Teste | Vazão | Percentil 90 | Erros | Critério |
|---|---|---|---|---|
| Carga (regime, 60–360 s) | **246,4 req/s** | **817 ms** | 0,01% | ❌ **Não satisfeito** (vazão 1,4% abaixo) |
| Pico (janela do pico, 130–240 s) | **272,8 req/s** | **1.923 ms** | 0,03% | ✅ **Satisfeito** (no limite) |

Análise completa na seção [Relatório de execução](#relatório-de-execução).

## Cenário automatizado

Cada iteração de um usuário virtual executa o fluxo completo de compra:

| # | Requisição | Validação (Response Assertion) |
|---|---|---|
| 01 | `GET /` – Home | HTTP 200 + `Welcome to the Simple Travel Agency!` |
| 02 | `POST /reserve.php` – Buscar voos (origem/destino) | HTTP 200 + `Flights from <origem> to <destino>` |
| 03 | `POST /purchase.php` – Escolher voo | HTTP 200 + `has been reserved.` |
| 04 | `POST /confirmation.php` – Finalizar compra | HTTP 200 + **`Thank you for your purchase today!`** |

Detalhes de implementação:

- **Massa de dados** (`test-plans/massa.csv`): rotas de origem/destino e dados do passageiro/cartão, lidos com *CSV Data Set Config*.
- **Correlação**: na etapa 02 um *Regular Expression Extractor* captura, de forma **aleatória**, um dos voos listados (`flight`, `price` e `airline`), que são enviados na etapa 03.
- **Sessão**: *HTTP Cookie Manager* limpo a cada iteração (cada iteração = uma nova compra).
- **Controle de vazão**: *Constant Throughput Timer* (modo *all active threads in current thread group – shared*). Ele limita a vazão ao alvo definido; as threads configuradas são o "estoque" de usuários para alcançá-lo.
- O campo `_token` do formulário de compra é renderizado vazio pelo site, então é enviado vazio (não precisa de correlação).
- Sem plugins: só componentes nativos do JMeter.

## Estrutura

```
.
├── test-plans/
│   ├── blazedemo-compra-passagem.jmx   # plano único: teste de carga + teste de pico
│   └── massa.csv                       # massa de dados (fica ao lado do .jmx)
├── scripts/
│   ├── executar.sh                     # executa em modo não-GUI e gera o relatório HTML
│   └── avaliar_resultado.py            # compara o .jtl com o critério de aceitação
└── results/
    ├── carga/                          # execução do teste de carga (jtl + relatório HTML)
    └── pico/                           # execução do teste de pico (jtl + relatório HTML)
```

## Plano de teste (`blazedemo-compra-passagem.jmx`)

O arquivo contém **três Thread Groups**, que compartilham o mesmo fluxo e as mesmas configurações:

| Thread Group | Habilitado por padrão | Uso |
|---|---|---|
| `[CARGA] Compra de passagem - 250 req/s sustentado` | ✅ | Teste de carga |
| `[PICO] Carga base - 50 req/s` | ❌ | Teste de pico |
| `[PICO] Pico - +250 req/s aos 120 s` | ❌ | Teste de pico |

No JMeter GUI, para rodar o **pico**, desabilite o grupo `[CARGA]` e habilite os dois grupos `[PICO]`
(botão direito → *Enable/Disable*). Pela linha de comando, o `scripts/executar.sh` faz isso sozinho.

### Teste de carga

| Parâmetro | Propriedade | Padrão |
|---|---|---|
| Usuários virtuais | `carga.threads` | 300 |
| Rampa de subida (s) | `carga.rampup` | 60 |
| Duração total (s) | `carga.duration` | 360 |
| Vazão alvo (req/s) | `carga.rps` | 250 |

Sobe gradualmente até 250 req/s em 60 s e **sustenta** essa vazão por 5 minutos.

Dimensionamento: com tempo de resposta médio de ~0,4 s por requisição, cada usuário faz ~2,5 req/s.
Para 250 req/s precisamos de ~100 usuários; 300 dá folga caso o tempo de resposta aumente sob carga.

### Teste de pico

| Grupo | Threads | Rampa | Início | Duração | Vazão alvo |
|---|---|---|---|---|---|
| Carga base (`base.*`) | 100 | 30 s | 0 s | 330 s | 50 req/s |
| Pico (`pico.*`) | 300 | **10 s** | 120 s | 120 s | +250 req/s |

```
req/s
 300 |              ┌──────────────┐
     |              │     PICO     │
     |              │  (~300 rps)  │
  50 |  ┌───────────┘              └───────────┐
     |  │  base                          base  │
   0 +──┴──────────┬──────────────┬────────────┴──> tempo (s)
     0            120            240          330
```

O tráfego salta de ~50 para **~300 req/s em ~10 s** (20% acima do critério), fica 2 minutos no pico
e volta à carga base. Assim dá para avaliar tanto o comportamento no pico quanto a recuperação depois dele.

Todos os parâmetros podem ser sobrescritos com `-J<propriedade>=<valor>`.

## Como executar

### Pré-requisitos

- Java 8+ (testado com OpenJDK 17)
- Apache JMeter 5.6.3 ([download](https://jmeter.apache.org/download_jmeter.cgi)) com o `bin/` no `PATH`, ou a variável `JMETER_HOME` apontando para a pasta de instalação
- Python 3 (só para o script de avaliação)

### Abrir no JMeter GUI

Abra `test-plans/blazedemo-compra-passagem.jmx` (*File → Open*). O `massa.csv` precisa estar na mesma pasta do `.jmx`.
O plano já tem um *Aggregate Report* e um *View Results Tree* (desabilitado; habilite só para depurar com poucos usuários).

> A execução de carga deve ser feita em **modo não-GUI**. A interface gráfica consome muitos recursos e distorce os resultados.

### Execução (modo não-GUI)

```bash
# Teste de carga
./scripts/executar.sh carga

# Teste de pico
./scripts/executar.sh pico

# Sobrescrevendo parâmetros
./scripts/executar.sh carga -Jcarga.threads=400 -Jcarga.duration=600
```

Cada execução cria `results/<tipo>-<data-hora>/` com `resultado.jtl`, `relatorio-html/index.html` (dashboard do JMeter) e `jmeter.log`.

Comando equivalente para o teste de carga, sem o script:

```bash
jmeter -n -t test-plans/blazedemo-compra-passagem.jmx -l results/carga.jtl -e -o results/carga-html
```

### Avaliação automática do critério

Como a vazão média do teste inteiro inclui as rampas, a avaliação é feita **na janela de regime**:

```bash
# Carga: descarta a rampa de 60 s
python3 scripts/avaliar_resultado.py results/carga/resultado.jtl --inicio 60 --fim 360

# Pico: só a janela do pico (120 s -> 240 s, descontando a rampa de 10 s)
python3 scripts/avaliar_resultado.py results/pico/resultado.jtl --inicio 130 --fim 240
```

O script mostra vazão, percentil 90, erros por transação e o veredito `SATISFEITO` / `NÃO SATISFEITO`.

## Relatório de execução

Execução em 29/09/2026 a partir de uma única máquina (macOS, JMeter 5.6.3, OpenJDK 17), em modo não-GUI.
Os dashboards HTML completos estão em:

- **Carga**: [`results/carga/relatorio-html/index.html`](results/carga/relatorio-html/index.html)
- **Pico**: [`results/pico/relatorio-html/index.html`](results/pico/relatorio-html/index.html)

### Teste de carga

| Métrica | Resultado | Alvo | Status |
|---|---|---|---|
| Vazão em regime (60–360 s) | **246,4 req/s** | ≥ 250 req/s | ❌ |
| Percentil 90 em regime | **817 ms** | < 2000 ms | ✅ |
| Requisições (teste inteiro) | 86.414 (~21.600 compras) | – | – |
| Taxa de erro | 0,01% (4 erros) | – | – |

| Transação | Qtd (regime) | p90 (ms) | Erros |
|---|---|---|---|
| 01 - Home | 18.486 | 1.245 | 4 |
| 02 - Buscar voos | 18.481 | 731 | 0 |
| 03 - Escolher voo | 18.453 | 706 | 0 |
| 04 - Finalizar compra | 18.465 | 716 | 0 |

Vazão e p90 a cada 10 s (trecho):

| Tempo | Vazão (req/s) | p90 (ms) | Máx (ms) |
|---|---|---|---|
| 20–150 s | 242–260 | 473–918 | até 2.884 |
| **160 s** | **148,6** | **4.021** | **15.583** |
| 170 s | 252,9 | 1.173 | 4.394 |
| 180–350 s | 239–260 | 462–1.942 | até 10.001 |

**Conclusão – carga: critério NÃO satisfeito.**

- O **tempo de resposta passou com folga**: p90 de 817 ms, menos da metade do limite de 2 s.
- A **vazão ficou 1,4% abaixo** do alvo (246,4 contra 250 req/s). Em quase toda a janela o sistema entregou ~250 req/s
  (entre 242 e 260 req/s a cada 10 s), mas **entre 160 e 170 s houve uma degradação pontual no servidor**:
  p90 subiu para 4 s, algumas requisições levaram até 15,5 s e a vazão caiu para 148 req/s. As threads ficaram
  presas esperando resposta, e esse deficit não foi compensado depois, o que puxou a média abaixo de 250.
- Também houve picos isolados de ~10 s de resposta ao longo do teste (máximo de 10.001 ms em várias janelas),
  sinal de enfileiramento/instabilidade no servidor sob carga contínua.
- Os 4 erros foram `NoRouteToHostException` na Home (falha de rede/conexão, não erro de negócio).
  **Todas as compras que chegaram à confirmação foram concluídas com sucesso.**

Como o critério pede as **duas** condições (vazão **e** p90), o resultado formal é **não satisfeito**. Na prática,
o sistema operou muito perto da vazão alvo, e o que impediu a aprovação foi a **instabilidade** (degradações
intermitentes), não a falta de capacidade de processamento.

### Teste de pico

| Métrica | Resultado | Alvo | Status |
|---|---|---|---|
| Vazão no pico (130–240 s) | **272,8 req/s** | ≥ 250 req/s | ✅ |
| Percentil 90 no pico | **1.923 ms** | < 2000 ms | ✅ (no limite) |
| Taxa de erro no pico | 0,03% (10 erros) | – | – |
| Recuperação após o pico | p90 voltou a ~400 ms em até 10 s | – | ✅ |

| Transação (pico) | Qtd | p90 (ms) | Erros |
|---|---|---|---|
| 01 - Home | 7.488 | 2.609 | 10 |
| 02 - Buscar voos | 7.525 | 1.704 | 0 |
| 03 - Escolher voo | 7.505 | 1.772 | 0 |
| 04 - Finalizar compra | 7.477 | 1.753 | 0 |

Vazão e p90 a cada 10 s:

| Fase | Tempo | Vazão (req/s) | p90 (ms) |
|---|---|---|---|
| Base | 0–110 s | ~50 | 400–1.000 |
| Subida do pico | 120–150 s | 271–309 | 492–1.741 |
| Pico – degradação | 160 s | 246,8 | 2.967 |
| Pico | 170–190 s | 292–308 | 549–2.019 |
| **Pico – degradação** | **200–210 s** | **163–191** | **2.087–7.039** (máx 24,9 s) |
| Pico | 220–230 s | 294–303 | 1.757–1.876 |
| Pós-pico | 240–330 s | ~50 | ~400 |

**Conclusão – pico: critério satisfeito, mas no limite.**

- O sistema **absorveu o salto de ~50 para ~300 req/s em 10 s** e, na média da janela do pico, entregou
  272,8 req/s com p90 de 1.923 ms, dentro do critério.
- A margem de tempo de resposta foi pequena (**77 ms abaixo do limite**), e a transação **Home isoladamente
  estourou o p90 (2,6 s)**. Durante o pico houve duas degradações (160 s e 200–210 s), com vazão caindo para
  163 req/s e respostas de até 25 s, o mesmo padrão observado no teste de carga.
- Os 10 erros foram de conexão (`NoRouteToHostException` e `NoHttpResponseException`) na Home: sob pico, o
  servidor começou a recusar/perder algumas conexões novas.
- **A recuperação foi imediata**: assim que o pico terminou, o p90 voltou a ~400 ms e a vazão base se manteve estável.

### Conclusão geral

| | Resultado |
|---|---|
| Teste de carga | ❌ Não satisfeito: p90 OK (817 ms), vazão 246,4 req/s (1,4% abaixo de 250) |
| Teste de pico | ✅ Satisfeito: 272,8 req/s e p90 de 1.923 ms (margem de só 4%) |

O BlazeDemo **suporta a ordem de grandeza de 250 req/s**, mas **não de forma estável**. Nos dois testes aparecem
degradações intermitentes (respostas de 10 a 25 s, quedas momentâneas de vazão e erros de conexão) que:

1. no teste de carga, reduziram a vazão média para logo abaixo do alvo;
2. no teste de pico, levaram o p90 para muito perto do limite de 2 s.

Por isso, a recomendação é **não considerar o critério de aceitação atendido de forma consistente**. Seria preciso
investigar a causa das degradações intermitentes (ex.: limite de conexões/workers no servidor, *rate limiting*,
coleta de lixo, dependências) e repetir os testes para confirmar a estabilidade.

## Considerações

- **Validação funcional**: antes dos testes de volume, o fluxo foi validado com 1 usuário (0% de erro, todas as
  asserções OK, incluindo a confirmação da compra).
- **Ambiente público**: o BlazeDemo é compartilhado e mantido pela BlazeMeter para demonstração. A latência e a
  estabilidade variam com fatores externos (outros usuários, CDN, rate limiting), então os resultados podem
  variar entre execuções e não são uma linha de base de produção. Exemplo: na fase base do teste de pico, o p90
  oscilou entre 400 ms e 1 s com a mesma carga de 50 req/s.
- **Gerador de carga**: os testes rodaram de uma única máquina, em rede doméstica. Os erros `NoRouteToHostException`
  podem ter origem na rede local e não só no servidor. Para uma avaliação definitiva, o ideal é rodar a partir de
  geradores dedicados (execução distribuída do JMeter ou BlazeMeter/nuvem).
- **Vazão como requisições HTTP**: o critério foi interpretado como 250 *requisições HTTP* por segundo
  (as 4 etapas do fluxo), o que equivale a ~62 compras completas por segundo.
- **Constant Throughput Timer**: ele limita a vazão ao alvo, mas não recupera o deficit de períodos lentos. Por
  isso uma degradação de 10 s basta para deixar a média abaixo de 250. Um alvo um pouco acima (ex.: 260 req/s)
  daria margem, mas mantive exatamente 250 para medir o critério como definido.
- **Boas práticas aplicadas**: execução em modo não-GUI, parametrização via propriedades (`-J`), asserções em todas
  as etapas, massa de dados externa e escolha dinâmica do voo.
- **Recursos embutidos** (CSS/JS de CDNs externas) não são baixados, para medir só o servidor do BlazeDemo.
