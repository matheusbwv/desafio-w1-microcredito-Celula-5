"""
LaunchLab UniFAP - Semana 1
Sistema de Score de Microcredito Inclusivo
Cooperativa de Microcredito Comunitario - Celula 5 (Sistemas de Informacao)
"""

LIMIAR_APROVACAO = 60.0
PESO_MAX_RENDA = 20.0      # teto: impede que renda alta compense score ruim
RENDA_REFERENCIA = 1500.0

SCORE_MINIMO = 0
SCORE_MAXIMO = 100


def calcular_bonus_renda(renda_formal):
    # renda so soma, nunca subtrai: nao pode ser criterio excludente
    if renda_formal <= 0:
        return 0.0

    proporcao = min(renda_formal / RENDA_REFERENCIA, 1.0)
    return proporcao * PESO_MAX_RENDA


def avaliar(score_social, renda_formal):
    bonus_renda = calcular_bonus_renda(renda_formal)
    pontuacao_final = score_social + bonus_renda
    aprovado = pontuacao_final >= LIMIAR_APROVACAO

    return pontuacao_final, bonus_renda, aprovado


def sanitizar_entradas(score_social, renda_formal):
    score_social = max(SCORE_MINIMO, min(score_social, SCORE_MAXIMO))
    renda_formal = max(0.0, renda_formal)

    return score_social, renda_formal


def calcular_triagem():
    print("--- SISTEMA DE MICROCRÉDITO INCLUSIVO UniFAP ---")

    try:
        score_social = int(input("Digite o Score Social Alternativo (0-100): "))
        renda_formal = float(input("Digite a Renda Formal CLT (R$): "))
    except ValueError:
        print("Entrada invalida: informe apenas numeros.")
        return

    # clamp em vez de perguntar de novo (a CI manda so 2 linhas)
    score_social, renda_formal = sanitizar_entradas(score_social, renda_formal)

    pontuacao_final, bonus_renda, aprovado = avaliar(score_social, renda_formal)

    print()
    print("----------- MEMORIA DE CALCULO -----------")
    print(f"Score Social Alternativo ..: {score_social:6.2f} pontos")
    print(f"Bonus por Renda Formal ....: {bonus_renda:6.2f} pontos (teto: {PESO_MAX_RENDA:.0f})")
    print(f"Pontuacao Final ...........: {pontuacao_final:6.2f} pontos")
    print(f"Limiar de Aprovacao .......: {LIMIAR_APROVACAO:6.2f} pontos")
    print("------------------------------------------")
    print()

    if aprovado:
        print("Resultado: Aprovado")
    else:
        print("Resultado: Reprovado")
        print("Voce tem direito a revisao humana desta analise (LGPD, art. 20).")


if __name__ == "__main__":
    calcular_triagem()
