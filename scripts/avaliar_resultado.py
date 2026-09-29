#!/usr/bin/env python3
"""
Avalia um arquivo de resultados do JMeter (.jtl em CSV) contra o critério de aceitação:
    vazão >= 250 req/s  E  percentil 90 do tempo de resposta < 2000 ms

Como a vazão média do teste inteiro é "puxada para baixo" pelas rampas de subida/descida,
a avaliação é feita numa janela de regime (steady state), informada em segundos a partir
da primeira requisição.

Uso:
    python3 scripts/avaliar_resultado.py <arquivo.jtl> [--inicio 60] [--fim 360]
                                         [--rps-alvo 250] [--p90-alvo 2000]
"""
import argparse
import csv
import math
import sys


def percentil(valores, p):
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    k = max(0, math.ceil(p / 100 * len(ordenados)) - 1)
    return float(ordenados[k])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("jtl")
    ap.add_argument("--inicio", type=float, default=0, help="início da janela (s após a 1ª amostra)")
    ap.add_argument("--fim", type=float, default=None, help="fim da janela (s após a 1ª amostra)")
    ap.add_argument("--rps-alvo", type=float, default=250)
    ap.add_argument("--p90-alvo", type=float, default=2000)
    args = ap.parse_args()

    with open(args.jtl, newline="", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    if not linhas:
        sys.exit("JTL vazio.")

    t0 = min(int(l["timeStamp"]) for l in linhas)
    ini = t0 + args.inicio * 1000
    fim = t0 + args.fim * 1000 if args.fim is not None else float("inf")
    janela = [l for l in linhas if ini <= int(l["timeStamp"]) < fim]
    if not janela:
        sys.exit("Nenhuma amostra na janela informada.")

    duracao = (max(int(l["timeStamp"]) for l in janela) - min(int(l["timeStamp"]) for l in janela)) / 1000 or 1
    tempos = [int(l["elapsed"]) for l in janela]
    erros = sum(1 for l in janela if l["success"] != "true")
    rps = len(janela) / duracao
    p90 = percentil(tempos, 90)

    print(f"Janela analisada : {args.inicio:.0f}s -> {'fim' if args.fim is None else f'{args.fim:.0f}s'} ({duracao:.0f}s)")
    print(f"Requisições      : {len(janela)}  (erros: {erros} = {erros / len(janela):.2%})")
    print(f"Vazão            : {rps:.1f} req/s   (alvo >= {args.rps_alvo:.0f})")
    print(f"Percentil 90     : {p90:.0f} ms      (alvo < {args.p90_alvo:.0f})")
    print()
    print(f"{'Transação':45} {'qtd':>7} {'p90 (ms)':>9} {'erros':>7}")
    for label in sorted({l["label"] for l in janela}):
        amostras = [l for l in janela if l["label"] == label]
        e = sum(1 for l in amostras if l["success"] != "true")
        print(f"{label:45} {len(amostras):>7} {percentil([int(l['elapsed']) for l in amostras], 90):>9.0f} {e:>7}")
    print()

    ok_rps = rps >= args.rps_alvo
    ok_p90 = p90 < args.p90_alvo
    print(f"[{'OK ' if ok_rps else 'NOK'}] Vazão")
    print(f"[{'OK ' if ok_p90 else 'NOK'}] Percentil 90")
    aprovado = ok_rps and ok_p90
    print(f"\nCRITÉRIO DE ACEITAÇÃO: {'SATISFEITO' if aprovado else 'NÃO SATISFEITO'}")
    sys.exit(0 if aprovado else 1)


if __name__ == "__main__":
    main()
