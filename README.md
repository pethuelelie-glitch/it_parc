# IT Parc - Module de Gestion du Parc Informatique

IT Parc est un module Odoo 18 développé pour **TECHPARK CI**. Il permet de gérer l'ensemble du cycle de vie des équipements informatiques d'une organisation : inventaire, affectations, maintenances, contrats fournisseurs et alertes automatiques.

---

## Fonctionnalités principales

**Gestion des équipements**
Suivi complet des équipements (ordinateurs, serveurs, imprimantes, équipements réseau, téléphones IP, etc.) avec états de workflow : Brouillon, Affecté, En maintenance, Réformé.

**Affectations**
Historique complet des affectations d'équipements aux employés, avec gestion des transferts via un assistant de réaffectation.

**Maintenances / Interventions**
Enregistrement des interventions correctives, préventives et évolutives. Vue calendrier intégrée pour planifier les interventions. Suivi des coûts et des durées.

**Contrats fournisseurs**
Gestion des contrats de maintenance, de licence, d'assurance et de support avec suivi des dates d'expiration et renouvellement assisté.

**Alertes automatiques**
Génération quotidienne (via tâches planifiées) d'alertes pour les garanties et contrats proches de l'expiration.

**Imports / Exports**
- Import en masse d'équipements depuis un fichier CSV avec détection des doublons
- Export Excel de l'inventaire, des coûts de maintenance et des contrats expirants
- Rapports PDF (fiche équipement, inventaire, journal des maintenances)

**Tableau de bord**
Composant interactif avec indicateurs clés (KPI), graphique de répartition par catégorie et raccourcis de navigation.

---

## Stack technique

- Odoo 18.0 (framework)
- Python 3 (modèles ORM)
- JavaScript ES6 + OWL (composant dashboard)
- Bootstrap 5 + Font Awesome (interface)
- xlsxwriter (exports Excel)
- QWeb (rapports PDF)
- Chart.js (graphiques)
- PostgreSQL (base de données via ORM Odoo)

---

## Dépendances Odoo

- base
- mail
- hr
- web

---

## Structure du module

```
it_parc/
├── models/          # Modèles métier (équipements, affectations, interventions, contrats, alertes)
├── wizards/         # Assistants (import CSV, export Excel, réaffectation, renouvellement, scan alertes)
├── controllers/     # Point d'entrée API pour le dashboard
├── views/           # Vues XML (formulaires, listes, kanban, calendrier, menus)
├── report/          # Templates QWeb pour les rapports PDF
├── security/        # Groupes d'accès (Technicien, Gestionnaire) et règles ACL
├── data/            # Séquences, tâches planifiées, données de démonstration
└── static/          # Assets frontend (JS, XML dashboard)
```

---

## Sécurité

Deux niveaux d'accès sont définis :

- **Technicien IT** : lecture sur les équipements et contrats, création et gestion des interventions et alertes.
- **Gestionnaire IT** : accès complet en lecture/écriture sur tous les enregistrements.

---

## Installation

1. Copier le dossier `it_parc` dans le répertoire `addons` de votre instance Odoo.
2. Mettre à jour la liste des modules depuis le menu Technique.
3. Rechercher "IT Parc" et installer le module.
4. Assigner les utilisateurs aux groupes **Technicien IT** ou **Gestionnaire IT**.

---

## Auteur

Développé par **ELIE EHOUSSOU**
