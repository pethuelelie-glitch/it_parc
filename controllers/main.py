# -*- coding: utf-8 -*-
from datetime import date
from odoo import http
from odoo.http import request


class ItParcDashboardController(http.Controller):

    @http.route('/it_parc/dashboard', type='json', auth='user')
    def dashboard_data(self):
        env = request.env
        Equip = env['it.equipement']
        Inter = env['it.intervention']
        Alerte = env['it.alerte']

        total = Equip.search_count([])
        actifs = Equip.search_count([('etat', '=', 'affecte')])
        en_maintenance = Equip.search_count([('etat', '=', 'en_maintenance')])
        retires = Equip.search_count([('etat', '=', 'retire')])
        alertes_actives = Alerte.search_count([('etat', '=', 'actif')])

        # Répartition par catégorie
        par_categorie = []
        sel_cats = dict(env['it.equipement']._fields['categorie'].selection)
        for code, label in sel_cats.items():
            count = Equip.search_count([('categorie', '=', code)])
            if count:
                par_categorie.append({'code': code, 'label': label, 'count': count})
        par_categorie.sort(key=lambda x: -x['count'])

        # Coût maintenance ce mois
        today = date.today()
        premier_mois = today.replace(day=1)
        inter_mois = Inter.search([
            ('etat', '=', 'termine'),
            ('date_debut', '>=', str(premier_mois) + ' 00:00:00'),
        ])
        cout_mois = sum(inter_mois.mapped('cout'))

        return {
            'total': total,
            'actifs': actifs,
            'en_maintenance': en_maintenance,
            'retires': retires,
            'alertes_actives': alertes_actives,
            'cout_mois': cout_mois,
            'par_categorie': par_categorie,
        }
