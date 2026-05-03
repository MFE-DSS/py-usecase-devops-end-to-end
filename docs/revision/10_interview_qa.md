# 10 — Interview Q&A (sélection 30 questions)

Format : **Q** → ✅ bonne / ❌ mauvaise / 🔁 relance.

## Python / pandas
1. **Aligner deux séries de returns ?** ✅ DatetimeIndex, `concat(axis=1, join="inner").dropna()`. ❌ boucle for. 🔁 NaN au milieu ?
2. **`ddof=0` vs `ddof=1` ?** ✅ ddof=1 estimateur sans biais, convention TE. ❌ "aucune différence".
3. **`numpy.std` ddof par défaut ?** ✅ 0. `pandas.Series.std` ddof=1. Piège classique.
4. **Decimal côté DB, float côté calcul ?** ✅ Decimal audit, float vitesse numpy, conversion à la frontière.

## Quant
5. **TE vs volatility ?** ✅ TE = std excess, vol = std returns absolus.
6. **Pourquoi `sqrt(12)` ?** ✅ Var iid additive, Var(annual) = 12 × Var(monthly).
7. **TE faible mais IR négatif ?** ✅ Suit bien le bench mais sous-performe.
8. **Cas où TE explose artificiellement ?** ✅ benchmark mismatch, devise, stale NAV, fund launch tardif.

## SQL / data model
9. **Pourquoi un `CalculationRun` séparé ?** ✅ traçabilité, rejouabilité, audit.
10. **Index sur quoi ?** ✅ `(fund, date)` returns, `(fund, metric_name, as_of)` metrics.
11. **Restatement ?** ✅ pas d'UPDATE, nouvelle ligne avec source. Idéalement bitemporal.
12. **`on_delete=PROTECT` ?** ✅ intégrité historique.
13. **Dernière TE par fonds ?** ✅ `SELECT DISTINCT ON (fund_id) ... ORDER BY fund_id, as_of DESC`.

## Django REST
14. **ViewSet vs APIView ?** ✅ ViewSet groupe CRUD + Router, APIView = endpoint custom.
15. **`fields = "__all__"` ?** ❌ anti-pattern, fuite champs internes.
16. **OpenAPI ?** ✅ `drf-spectacular`, `/api/schema/`.
17. **GET ou POST pour trigger calcul ?** ✅ POST, side-effect.

## API design
18. **Versioning ?** ✅ URL prefix `/api/v1/`, bump pour breaking only.
19. **Idempotency-Key ?** ✅ header POST, dédup serveur.
20. **Pagination ?** ✅ PageNumber, page_size 50 par défaut.

## Software / SOLID
21. **SRP appliqué ?** ✅ View → Service → Repo → Domain, chacun une raison de changer.
22. **DIP en Django ?** ✅ Service prend repos en constructeur, swap en test.
23. **Fat Model ?** ❌ couple persistence et calcul.
24. **Domain pur ?** ✅ pas de Django dans `domain/`, testable sans DB.

## Tests / DevOps
25. **Test pyramid ratio ?** ✅ ~70/20/10.
26. **Couverture cible ?** ✅ 85 % global, 100 % sur domain.
27. **CI pipeline ?** ✅ lint → migrate → pytest --cov-fail-under → build image.
28. **Image vs conteneur ?** ✅ image = recette figée, conteneur = instance runtime.
29. **Rollback ?** ✅ image taguée, redéploy + replay batch.

## Incident / trade-offs
30. **PM conteste TE 4.2 % vs Bloomberg 4.5 %.** ✅ tracer run, vérifier benchmark/devise/version, expliquer méthodologie. Pas défendre sans tracer.

## Ce que je dois être capable d'expliquer en entretien
- Donner ces réponses sans hésitation
- Être à l'aise sur les relances ("et si...")
- Reconnaître quand j'ai donné une mauvaise réponse et la corriger
