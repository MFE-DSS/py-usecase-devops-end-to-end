# 13 — ORM, SQL, Performance Django

Cette note couvre la question d'entretien : *"Comment éviter des problèmes de performance avec l'ORM Django ?"*

## 1. Mental model du QuerySet

Un `QuerySet` Django est **lazy** : il ne touche pas la DB tant qu'il n'est pas évalué. Évaluation déclenchée par :
- itération (`for fund in qs:`)
- slicing avec step (`qs[::2]`)
- `len(qs)`
- conversion (`list(qs)`, `bool(qs)`)
- accès à un élément (`qs[0]`)
- sérialisation, JSON encoding

Avant ces déclencheurs, tu peux **chaîner** sans coût : `Fund.objects.filter(active=True).exclude(currency="JPY").order_by("isin")`.

**Conséquence** : on construit le QuerySet le plus précis possible, on l'évalue **une fois**.

```python
# Mauvais
funds = Fund.objects.all()
active = [f for f in funds if f.active]   # évalue tout, filtre en Python

# Bon
active = list(Fund.objects.filter(active=True))   # filtre en SQL
```

## 2. N+1 queries — le bug le plus fréquent

### Le pattern
```python
# 1 query pour les metrics
metrics = RiskMetric.objects.all()
for m in metrics:
    print(m.fund.name)        # +1 query par metric → N+1
    print(m.benchmark.code)   # +1 query par metric → 2N+1
```
Pour 100 metrics avec 2 FK → **201 queries**.

### Détection
```python
from django.db import connection, reset_queries
from django.conf import settings
settings.DEBUG = True
reset_queries()
list(RiskMetric.objects.all())
print(len(connection.queries))  # nombre de queries SQL réellement émises
```

En tests :
```python
from django.test.utils import CaptureQueriesContext
from django.db import connection

with CaptureQueriesContext(connection) as ctx:
    serializer = RiskMetricSerializer(qs, many=True).data
assert len(ctx.captured_queries) <= 3  # garde-fou anti-N+1
```

### Remède 1 : `select_related` (FK / OneToOne)
JOIN SQL en une seule query :
```python
RiskMetric.objects.select_related("fund", "benchmark", "calculation_run")
```
SQL généré :
```sql
SELECT rm.*, f.*, b.*, cr.*
FROM risk_metric rm
JOIN fund f ON f.id = rm.fund_id
JOIN benchmark b ON b.id = rm.benchmark_id
JOIN calculation_run cr ON cr.id = rm.calculation_run_id;
```
**1 query au lieu de 4N**.

### Remède 2 : `prefetch_related` (ManyToMany / reverse FK)
2 queries + jointure côté Python (Django) :
```python
Fund.objects.prefetch_related("returns")
# query 1: SELECT * FROM fund;
# query 2: SELECT * FROM fund_return WHERE fund_id IN (...);
```
On ne peut **pas** utiliser `select_related` ici (cardinalité 1-N côté reverse).

### Combinaison
```python
RiskMetric.objects.select_related("fund", "benchmark").prefetch_related("calculation_run__metrics")
```

### Remède 3 : `Prefetch` avec QuerySet personnalisé
```python
from django.db.models import Prefetch

recent_returns = FundReturn.objects.filter(date__gte="2025-01-01").order_by("-date")
funds = Fund.objects.prefetch_related(
    Prefetch("returns", queryset=recent_returns, to_attr="recent_returns")
)
for f in funds:
    f.recent_returns   # déjà filtré et trié, 0 query supplémentaire
```

## 3. `only` / `defer` / `values` / `values_list`

Quand on n'a besoin que de quelques champs :

```python
# only: load only these columns, lazy-load le reste si tu y touches
Fund.objects.only("id", "isin")

# defer: opposite — charge tout sauf ces colonnes (utile si BLOB lourd)
Fund.objects.defer("notes")

# values: dict, no model instance — plus rapide
Fund.objects.values("id", "isin", "currency")

# values_list: tuple, encore plus rapide
list(Fund.objects.values_list("id", flat=True))
```

**Quand utiliser** : exports, stats, payloads minces. **Pas** quand tu as besoin des méthodes du modèle.

## 4. Aggregation côté DB

Faire en SQL ce qui peut l'être :

```python
from django.db.models import Count, Avg, Q

# Mauvais : ramener 100k metrics et compter en Python
total = len(RiskMetric.objects.filter(data_quality_status="OK"))

# Bon : COUNT(*) en SQL
total = RiskMetric.objects.filter(data_quality_status="OK").count()

# Group by
RiskMetric.objects.values("data_quality_status").annotate(
    n=Count("id"),
    avg_value=Avg("metric_value"),
)
```

## 5. Indexes — quand et où

| Cas | Index recommandé |
|---|---|
| Recherche fréquente par `(fund, date)` sur returns | `Index(fields=["fund", "date"])` |
| Lookup `(fund, metric_name, as_of_date)` | composite index |
| `filter(active=True)` très sélectif | `Index(fields=["active"])` ou partial index |
| FK | déjà indexé automatiquement par Django |
| Texte recherché par `LIKE 'foo%'` | index B-tree sur le préfixe |
| Recherche full-text PostgreSQL | `GinIndex` |

**Anti-pattern** : indexer tout. Chaque index ralentit `INSERT/UPDATE` et coûte en disque.

```python
class Meta:
    indexes = [
        models.Index(fields=["fund", "date"]),
        models.Index(fields=["fund", "metric_name", "as_of_date"]),
    ]
```

## 6. Transactions

```python
from django.db import transaction

@transaction.atomic
def run_calculation(...):
    run = CalculationRun.objects.create(...)
    metric = RiskMetric.objects.create(...)
    # rollback automatique si exception
```

**Usage typique** : service layer. Le `@transaction.atomic` sur la méthode principale du service garantit que **soit tout est créé, soit rien**. Critique quand tu écris dans plusieurs tables corrélées.

**Piège** : `atomic` sur un signal `post_save` peut deadlocker. Garder les transactions courtes.

## 7. `bulk_create` / `bulk_update`

```python
# Mauvais : N queries pour insérer N returns
for row in rows:
    FundReturn.objects.create(fund=fund, date=row.date, monthly_return=row.value)

# Bon : 1 query
FundReturn.objects.bulk_create(
    [FundReturn(fund=fund, date=r.date, monthly_return=r.value) for r in rows],
    batch_size=1000,
    ignore_conflicts=False,  # ou True selon politique
)
```
Caveats : `bulk_create` ne déclenche **pas** les signaux `pre_save`/`post_save`, ne renvoie pas les `id` sur SQLite, et ne gère pas les FK auto-générées si parents non sauvegardés.

## 8. Quand utiliser du SQL brut

Critères honnêtes :
- requête analytique complexe (window functions, CTEs récursives, pivots) ;
- perf critique sur du gros volume où l'ORM génère une query naïve ;
- features Postgres avancées non exposées par l'ORM (LATERAL joins, full-text) ;
- migration de données ponctuelle.

**Pas** pour : économiser 5 ms sur une lecture standard.

```python
from django.db import connection

with connection.cursor() as cur:
    cur.execute("""
        SELECT fund_id, AVG(metric_value)
        FROM risk_metric
        WHERE metric_name = %s AND as_of_date >= %s
        GROUP BY fund_id
    """, ["tracking_error_12m", "2025-01-01"])
    rows = cur.fetchall()
```

Ou via `Manager.raw()` pour rester model-aware :
```python
RiskMetric.objects.raw("SELECT * FROM risk_metric WHERE ...")
```

## 9. Connection pooling et `conn_max_age`

`settings.py` :
```python
DATABASES = {
    "default": dj_database_url.config(default=..., conn_max_age=600)
}
```
- `conn_max_age=0` (default) : connexion fermée à chaque requête → latence overhead.
- `conn_max_age=600` : connexion réutilisée 10 min → meilleur throughput.
- En prod gros volume : utiliser **PgBouncer** en front pour un pool partagé.

## 10. Pagination — pas seulement pour l'API

Lire 100k lignes en une fois fait exploser la RAM. Itérer par chunks :

```python
qs = FundReturn.objects.all().order_by("id")
for ret in qs.iterator(chunk_size=2000):
    process(ret)
```
`iterator()` ne cache pas les résultats côté client → mémoire stable.

## 11. Anti-patterns à reconnaître

| Anti-pattern | Symptôme | Fix |
|---|---|---|
| N+1 sur un Serializer DRF | `RiskMetricSerializer` qui sérialise `fund.name` sans `select_related` | `get_queryset` du ViewSet avec `select_related` |
| `len(qs)` au lieu de `qs.count()` | matérialisation inutile | `.count()` |
| Boucle `for x: x.save()` | N queries | `bulk_update` |
| `.all()` puis filtre Python | charge toute la table | filtre SQL |
| Index sur tout | `INSERT` lents | indexer ce qui apparaît dans `WHERE`/`ORDER BY`/`JOIN` |
| Pas de `select_related` sur FK chaud | latence dashboard | `select_related` systématique sur l'admin et les viewsets |

## 12. Outils de diagnostic

- **Django Debug Toolbar** (dev only) : panel SQL avec stack trace, easy à lire.
- **`django-silk`** : profiling production-grade.
- **`EXPLAIN ANALYZE`** côté Postgres pour les requêtes critiques.
- **`pytest --django-debug-mode`** + `CaptureQueriesContext` pour bornes de tests.
- **logs SQL** : `LOGGING` avec `'django.db.backends': {'level': 'DEBUG'}` (verbeux, dev only).

## Réponses orales prêtes

### "Comment éviter le N+1 ?"
*"Première règle, je sais reconnaître le pattern : une query qui boucle et accède à une FK sur chaque itération. Pour fixer : `select_related` sur les FK et OneToOne — ça produit un JOIN unique. `prefetch_related` sur les reverse FK et ManyToMany — ça fait deux queries avec assemblage Python. En tests, je pose un garde-fou avec `CaptureQueriesContext` qui asserte que mon viewset reste sous N queries quel que soit le volume retourné. C'est ce qui empêche les régressions."*

### "Quand passes-tu en SQL brut ?"
*"Trois cas : analytics complexes — window functions, CTEs récursives — où l'ORM génère du code lourd ; perf critique sur du gros volume où j'ai mesuré que l'ORM était le bottleneck ; features Postgres natives non exposées comme les LATERAL joins. En dehors de ça je reste sur l'ORM, c'est plus testable et plus maintenable. Je ne tombe pas dans le SQL pour le sport."*

### "Indexes — comment tu choisis ?"
*"Je regarde mon `WHERE`, mon `ORDER BY`, et mes JOINs réels — pas hypothétiques. Sur ce projet : `(fund, date)` sur returns parce que je fais des fenêtres glissantes dessus, `(fund, metric_name, as_of_date)` sur risk_metric parce que c'est mon lookup principal. Je n'index pas `created_at` juste pour le sport, ça ralentit les writes. Et je profite que Django auto-index les FK."*

## Ce que je dois être capable d'expliquer en entretien
- N+1 : reconnaître, mesurer, fixer
- `select_related` vs `prefetch_related` : différence et quand utiliser
- `count()` vs `len()`, `values()` vs `only()`, `bulk_create`
- Indexes : quand, où, pourquoi pas partout
- Transactions : `atomic` au niveau service
- SQL brut : 3 cas légitimes
- Outils de diagnostic : Debug Toolbar, `CaptureQueriesContext`, `EXPLAIN`
