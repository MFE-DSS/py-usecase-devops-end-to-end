# 04 — Software Concepts

## MVC vs MTV
- **MVC**: Model-View-Controller (Rails, Spring)
- **MTV** (Django): Model-Template-View. La "View" Django joue le rôle du Controller MVC. Le "Template" rend la View MVC.
- Avec **DRF** : pas de Templates, on a Model + Serializer + ViewSet. Le Serializer remplace le Template (produit du JSON au lieu d'HTML).

## Rôles des couches
| Couche | Rôle | Exemple projet |
|---|---|---|
| Model | Schéma persisté | `Fund`, `RiskMetric` |
| ViewSet | Reçoit HTTP, délègue, sérialise | `RiskMetricViewSet` |
| Serializer | JSON ↔ ORM, validation | `RiskMetricSerializer` |
| Service | Orchestration use case | `TrackingErrorCalculationService` |
| Repository | Accès données | `ReturnRepository` |
| Domain | Logique pure | `compute_tracking_error()` |

## Anti-patterns à connaître
- **Fat Model** : `Fund.compute_tracking_error()` couple persistence et calcul
- **Calcul dans la View** : impossible de réutiliser en batch/CLI
- **Service anémique** : 1 ligne d'ORM dans un service = supprime
- **`Meta.fields = "__all__"`** : fuite de champs internes

## SOLID appliqué
| Lettre | Application |
|---|---|
| **S** | `compute_tracking_error` ne fait qu'une chose |
| **O** | Nouvelle métrique = nouvelle fonction + route, sans modifier l'existant |
| **L** | Repository remplaçable par un fake en test |
| **I** | `ReturnRepository` n'expose que `get_monthly_returns`, pas tout l'ORM |
| **D** | Service prend repos en constructeur, pas de `Manager` ORM en dur |

## DRY / KISS / YAGNI
- **DRY** : une seule définition de la formule, dans `domain/metrics.py`
- **KISS** : Django + DRF + Postgres. Pas de Celery, pas de microservices, pas d'event sourcing
- **YAGNI** : pas d'abstraction `BaseMetricCalculator` pour 1 métrique

## DIP en Django concret
```python
class TrackingErrorCalculationService:
    def __init__(self, return_repo, metric_repo):
        self._returns = return_repo
        self._metrics = metric_repo
```
En tests : on injecte des fakes. En prod : implémentations ORM.

## Domain / Application / Infrastructure
- **Domain** : `domain/metrics.py` — pas de Django
- **Application** : `services/` — orchestration, transactions
- **Infrastructure** : `models.py`, `repositories/`, `api/`

## Concepts API à connaître
- **API contract** : le JSON est une promesse, pas un détail d'implémentation
- **Idempotence** : POST avec `Idempotency-Key` ne crée pas de doublon
- **Stateless** : aucun état serveur entre requêtes
- **Auditability** : chaque métrique liée à un `CalculationRun` (qui, quand, quelle version)
- **Observability** : logs structurés, healthcheck, métriques

## Ce que je dois être capable d'expliquer en entretien
- Différence MVC / MTV en 20 secondes
- Pourquoi pas tout dans le Model
- SOLID avec un exemple concret par lettre
- Quand DIP est utile vs overkill
