# 09 — Incident Playbook

## Scénario type
> Un PM dit : "La TE affichée pour AlphaEU est 6.8 %. Impossible, je suis à 4 % chez Bloomberg."

## Méthode (5 étapes)

### 1. Tracer, pas défendre
Récupérer le `calculation_run_id` du chiffre contesté. Lire :
- `calculation_version`
- benchmark utilisé
- `observation_count`
- `data_quality_status`
- timestamp du run

### 2. Hypothèses par probabilité
1. **Wrong benchmark mapping** — PM compare à un autre index
2. **Devise** — fonds EUR, benchmark loaded en USD
3. **Stale NAV** un mois → vol artificiellement haute
4. **Outlier non flaggé**
5. **Différence méthodologique** vs Bloomberg

### 3. Requêtes SQL d'investigation
```sql
-- Quel benchmark était mappé au moment du calcul ?
SELECT b.code, m.valid_from, m.valid_to, m.is_active
FROM fund_benchmark_mapping m
JOIN benchmark b ON b.id = m.benchmark_id
WHERE m.fund_id = 42
  AND m.valid_from <= '2026-04-30'
  AND (m.valid_to IS NULL OR m.valid_to > '2026-04-30');

-- Returns cohérents ?
SELECT date, monthly_return, source FROM fund_return
WHERE fund_id = 42 AND date >= '2025-05-01' ORDER BY date;
```

### 4. Diagnostic + fix
- Identifier root cause (ex: mapping changé sans validation)
- Restaurer état correct
- **Ne pas** delete l'ancien run (audit)
- Re-trigger un nouveau `CalculationRun` avec la même version
- Ouvrir un `DataQualityIssue` pour traçabilité

### 5. Communication 3 niveaux

**Au PM :**
*"Tu as raison, le chiffre est faux. Cause : le mapping fonds-benchmark a été modifié le 15/03, AlphaEU pointait vers MSCI Europe au lieu de STOXX 600. La TE 6.8 % était correctement calculée mais sur le mauvais index. J'ai restauré, relancé. La TE actualisée est 4.05 %, cohérente avec ton chiffre Bloomberg. L'ancien run reste en base pour traçabilité."*

**À l'IT lead :**
*"Root cause : changement de mapping benchmark sans contrôle d'intégrité. Calcul nominal donc pas d'alerte. Action : audit log sur `FundBenchmarkMapping` + test data-quality flagant tout changement comme issue MEDIUM en attendant validation."*

**Au quant senior :**
*"Erreur de référentiel, pas de bug numérique. Méthodologie te.v1.0 inchangée. Je propose d'ajouter un cross-check : variation > 50 % vs les 3 derniers calculs = flag DEGRADED automatique."*

## Réponse orale parfaite
*"Trois choses dans cet ordre. Un, je ne défends pas le chiffre, je l'investigue : je remonte le calculation_run, je lis les logs, je vérifie benchmark et version. Deux, je liste les hypothèses par probabilité — mapping, devise, stale NAV, méthodologie — et je teste chacune avec une requête. Trois, je communique : si bug côté nous, je l'admets, je corrige, je documente le RCA. Si différence méthodologique légitime, j'explique précisément la convention — ddof=1, sqrt(12), fenêtre 12M stricte — et je propose un point méthodologique pour aligner si besoin. Le pire qu'on puisse faire c'est défendre un chiffre sans l'avoir tracé."*

## Ce que je dois être capable d'expliquer en entretien
- Méthode d'investigation en 3 étapes
- Pourquoi ne jamais delete un run ancien
- Comment communiquer différemment selon l'audience
- Quand ouvrir un `DataQualityIssue`
