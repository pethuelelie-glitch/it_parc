# IT Parc — Module de gestion du parc informatique
### Odoo 18 | TECHPARK CI

---

## Description

Module Odoo 18 complet pour la gestion du parc informatique de TECHPARK CI (Abidjan).
Conçu pour ~320 équipements et 85 collaborateurs.

---

## Fonctionnalités

| Fonctionnalité | Description |
|---|---|
| 📋 Inventaire | Gestion des équipements avec workflow 4 états (brouillon → affecté → maintenance → retiré) |
| 👤 Affectations | Affectation aux employés + historique complet des changements |
| 🔧 Interventions | Suivi des maintenances correctives et préventives avec planning calendrier |
| 📄 Contrats | Gestion des contrats fournisseurs avec alertes d'expiration |
| 🔔 Alertes | Scan automatique quotidien des garanties et contrats expirants |
| 📥 Import CSV | Import en masse avec détection de doublons et rapport HTML |
| 📊 Rapports PDF | 3 rapports QWeb (fiche équipement, inventaire, maintenances) |
| 📈 Exports Excel | 3 exports xlsxwriter (inventaire, coûts, contrats expirants) |
| 🖥️ Dashboard OWL | Tableau de bord OWL 2 avec 5 KPIs + graphique barres + barres d'état |

---

## Installation

```bash
# Copier le dossier dans votre répertoire addons
cp -r it_parc /path/to/odoo/addons/

# Redémarrer Odoo et mettre à jour la liste des apps
./odoo-bin -c odoo.conf --update=all

# Ou installer via l'interface Apps
```

**Dépendances Python :**
```bash
pip install xlsxwriter
```

---

## Dépendances Odoo

```python
[
        'base', 'mail', 'hr', 'web',
        'stock', 'purchase', 'account', 'maintenance', 'contacts',
],
```

---

## Structure du module

```
it_parc/
├── models/             # 5 modèles métier
│   ├── it_equipement.py    # Équipements + dashboard data
│   ├── it_affectation.py   # Historique affectations
│   ├── it_intervention.py  # Interventions maintenance
│   ├── it_contrat.py       # Contrats fournisseurs
│   └── it_alerte.py        # Alertes + cron scan
├── wizards/            # 4 wizards
│   ├── wizard_reaffectation.py
│   ├── wizard_renouvellement_contrat.py
│   ├── wizard_import_csv.py
│   └── wizard_scan_alertes.py
├── controllers/        # Exports Excel HTTP
│   └── main.py
├── views/              # 10 fichiers XML vues
├── report/             # 3 rapports QWeb PDF
├── security/           # Groupes + droits d'accès
├── data/               # Séquences, crons, démo
└── static/src/         # Dashboard OWL (JS + XML)
```

---

## Groupes de sécurité

| Groupe | Droits |
|---|---|
| **IT Technicien** | Lecture inventaire, création/suivi interventions, lecture alertes |
| **IT Manager** | Accès complet (+ contrats, imports, exports, configuration) |

---

## Exports Excel (routes HTTP)

| Route | Description |
|---|---|
| `/it_parc/export/inventaire` | Inventaire complet 16 colonnes (couleurs garantie) |
| `/it_parc/export/couts_maintenance` | Synthèse coûts par équipement |
| `/it_parc/export/contrats_expirants` | Contrats expirant dans 60 jours (couleurs urgence) |

---

## Séquence de référence

Format : `EQ/2025/0001`

---

## Auteur

**TECHPARK CI** — Module développé pour la gestion interne du parc informatique.
Odoo 18 | Python 3.11+ | OWL 2
