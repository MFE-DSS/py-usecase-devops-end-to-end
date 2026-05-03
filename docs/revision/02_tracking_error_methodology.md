# 02 — Tracking Error Methodology

## Définition
Écart-type des excess returns (returns du fonds moins benchmark) sur une fenêtre temporelle, annualisé.

## Formule
```
excess_t   = R_fund_t - R_bench_t
TE_monthly = std(excess_t, ddof=1)
TE_annual  = TE_monthly * sqrt(12)
```

Convention industry : `ddof=1` (estimateur non biaisé).

## Différences avec autres métriques
| Métrique | Formule | Interprétation |
|---|---|---|
| TE | std(R_f - R_b) × √12 | Risque relatif au benchmark |
| Volatility | std(R_f) × √12 | Risque absolu |
| Max Drawdown | min cumulé | Pire perte path-dependent |
| Information Ratio | mean(excess)/std(excess) × √12 | TE risk-adjusted (alpha par unité de TE) |

## Utilité
- **Fund Selector** : valider mandat (un fonds "core" avec TE 8 % a dérivé)
- **PM** : risk budgeting, contraindre l'active risk
- **Risk Officer** : flag de dérive de style

## Pièges de production
| Piège | Conséquence |
|---|---|
| Dates non alignées | TE artificiellement haute |
| NaN au milieu | Fenêtre raccourcie ou biaisée |
| Benchmark mal mappé | TE numériquement correcte, fausse business |
| Devises différentes | Volatilité de change pollue la TE |
| Total return vs price return | Décalage systématique |
| Stale NAV | Volatilité sous-estimée |
| `ddof=0` vs `ddof=1` | Quelques bps de différence |

## Cas particuliers à gérer
- **< 9 obs** → `INSUFFICIENT_DATA`, value `None`
- **9-11 obs** → `DEGRADED`, valeur calculée mais signalée
- **≥ 12 obs** → `OK`
- **Std nulle** (replication parfaite) → 0.0, `OK`
- **Outlier > 5σ** → flag `DataQualityIssue`, calcul standard

## Pitch 60s
*"Tracking Error 12-mois, c'est l'écart-type annualisé des excess returns mensuels d'un fonds par rapport à son benchmark sur les douze derniers mois. On récupère les returns mensuels du fonds et de son benchmark de référence à cette date, on les aligne strictement par fin de mois, on calcule R_fund moins R_bench, on prend l'écart-type ddof=1, et on multiplie par racine de 12. En production l'enjeu n'est pas la formule, c'est tout ce qu'il y a autour : le mapping fonds-benchmark valide à la date du calcul, le traitement des données manquantes — typiquement on exige 12 observations sinon INSUFFICIENT_DATA — et le versioning méthodologique pour que le chiffre reste reproductible. On stocke le résultat avec un calculation_run, un data_quality_status, et un observation_count, ce qui permet à un PM qui conteste de remonter en deux requêtes au benchmark, à la version, et aux observations effectives."*

## Ce que je dois être capable d'expliquer en entretien
- Formule au tableau, sans hésiter
- Pourquoi `ddof=1`
- Pourquoi `sqrt(12)` (Var iid additive)
- 5 pièges de production différents
- Les 3 statuts qualité et leurs seuils
