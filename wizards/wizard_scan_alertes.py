# -*- coding: utf-8 -*-
from odoo import fields, models


class WizardScanAlertes(models.TransientModel):
    _name = 'wizard.scan.alertes'
    _description = 'Scan manuel des alertes'

    delai_jours = fields.Integer(
        string='Délai d\'anticipation (jours)',
        default=30,
        help="Générer des alertes pour les garanties/contrats qui expirent dans X jours.",
    )
    nb_alertes_creees = fields.Integer(
        string='Alertes générées',
        readonly=True,
    )
    scan_fait = fields.Boolean(default=False)

    def action_lancer_scan(self):
        self.ensure_one()
        Alerte = self.env['it.alerte']

        # Compter avant
        avant = Alerte.search_count([])
        Alerte.scan_alertes_auto(delai_jours=self.delai_jours)
        apres = Alerte.search_count([])

        self.write({
            'nb_alertes_creees': apres - avant,
            'scan_fait': True,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_voir_alertes(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Alertes actives',
            'res_model': 'it.alerte',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'nouvelle')],
            'target': 'current',
        }
