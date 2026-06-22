# -*- coding: utf-8 -*-
{
    'name': 'IT Parc - Gestion de parc informatique',
    'version': '18.0.1.0.0',
    'category': 'Tools',
    'summary': 'Gestion complète du parc informatique interne',
    'description': """
        Module de gestion du parc informatique pour TECHPARK CI.
        - Inventaire des équipements avec workflow d'état
        - Affectation aux employés et historique
        - Suivi des interventions de maintenance
        - Gestion des contrats fournisseurs
        - Alertes automatiques (garanties, contrats)
        - Import en masse par CSV
        - Rapports PDF (QWeb) et exports Excel (xlsxwriter)
        - Tableau de bord OWL avec KPIs et graphiques
    """,
    'author': 'TECHPARK CI',
    'depends': [
        'base', 'mail', 'hr', 'web',
        'stock', 'purchase', 'account', 'maintenance', 'contacts',
    ],
    'data': [
        'security/it_parc_security.xml',
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'data/ir_cron.xml',
        'views/menus.xml',
        'views/it_equipement_views.xml',
        'views/it_affectation_views.xml',
        'views/it_intervention_views.xml',
        'views/it_contrat_views.xml',
        'views/it_alerte_views.xml',
        'views/wizard_reaffectation_views.xml',
        'views/wizard_renouvellement_views.xml',
        'views/wizard_import_csv_views.xml',
        'views/wizard_scan_alertes_views.xml',
        'report/report_fiche_equipement.xml',
        'report/report_inventaire.xml',
        'report/report_maintenances.xml',
    ],
    'demo': [
        'data/it_parc_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'it_parc/static/src/xml/dashboard.xml',
            'it_parc/static/src/js/dashboard.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
