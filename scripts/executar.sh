#!/usr/bin/env bash
# Executa o plano em modo não-GUI e gera o relatório HTML do JMeter.
# Uso: ./scripts/executar.sh <carga|pico> [-Jpropriedade=valor ...]
#
# O plano test-plans/blazedemo-compra-passagem.jmx contém os dois cenários:
#   - grupo [CARGA] habilitado por padrão (teste de carga);
#   - grupos [PICO] desabilitados por padrão.
# Para o pico, o script gera uma cópia temporária com os grupos invertidos.
set -euo pipefail

TIPO="${1:?Informe o tipo de teste: carga ou pico}"
shift
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
PLANO="$RAIZ/test-plans/blazedemo-compra-passagem.jmx"
JMETER="${JMETER_HOME:+$JMETER_HOME/bin/}jmeter"
SAIDA="$RAIZ/results/$TIPO-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$SAIDA"

case "$TIPO" in
  carga) ;;
  pico)
    TMP="$SAIDA/plano-pico.jmx"
    sed -e 's/testname="\[CARGA\]\([^"]*\)" enabled="true"/testname="[CARGA]\1" enabled="false"/' \
        -e 's/testname="\[PICO\]\([^"]*\)" enabled="false"/testname="[PICO]\1" enabled="true"/' \
        "$PLANO" > "$TMP"
    PLANO="$TMP"
    ;;
  *) echo "Tipo inválido: $TIPO (use carga ou pico)"; exit 1 ;;
esac

"$JMETER" -n \
  -t "$PLANO" \
  -l "$SAIDA/resultado.jtl" \
  -j "$SAIDA/jmeter.log" \
  -e -o "$SAIDA/relatorio-html" \
  -Jmassa="$RAIZ/test-plans/massa.csv" \
  -Jjmeter.save.saveservice.output_format=csv \
  "$@"

echo
echo "Resultados em: $SAIDA"
echo "Relatório HTML: $SAIDA/relatorio-html/index.html"
