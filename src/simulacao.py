"""
LaunchLab UniFAP - Semana 1
Simulacao da base sintetica de solicitantes

Gera uma coorte sintetica de solicitantes, submete cada um a regra legada e
a regra nova (importada de triagem.py, sem reimplementar a logica) e mede a
diferenca. Os numeros do README (secoes 5 e 7) saem daqui.

Uso: python3 src/simulacao.py
"""

import random

from triagem import LIMIAR_APROVACAO, avaliar

# ---------------------------------------------------------------------------
# PREMISSAS DA COORTE SINTETICA
# ---------------------------------------------------------------------------

SEMENTE = 42                    # fixa: a simulacao e reproduzivel
N_SOLICITANTES = 500            # volume mensal de solicitacoes no posto

# Composicao por vinculo. Publico de microcredito comunitario em area
# periferica: majoritariamente informal, bem acima da media nacional.
FATIA_INFORMAL_PURO = 0.60      # renda CLT = 0
FATIA_RENDA_PARCIAL = 0.22      # bico/CLT parcial, abaixo da referencia
FATIA_FORMAL_PLENO = 0.18       # CLT igual ou acima da referencia

# Distribuicao do Score Social: Beta(5, 3) reescalada para 0-100.
# Media 62,5 pontos, assimetrica a direita: a maioria do publico paga em dia.
SCORE_ALFA = 5.0
SCORE_BETA = 3.0

RENDA_PARCIAL_MIN = 200.0
RENDA_PARCIAL_MAX = 1500.0
RENDA_FORMAL_MEDIA_LOG = 7.5    # lognormal: mediana ~ R$ 1.808
RENDA_FORMAL_SIGMA_LOG = 0.45

# Regra legada, reproduzida aqui apenas para servir de linha de base
LEGADO_SCORE_MINIMO = 60
LEGADO_RENDA_MINIMA = 1500.0

# ---------------------------------------------------------------------------
# PREMISSAS FINANCEIRAS
# ---------------------------------------------------------------------------

TICKET_MEDIO = 1200.00
PRAZO_MESES = 12
JUROS_MENSAL = 0.025
INADIMPLENCIA_ESPERADA = 0.08   # conservadora: ver justificativa no README
CUSTO_OPERACIONAL_CONTRATO = 60.00


def gerar_coorte(semente=SEMENTE, n=N_SOLICITANTES):
    """Gera a coorte sintetica como lista de (score_social, renda_formal).

    Premissa central: o Score Social e sorteado da MESMA distribuicao para os
    tres segmentos, independente do vinculo. Isto e a hipotese do projeto
    (formalidade nao prediz adimplencia) assumida como verdadeira, nao um
    resultado demonstrado pela simulacao. Ver ressalva no README, secao 7.
    """
    rng = random.Random(semente)
    coorte = []

    for _ in range(n):
        score = rng.betavariate(SCORE_ALFA, SCORE_BETA) * 100.0
        sorteio = rng.random()

        if sorteio < FATIA_INFORMAL_PURO:
            segmento, renda = "informal_puro", 0.0
        elif sorteio < FATIA_INFORMAL_PURO + FATIA_RENDA_PARCIAL:
            segmento = "renda_parcial"
            renda = rng.uniform(RENDA_PARCIAL_MIN, RENDA_PARCIAL_MAX)
        else:
            segmento = "formal_pleno"
            # trunca a lognormal na referencia: o segmento e, por definicao,
            # quem tem CLT igual ou acima de R$ 1.500
            renda = RENDA_PARCIAL_MAX - 1
            while renda < RENDA_PARCIAL_MAX:
                renda = rng.lognormvariate(RENDA_FORMAL_MEDIA_LOG, RENDA_FORMAL_SIGMA_LOG)

        coorte.append((segmento, int(round(score)), round(renda, 2)))

    return coorte


def aprovado_no_legado(score_social, renda_formal):
    # o E logico do sistema antigo: score alto E renda formal comprovada
    return score_social >= LEGADO_SCORE_MINIMO and renda_formal > LEGADO_RENDA_MINIMA


def aprovado_no_novo(score_social, renda_formal):
    _, _, aprovado = avaliar(score_social, renda_formal)
    return aprovado


def simular(coorte):
    resultado = {
        "total": len(coorte),
        "aprovados_legado": 0,
        "aprovados_novo": 0,
        "ganhos": 0,        # reprovados no legado, aprovados no novo
        "perdidos": 0,      # aprovados no legado, reprovados no novo
        "por_segmento": {},
    }

    for segmento, score, renda in coorte:
        stats = resultado["por_segmento"].setdefault(
            segmento, {"total": 0, "legado": 0, "novo": 0}
        )
        stats["total"] += 1

        legado = aprovado_no_legado(score, renda)
        novo = aprovado_no_novo(score, renda)

        resultado["aprovados_legado"] += legado
        resultado["aprovados_novo"] += novo
        stats["legado"] += legado
        stats["novo"] += novo

        if novo and not legado:
            resultado["ganhos"] += 1
        if legado and not novo:
            resultado["perdidos"] += 1

    return resultado


def juros_totais_price(principal, taxa, prazo):
    """Juros pagos ao longo de um contrato Price, em reais."""
    parcela = principal * taxa / (1 - (1 + taxa) ** -prazo)
    return parcela * prazo - principal


def projetar_financeiro(novos_contratos):
    volume = novos_contratos * TICKET_MEDIO
    juros_contrato = juros_totais_price(TICKET_MEDIO, JUROS_MENSAL, PRAZO_MESES)
    receita = novos_contratos * juros_contrato
    perda = volume * INADIMPLENCIA_ESPERADA
    custo = novos_contratos * CUSTO_OPERACIONAL_CONTRATO
    liquido = receita - perda - custo

    return {
        "novos_contratos": novos_contratos,
        "juros_por_contrato": juros_contrato,
        "volume_mensal": volume,
        "receita_mensal": receita,
        "perda_mensal": perda,
        "custo_mensal": custo,
        "liquido_mensal": liquido,
        "liquido_anual": liquido * 12,
        "volume_anual": volume * 12,
        "inadimplencia_equilibrio": (receita - custo) / volume if volume else 0.0,
    }


def pct(parte, total):
    return 100.0 * parte / total if total else 0.0


def analise_sensibilidade(n_sementes=50):
    """Repete a simulacao com sementes diferentes.

    Serve para separar o que e efeito da regra do que e sorte de uma coorte
    especifica, e para verificar em todas as coortes a propriedade central:
    a regra nova nunca retira uma aprovacao que a regra legada concedia.
    """
    legado, novo, ganhos, regressoes = [], [], [], 0

    for semente in range(1, n_sementes + 1):
        r = simular(gerar_coorte(semente=semente))
        legado.append(pct(r["aprovados_legado"], r["total"]))
        novo.append(pct(r["aprovados_novo"], r["total"]))
        ganhos.append(r["ganhos"])
        regressoes += r["perdidos"]

    return {
        "n_sementes": n_sementes,
        "legado_min": min(legado), "legado_media": sum(legado) / len(legado),
        "legado_max": max(legado),
        "novo_min": min(novo), "novo_media": sum(novo) / len(novo),
        "novo_max": max(novo),
        "ganhos_min": min(ganhos), "ganhos_media": sum(ganhos) / len(ganhos),
        "ganhos_max": max(ganhos),
        "regressoes": regressoes,
    }


def main():
    coorte = gerar_coorte()
    r = simular(coorte)
    f = projetar_financeiro(r["ganhos"])

    print("=" * 66)
    print("SIMULACAO DA COORTE SINTETICA")
    print("=" * 66)
    print(f"Semente ...................: {SEMENTE} (reproduzivel)")
    print(f"Solicitantes ..............: {r['total']}")
    print(f"Limiar de aprovacao .......: {LIMIAR_APROVACAO:.0f} pontos")
    print()

    print("--- TRIAGEM: REGRA LEGADA vs REGRA NOVA ---")
    print(f"Aprovados no legado .......: {r['aprovados_legado']:4d} "
          f"({pct(r['aprovados_legado'], r['total']):5.1f}%)")
    print(f"Aprovados no novo .........: {r['aprovados_novo']:4d} "
          f"({pct(r['aprovados_novo'], r['total']):5.1f}%)")
    print(f"Rejeicao no legado ........: "
          f"{pct(r['total'] - r['aprovados_legado'], r['total']):5.1f}%")
    print(f"Rejeicao no novo ..........: "
          f"{pct(r['total'] - r['aprovados_novo'], r['total']):5.1f}%")
    print(f"Destravados pelo novo .....: {r['ganhos']:4d}")
    print(f"Perdidos pelo novo ........: {r['perdidos']:4d} "
          f"(deve ser 0: a regra nunca retira aprovacao)")
    print()

    print("--- POR SEGMENTO ---")
    print(f"{'Segmento':<16}{'Total':>7}{'Legado':>9}{'Novo':>8}"
          f"{'% legado':>11}{'% novo':>9}")
    for nome in ("informal_puro", "renda_parcial", "formal_pleno"):
        s = r["por_segmento"][nome]
        print(f"{nome:<16}{s['total']:>7}{s['legado']:>9}{s['novo']:>8}"
              f"{pct(s['legado'], s['total']):>10.1f}%{pct(s['novo'], s['total']):>8.1f}%")
    print()

    print("--- PROJECAO FINANCEIRA (sobre os contratos destravados) ---")
    print(f"Novos contratos/mes .......: {f['novos_contratos']:>12d}")
    print(f"Juros por contrato ........: R$ {f['juros_por_contrato']:>11,.2f}")
    print(f"Volume desembolsado/mes ...: R$ {f['volume_mensal']:>11,.2f}")
    print(f"(+) Receita de juros/mes ..: R$ {f['receita_mensal']:>11,.2f}")
    print(f"(-) Perda inadimplencia ...: R$ {f['perda_mensal']:>11,.2f}")
    print(f"(-) Custo operacional .....: R$ {f['custo_mensal']:>11,.2f}")
    print(f"(=) Liquido mensal ........: R$ {f['liquido_mensal']:>11,.2f}")
    print(f"(=) Liquido anual .........: R$ {f['liquido_anual']:>11,.2f}")
    print(f"Volume anual ..............: R$ {f['volume_anual']:>11,.2f}")
    print(f"Inadimplencia de equilibrio: {f['inadimplencia_equilibrio'] * 100:>12.2f}%")
    print()

    s = analise_sensibilidade()
    print(f"--- SENSIBILIDADE ({s['n_sementes']} sementes) ---")
    print(f"{'Metrica':<26}{'min':>10}{'media':>10}{'max':>10}")
    print(f"{'Aprovacao legado (%)':<26}{s['legado_min']:>10.1f}"
          f"{s['legado_media']:>10.1f}{s['legado_max']:>10.1f}")
    print(f"{'Aprovacao novo (%)':<26}{s['novo_min']:>10.1f}"
          f"{s['novo_media']:>10.1f}{s['novo_max']:>10.1f}")
    print(f"{'Contratos destravados':<26}{s['ganhos_min']:>10d}"
          f"{s['ganhos_media']:>10.0f}{s['ganhos_max']:>10d}")
    print(f"Aprovacoes retiradas pela regra nova: {s['regressoes']} "
          f"(em {s['n_sementes']} coortes)")
    print("=" * 66)


if __name__ == "__main__":
    main()
