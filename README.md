# Sistema de Score de Microcrédito Inclusivo

**LaunchLab UniFAP 2026 · Semana 1 · Célula 5 · Sistemas de Informação**

Algoritmo de triagem de crédito para cooperativa de microcrédito comunitário, projetado para **não excluir trabalhadores do mercado informal**.

---

## 1. O Problema

A cooperativa atendia comunidades periféricas de Macapá com um motor de decisão que negava crédito automaticamente a quem não comprovasse **renda formal (CLT)**.

O efeito prático foi a exclusão de **95% das mulheres chefes de família** da comunidade: costureiras, feirantes, cozinheiras e diaristas que, apesar de não terem carteira assinada, mantinham **histórico exemplar de pagamento** no comércio do bairro.

O sistema não estava medindo risco de crédito. Estava medindo **formalidade de vínculo empregatício**, e tratando as duas coisas como se fossem a mesma.

### O defeito no sistema legado

```python
if score_social >= 60:
    if renda_formal > 1500:      # ← porta de exclusão
        print("Resultado: Aprovado")
    else:
        print("Resultado: Reprovado")
else:
    print("Resultado: Reprovado")
```

O aninhamento é um **E lógico**: exigia score alto **E** renda formal. Uma cliente com score social 100 e renda CLT R$ 0,00 caía no `else` interno e era reprovada. O bom histórico de pagamento era coletado, calculado e depois descartado pela regra seguinte.

---

## 2. Fluxo do Processo de Negócio

```mermaid
flowchart TD
    A[Solicitação de crédito<br/>no posto comunitário] --> A2[Visita de campo do agente:<br/>apuração das 5 variáveis informais<br/>que compõem o Score Social · ver §3]
    A2 --> B[Coleta mínima do sistema:<br/>Score Social + Renda Formal<br/>apenas 2 números · sem identificadores]
    B --> C[Sanitização<br/>score 0-100 · renda >= 0]
    C --> D[ETAPA 1: Análise primária<br/>Score Social Alternativo<br/>0 a 100 pontos]
    D --> E[ETAPA 2: Análise complementar<br/>Bônus por Renda Formal<br/>0 a 20 pontos · nunca negativo]
    E --> F[Pontuação Final =<br/>Score Social + Bônus]
    F --> G{Pontuação Final<br/>maior ou igual a 60?}
    G -->|Sim| H[Resultado: Aprovado]
    G -->|Não| I[Resultado: Reprovado]
    H --> K[Memória de cálculo<br/>entregue ao cliente]
    I --> K
    K --> L[Canal de revisão humana<br/>LGPD art. 20]
```

### Princípio de ordenação

A renda formal **só é consultada depois** que o score social já produziu sua pontuação, e **só pode somar**. Não existe caminho no fluxo em que renda baixa ou zero derrube uma decisão que o score social já sustentava. É essa a diferença entre *ponderar* e *excluir*.

---

## 3. Modelo de Pontuação e Justificativa dos Pesos

```
Pontuação Final = Score Social Alternativo + Bônus de Renda Formal

Bônus de Renda = min(renda_formal / 1500 ; 1,0) × 20

Aprovado  ⟺  Pontuação Final >= 60
```

### Parâmetros da política

| Parâmetro | Valor | Onde fica |
|---|---|---|
| `LIMIAR_APROVACAO` | 60,0 pontos | `src/triagem.py` |
| `PESO_MAX_RENDA` | 20,0 pontos | `src/triagem.py` |
| `RENDA_REFERENCIA` | R$ 1.500,00 | `src/triagem.py` |

Os três parâmetros estão isolados no topo do módulo, como constantes nomeadas. O comitê de crédito consegue recalibrar a política **sem tocar na lógica do algoritmo**, o que torna cada mudança de política um diff pequeno, legível e auditável no histórico do Git.

### Por que o Score Social pesa 100 e a renda pesa no máximo 20

**O score social carrega peso integral (0 a 100) porque é o preditor direto.** Ele resume comportamento observado de adimplência: pontualidade nas contas do bairro, regularidade do fluxo de caixa do negócio, tempo de atuação no local, referências de fornecedores e da associação de moradores. É *evidência de pagamento*. A renda CLT é apenas um *proxy* de capacidade de pagamento, e um proxy fraco: um assalariado superendividado com renda de R$ 3.000 é pior risco que uma feirante com R$ 0 de CLT e 12 anos de contas em dia.

**A renda formal recebe teto de 20 pontos (20% do score social) porque ainda carrega informação real, mas marginal.** Renda formal indica uma segunda fonte de recursos, independente do negócio: funciona como colchão em caso de sazonalidade ou choque na renda informal. É motivo legítimo para reforçar a nota, e motivo nenhum para vetar.

**O teto é a peça de contenção de risco.** Sem ele, renda suficientemente alta compraria a aprovação de qualquer solicitante. Com o teto em 20, quem tem score social 30 chega no máximo a 50 pontos, abaixo do limiar, **independentemente de ganhar R$ 3.000 ou R$ 100.000**. O modelo continua recusando mau histórico de pagamento, que é exatamente o que um motor de crédito deve fazer.

**A saturação em R$ 1.500 (≈ 1 salário mínimo) reflete rendimento decrescente.** A diferença de segurança entre R$ 0 e R$ 1.500 de renda formal é grande; entre R$ 5.000 e R$ 8.000, é irrelevante para um crédito de ticket médio R$ 1.200. Progressão linear até a referência e platô depois disso.

**O limiar de 60 preserva o corte de risco original.** A reforma não afrouxou a régua; moveu o *critério*. Quem tinha score social suficiente sob a regra antiga continua aprovado; quem era barrado apenas por falta de carteira assinada deixa de ser.

### Composição do Score Social Alternativo: pesos das variáveis informais

O Score Social (0 a 100) é o insumo do algoritmo, apurado pelo agente de crédito comunitário na visita de campo **antes** da execução do script. Sua composição é regra de negócio documentada, não código, e é aqui que as variáveis alternativas de comportamento recebem peso:

| # | Variável informal | Peso | Como é apurada | Por que pesa isso |
|---|---|---:|---|---|
| 1 | **Pontualidade em contas recorrentes** | 30 | Comprovantes de água, luz, aluguel e declaração de fiado no comércio local (12 meses) | Maior peso individual: é **evidência direta e verificável** de adimplência. Não é proxy de nada: é o próprio comportamento que se quer prever |
| 2 | **Tempo de atuação no negócio e na comunidade** | 20 | Declaração de associação de moradores ou de dois comerciantes vizinhos | Proxy de resiliência. Um negócio que sobreviveu 10 anos na periferia já atravessou choques que quebraram concorrentes |
| 3 | **Regularidade do fluxo de caixa** | 20 | Caderno de vendas, extrato de maquininha ou registro de Pix (3 meses) | Mede **capacidade** real de pagamento, o papel que a renda CLT cumpriria, medido na fonte certa para quem é informal |
| 4 | **Referências comunitárias** | 15 | Duas referências de fornecedores, clientes fixos ou lideranças locais | Capital social. Em microcrédito comunitário, a reputação no bairro funciona como **garantia reputacional** e substitui a garantia real que este público não tem |
| 5 | **Histórico com a própria cooperativa** | 15 | Contratos anteriores quitados na instituição | O melhor preditor existente, quando existe. Peso contido de propósito (ver nota abaixo) |
| | **Total** | **100** | | |

**Por que a pontualidade (30) pesa mais que tudo:** o objetivo do redesenho é substituir um critério de *formalidade* por um critério de *comportamento*. A variável 1 é a mais próxima do evento que se quer prever: pagar em dia. As variáveis 2 e 3 medem sustentação do negócio; a 4 mede pressão social; a 1 mede o histórico do próprio ato de pagar.

> ⚠️ **Verificação de exclusão embutida: cliente novo.** Quem nunca tomou crédito na cooperativa zera a variável 5 e alcança no máximo **85 pontos** (30+20+20+15). Como 85 > 60, **o cliente de primeira viagem continua aprovável** por mérito das variáveis 1 a 4. Isso foi calibrado deliberadamente: um peso maior na variável 5 recriaria uma exclusão nova, a do recém-chegado, reproduzindo o defeito que este projeto veio corrigir, só que em outra porta. Nenhuma variável isolada pode ter poder de veto.

**Variáveis vedadas na composição.** Não podem entrar no score, sob nenhuma justificativa técnica: bairro ou logradouro de residência, sobrenome, origem racial, religião ou frequência a templo, filiação sindical ou partidária, estado civil, número de filhos, dado de saúde ou deficiência. São *proxies de característica protegida*: reintroduziriam discriminação indireta sob aparência de neutralidade estatística, exatamente como a exigência de CLT fazia. Ver seção 4.2 e 4.5.

### Cenários

| Perfil | Score Social | Renda CLT | Bônus | Final | Resultado |
|---|---:|---:|---:|---:|---|
| Costureira, 12 anos no bairro, contas em dia | 100 | R$ 0 | 0,00 | 100,00 | **Aprovado** |
| Feirante com bom histórico | 80 | R$ 0 | 0,00 | 80,00 | **Aprovado** |
| Mecânico informal, histórico regular | 60 | R$ 0 | 0,00 | 60,00 | **Aprovado** |
| Histórico mediano + meio salário CLT | 50 | R$ 750 | 10,00 | 60,00 | **Aprovado** |
| Histórico mediano + CLT integral | 50 | R$ 3.000 | 20,00 | 70,00 | **Aprovado** |
| Histórico mediano, sem renda formal | 50 | R$ 0 | 0,00 | 50,00 | Reprovado |
| Histórico fraco | 40 | R$ 0 | 0,00 | 40,00 | Reprovado |
| **Histórico ruim + renda muito alta** | 30 | R$ 100.000 | 20,00 | 50,00 | **Reprovado** |

A última linha é a prova de que o modelo não virou uma porta escancarada: renda alta **não compra** aprovação. A terceira linha é a prova de que o problema original foi resolvido: renda zero **não impede** aprovação.

---

## 4. Compliance e Proteção de Dados (LGPD, Lei nº 13.709/2018)

O público atendido é composto por pessoas em situação de vulnerabilidade socioeconômica, para quem um vazamento de dados financeiros tem consequências desproporcionais, desde constrangimento comunitário até exposição a agiotagem e golpes dirigidos. A proteção de dados aqui é requisito de produto, não formalidade jurídica.

### 4.1 Minimização (art. 6º, III)

O sistema coleta **duas variáveis numéricas e nada mais**: o Score Social Alternativo e a Renda Formal. Não pede nome, CPF, RG, endereço, telefone, estado civil, nome de familiares nem foto.

Consequência direta: **os dados processados na triagem são, isoladamente, anônimos.** Um dump completo da entrada do sistema seria um par de números sem titular identificável. É a defesa mais forte possível: o dado que não existe não vaza.

### 4.2 Ausência de dados sensíveis (art. 5º, II)

Nenhuma variável de origem racial, convicção religiosa, opinião política, filiação sindical, dado de saúde, vida sexual, genético ou biométrico entra no cálculo.

Esse ponto exige vigilância permanente na composição do Score Social a montante. Variáveis de comportamento comunitário podem funcionar como **proxies discriminatórios**: frequência a determinado templo, bairro de residência, sobrenome, participação em associação. A cooperativa deve manter e publicar a lista de variáveis admitidas no score, com veto explícito a proxies de característica protegida.

### 4.3 Base legal (art. 7º, V)

O tratamento se dá para **execução de procedimentos preliminares a contrato, a pedido do titular**, a própria solicitação de crédito. Não se apoia em consentimento genérico, o que evita a coleta oportunista de dados alheios à finalidade.

### 4.4 Decisão automatizada e direito à revisão (art. 20)

O art. 20 garante ao titular o direito de solicitar revisão de decisões tomadas exclusivamente por tratamento automatizado que afetem seus interesses. O sistema implementa isso de duas formas:

- **Explicabilidade por construção.** O programa imprime a *memória de cálculo*: score de origem, bônus aplicado, pontuação final e limiar. O cliente vê exatamente por que foi aprovado ou negado, em números. Não existe caixa-preta.
- **Encaminhamento ativo.** Toda reprovação exibe a informação do direito à revisão humana. O modelo é uma ferramenta de *triagem*, não a palavra final: casos limítrofes e contestações vão ao analista de crédito.

O algoritmo é determinístico e legível em uma linha de aritmética. Isso é uma escolha deliberada de governança: um modelo estatístico opaco (rede neural, gradient boosting) poderia ganhar acurácia marginal ao custo de tornar o art. 20 impossível de cumprir de boa-fé.

### 4.5 Não discriminação (art. 6º, IX)

A LGPD veda o tratamento de dados para fins discriminatórios ilícitos ou abusivos. O sistema legado, ao usar formalidade de vínculo como veto, produzia **discriminação indireta de gênero e classe**: critério neutro no texto, efeito desproporcional sobre mulheres chefes de família. Eliminar esse veto é o cumprimento material do inciso, e o motivo de existir deste projeto.

**Monitoramento contínuo:** a cooperativa deve auditar trimestralmente as taxas de aprovação segmentadas por gênero e faixa de renda, sobre dados agregados e anonimizados, para detectar disparate impact residual antes que ele se consolide.

### 4.6 Segurança, retenção e ciclo de vida (arts. 46 e 16)

| Controle | Aplicação |
|---|---|
| Persistência | O script de triagem **não grava dados em disco**, processa em memória e encerra |
| Segregação | Dados cadastrais ficam no sistema da cooperativa; a triagem recebe apenas o par de números |
| Controle de acesso | Perfis por função, com credencial individual; sem contas compartilhadas em posto de atendimento |
| Trilha de auditoria | Registro de acessos e alterações de parâmetro versionado no Git |
| Criptografia | Em trânsito (TLS) e em repouso, na base cadastral a montante |
| Retenção | Prazo definido por obrigação regulatória do contrato de crédito; eliminação ao término (art. 16) |
| Relatórios | Somente dados agregados e anonimizados, nunca registros individuais |

### 4.7 Papéis e responsabilidades

- **Controlador:** a cooperativa de microcrédito, que decide finalidade e meios do tratamento.
- **Operadores:** agentes de crédito comunitários e prestadores de tecnologia.
- **Encarregado (DPO):** designado formalmente, com canal de contato publicado no posto de atendimento **e em linguagem acessível**: cartaz físico e atendimento presencial, não apenas e-mail em rodapé de site. A titular precisa conseguir exercer seus direitos (arts. 18 e 19) no balcão onde pediu o crédito.

---

## 5. Análise de Viabilidade Financeira

> ⚠️ **Premissas ilustrativas.** Os números abaixo demonstram o *método* de estimativa. Devem ser substituídos pelos dados históricos reais da cooperativa antes de qualquer decisão de investimento.

### Premissas

| Variável | Valor |
|---|---:|
| Solicitações de crédito por mês | 500 |
| Taxa de rejeição sob o sistema legado | 68% (340 negados/mês) |
| Dos negados, proporção com Score Social ≥ 60 | 45% |
| **Novos contratos habilitados pelo novo modelo** | **153/mês** |
| Ticket médio | R$ 1.200,00 |
| Prazo | 12 meses (Tabela Price) |
| Taxa de juros | 2,5% a.m. |
| Inadimplência esperada (informais com score ≥ 60) | 8% |
| Custo operacional por contrato | R$ 60,00 |

Sobre a inadimplência estimada: a premissa de 8% é **conservadora e proposital**. Ela assume que o público informal aprovado terá desempenho *pior* que a carteira atual, mesmo sendo composto por pessoas selecionadas justamente por histórico comprovado de pagamento. Se o Score Social tiver poder preditivo real (e a hipótese central deste projeto é que tem), o número tende a ficar abaixo disso.

### Cálculo

Juros totais por contrato (Price, 2,5% a.m. × 12 meses) = **16,98% do principal** ≈ R$ 203,81

| Componente | Mensal | Anual |
|---|---:|---:|
| Volume adicional desembolsado | R$ 183.600 | R$ 2.203.200 |
| (+) Receita de juros | R$ 31.183,64 | R$ 374.203,68 |
| (−) Perda esperada por inadimplência (8%) | −R$ 14.688 | −R$ 176.256 |
| (−) Custo operacional (153 × R$ 60) | −R$ 9.180 | −R$ 110.160 |
| **= Resultado líquido incremental** | **R$ 7.315,64** | **R$ 87.787,66** |

### Ponto de equilíbrio

```
Inadimplência máxima suportada = (Receita de juros − Custo operacional) / Volume desembolsado
                               = (31.183,64 − 9.180,00) / 183.600,00
                               = 11,98%
```

**A operação suporta até 11,98% de inadimplência antes de gerar prejuízo.** Contra a estimativa conservadora de 8%, isso deixa **4 pontos percentuais de margem de segurança**, folga de 50% sobre o cenário-base. A expansão é economicamente sustentável mesmo se o desempenho do público informal frustrar a expectativa.

### Ganhos não capturados no cálculo direto

**Custo de aquisição já afundado.** Esses 153 clientes/mês **já chegaram** ao balcão da cooperativa e já foram analisados. Todo o custo de aquisição e triagem foi pago, e depois jogado fora pela regra de veto. Convertê-los tem CAC marginal próximo de zero, o que torna esta a expansão mais barata disponível à cooperativa.

**Valor de ciclo de vida (LTV).** O microcrédito é um produto de recorrência: o cliente que quita o primeiro contrato normalmente renova com ticket maior. A análise acima captura apenas o **primeiro ciclo de 12 meses**. O valor presente de uma cliente que renova por cinco anos com ticket crescente é múltiplo do número apresentado.

**Risco reputacional e regulatório evitado.** Manter um critério que rejeita 95% das mulheres chefes de família expõe a cooperativa a questionamento por discriminação indireta, sob a LGPD (art. 6º, IX) e sob a legislação de defesa do consumidor. O custo de um passivo desses não aparece na DRE até o dia em que aparece de uma vez.

**Cumprimento de missão institucional.** Uma cooperativa de microcrédito comunitário existe para financiar quem o sistema bancário tradicional não alcança. O critério antigo replicava exatamente a exclusão que a instituição foi criada para combater, e um índice de rejeição de 68% é evidência direta desse desalinhamento.

### Conclusão

A reforma do algoritmo injeta **R$ 2,2 milhões/ano em crédito produtivo** na economia periférica, gera **~R$ 87,8 mil/ano de resultado líquido incremental** no cenário conservador, e opera com 4 p.p. de margem antes do ponto de equilíbrio. Não há trade-off entre justiça e sustentabilidade financeira: **a exclusão dos informais honestos era, ela própria, o desperdício.**

---

## 6. Como Executar

Requisito: Python 3.

```bash
python3 src/triagem.py
```

Exemplo de sessão:

```
--- SISTEMA DE MICROCRÉDITO INCLUSIVO UniFAP ---
Digite o Score Social Alternativo (0-100): 80
Digite a Renda Formal CLT (R$): 0

----------- MEMORIA DE CALCULO -----------
Score Social Alternativo ..:  80.00 pontos
Bonus por Renda Formal ....:   0.00 pontos (teto: 20)
Pontuacao Final ...........:  80.00 pontos
Limiar de Aprovacao .......:  60.00 pontos
------------------------------------------

Resultado: Aprovado
```

---

## 7. Validação Automatizada

O pipeline em `.github/workflows/testes.yml` roda a cada `git push`:

| Caso | Entrada | Esperado | Status |
|---|---|---|---|
| 1. Informal com bom score | score 80, renda R$ 0 | `Resultado: Aprovado` | ✅ |
| 2. Baixo score sem renda | score 40, renda R$ 0 | `Resultado: Reprovado` | ✅ |

---

## 8. Estrutura

```
.
├── README.md                      Fluxo de negócio, pesos, LGPD e viabilidade
├── .gitignore
├── src/
│   └── triagem.py                 Motor de triagem
└── .github/workflows/testes.yml   Validação automatizada
```
