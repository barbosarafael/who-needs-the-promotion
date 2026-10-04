# Protocolo de avaliação causal (T5)

**Status: especificação protocolar; não autoriza execução causal nem valida features.**
Este protocolo usa o contrato T1 e os estimandos T2/T3. H1 (cutoff temporal,
features aprovadas, população/modelagem e adequação da identificação) permanece
pendente; H2 deverá aprovar catálogo de features, splits e métricas antes dos
experimentos. Nenhum cutoff é proposto aqui. Até H1, toda regra dependente de
covariáveis aplica-se somente condicionalmente a um conjunto `X` futuro,
aprovado em H1; timing desconhecido exclui a feature da análise primária.

## Pergunta, estimandos e hipótese

Pergunta: ranking e políticas baseados em efeito incremental melhoram resultados
contra baselines, sob identificação válida? Estimandos candidatos são ATE/ATT,
CATE `tau(x)=E[Y(1)-Y(0)|X=x]`, uplift/ranking e valor de política
`V(pi)=E[Y(pi(X))]`; escolha da população/estimando fica sujeita a H1. Hipótese
avaliável: políticas aprendidas têm valor incremental maior que baselines numa
amostra honesta. Não se observa efeito individual real; métricas preditivas
padrão não são métrica causal primária.

## Gates e dados

- T3 descreve dados, grão, taxas, missingness e timing; seu contrato não resolve
  o cutoff. H1 deve aprovar cutoff, outcome window, unidade/população, features
  e plausibilidade de análise observacional. Se não aprovado, sem inferência
  causal real; no máximo especificação de protocolo.
- Feature dependente é válida **somente se** demonstravelmente disponível antes
  da atribuição e aprovada em H1; tratamento, outcome e variáveis pós-tratamento
  nunca integram `X`. Uma regra técnica não estabelece disponibilidade temporal.
- Registrar revisão/hash dos dados, unidade, estimando, população, features
  aprovadas, transformação, algoritmo/hiperparâmetros, seed, folds, métricas,
  intervalos, limitações e decisão. Nenhum threshold de sucesso será inventado.

## Diagnósticos de desenho

Antes e, quando aplicável, após ajuste/ponderação, reportar por covariável
aprovada: diferença média padronizada (SMD), com denominador pooled SD
pré-ajuste; para binárias usar a mesma fórmula com variância Bernoulli pooled.
Exibir tabela/plot e proporção/maximo de `|SMD|`; `0.1` pode ser referência
heurística, nunca prova de ausência de confusão. Propensity `e(X)=P(A=1|X)`:
plotte distribuições separadas por A, suporte comum, caudas/extremos e
proporção fora do suporte. Reportar pesos, quantis, extremos e ESS por braço,
`ESS=(sum w)^2/sum(w^2)`. Especificação do propensity, trimming/clipping e
população-alvo devem ser pré-especificados; reportar sensibilidade, nunca
escolher limiar pelo melhor resultado. Balance/overlap não provam
exchangeability. Sem features aprovadas, estes diagnósticos são plano, não
executáveis.

## Splits, ajuste e cross-fitting

1. Manter IDs de cliente disjuntos entre treino, validação e teste. Uma única
   linha por cliente/oportunidade conforme contrato; havendo campanhas repetidas,
   agrupar cliente e resolver unidade antes do split. Duplicatas/entidades
   relacionadas não podem cruzar folds.
2. Split aleatório estratificado por tratamento só é elegível se T3/H1 confirmar
   população sem estrutura temporal incompatível. Se existir ordenação temporal
   pertinente, usar holdout futuro definido após H1; não inventar datas agora.
   Todo pré-processamento, seleção de variáveis e ajuste é aprendido no treino.
3. Validação serve para seleção limitada; teste fica intocado até protocolo e
   modelo congelados. Evitar testar repetidamente e escolher vencedor no teste.
   Reportar seeds e tamanhos/taxas por braço.
4. Para estimadores com nuisance functions, usar K-fold cross-fitting: ajustar
   nuisance no complemento do fold, predizer no fold excluído; folds agrupados
   por cliente e, se aplicável, respeitando tempo. Feature selection/imputação/
   encoding dentro do treino de cada fold. Se amostra permitir, folds externos
   avaliam seleção e folds internos ajustam hiperparâmetros. Documentar K e
   fallback quando estratos insuficientes; não cruzar informação entre folds.
5. O teste honesto deve conter tratamento e controle, overlap suficiente e
   representação do alvo. Não re-treinar métricas no mesmo conjunto usado para
   seleção. Modelo/score de política é produzido sem outcome de avaliação.

## Métricas por contexto

### Observacional (X5)

- ATE/ATT: diferença bruta apenas como referência; estimativas ajustadas
  (regressão/g-formula, IPW, AIPW quando futuramente autorizadas), com estimando,
  hipóteses, suporte, ESS e IC. Não confundir precisão estatística com validade
  causal.
- CATE: nenhuma métrica contra ITE observado. Calibração/ranking apenas via
  pseudo-outcomes/cross-fitting e sob identificação, com incerteza e caveat;
  não reivindicar verdade individual.
- Qini/AUUC/uplift@K e policy value são secundários e condicionais a
  exchangeability, consistência, positivity, ausência de interferência e
  avaliação honesta. Explicitar estimador/normalização, população e orçamento;
  curvas não são estimativas automaticamente válidas em dados observacionais.
- Diagnósticos SMD/overlap/ESS, sensibilidade e estabilidade complementam, não
  substituem identificação. AUC/accuracy/RMSE de outcome são apenas diagnóstico
  de nuisance, nunca critério primário causal ou seleção final.

### Semi-sintético

Em gerador com atribuição e potenciais outcomes conhecidos, pode-se calcular
erro ATE (estimado menos verdadeiro), erro CATE (MAE/RMSE contra tau conhecida),
calibração por grupos, ranking e valor de política contra valor-oráculo. A
verdade vale somente para DGP gerado, não para clientes X5. Registrar seed,
funções, prevalências e mecanismos; variar confusão/overlap como cenários, sem
interpretar benchmark como prova de identificação observacional.

## Políticas baseline

Comparar no mesmo alvo e cobertura/budget: (1) treat-none; (2) treat-all; (3)
random uniforme, e random sem reposição sob cada orçamento com expectativa/IC;
(4) ranking de propensão de compra, explicitamente não causal; (5) efeito
constante: ordenar em empate e escolher aleatoriamente sob budget, ou tratar
ninguém/todos conforme sinal e regra congelada; especificar formalmente quando
ATE não estimado, não usar estimativa de teste; (6) política candidata de score
CATE apenas após aprovação de H1/H2/H4. Política cost-aware pertence a T12 e
fica fora deste trabalho. Tratar-all/none definem referências de coverage e
valor; não implicam recomendação operacional.

## Incerteza, estabilidade e reporte

Preferir bootstrap por unidade independente (cliente; cluster se interferência/
agrupamento validado), reamostrando o pipeline de avaliação/policy score segundo
estimand. Para política fixa, reportar IC percentile/BCa e número de réplicas e
seed; para pipeline aprendido, refazer ajuste/cross-fitting a cada réplica ou
identificar explicitamente IC condicional que não inclui incerteza de treino.
Em dados com desenho temporal/cluster, bootstrap deve preservar esse desenho.
Reportar IC 95% sem interpretar cobertura como correção de confounding.

Em subgrupos pré-especificados e com suporte, reportar N, tratados/controles,
ESS, efeito/policy metric e IC; limitar conclusões para células esparsas. Medir
variação de ranking/seleção/valor entre folds e bootstrap, cobertura em vários
budgets definidos antes dos resultados; não selecionar subgrupo ou budget pelo
p-valor. Controlar multiplicidade ou rotular análises exploratórias. Ausência de
bootstrap viável deve ser reportada, não substituída por certeza pontual.

## Registro de decisão

Preencher para cada experimento: ID, hipótese, revisão do dataset, unidade,
estimando/população, features aprovadas (ou “nenhuma até H1”), split/folds, método,
seed, métricas e IC, baselines, diagnósticos, resultados, interpretação,
pressupostos, limitações e próxima decisão. Resultados não disponíveis nesta
etapa: nenhum experimento executado. H2 precisa ratificar escolhas finais antes
de T7/T8; T5 não inicia T4, T6, T7, T8 ou tarefas posteriores.
