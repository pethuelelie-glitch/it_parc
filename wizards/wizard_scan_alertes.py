# -*- coding: utf-8 -*-
from odoo import models, fields, _
from datetime import timedelta


class WizardScanAlertes(models.TransientModel):
    _name = 'wizard.scan.alertes'
    _description = 'Scan manuel des alertes'

    jours_avant_garantie = fields.Integer(
        string='Alerter X jours avant fin de garantie', default=30, required=True)
    jours_avant_contrat = fields.Integer(
        string='Alerter X jours avant expiration contrat', default=30, required=True)
    nb_alertes_creees = fields.Integer(string='Alertes créées', readonly=True)
    resultat = fields.Text(string='Résultat', readonly=True)
    traite = fields.Boolean(default=False)

    def action_scanner(self):
        self.ensure_one()
        today = fields.Date.today()
        nb = 0
        Alerte = self.env['it.alerte']

        # Alertes garanties équipements
        seuil_g = today + timedelta(days=self.jours_avant_garantie)
        equipements = self.env['it.equipement'].search([
            ('date_fin_garantie', '!=', False),
            ('date_fin_garantie', '<=', seuil_g),
            ('etat', 'not in', ['retire']),
        ])
        for equip in equipements:
            existe = Alerte.search([
                ('equipement_id', '=', equip.id),
                ('type_alerte', '=', 'garantie'),
                ('etat', '=', 'actif'),
            ], limit=1)
            if not existe:
                Alerte.create({
                    'name': _("Fin de garantie — %s") % equip.name,
                    'type_alerte': 'garantie',
                    'equipement_id': equip.id,
                    'date_echeance': equip.date_fin_garantie,
                    'message': _(
                        "La garantie de '%s' (réf. %s) expire le %s."
                    ) % (equip.name, equip.reference, equip.date_fin_garantie),
                })
                nb += 1

        # Alertes contrats
        seuil_c = today + timedelta(days=self.jours_avant_contrat)
        contrats = self.env['it.contrat'].search([
            ('etat', '=', 'actif'),
            ('date_fin', '<=', seuil_c),
        ])
        for contrat in contrats:
            existe = Alerte.search([
                ('contrat_id', '=', contrat.id),
                ('type_alerte', '=', 'contrat'),
                ('etat', '=', 'actif'),
            ], limit=1)
            if not existe:
                Alerte.create({
                    'name': _("Expiration contrat — %s") % contrat.name,
                    'type_alerte': 'contrat',
                    'contrat_id': contrat.id,
                    'date_echeance': contrat.date_fin,
                    'message': _(
                        "Le contrat '%s' (réf. %s) avec %s expire le %s."
                    ) % (contrat.name, contrat.reference, contrat.fournisseur_id.name, contrat.date_fin),
                })
                nb += 1

        self.write({
            'nb_alertes_creees': nb,
            'resultat': _("%d alerte(s) créée(s).") % nb,
            'traite': True,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.scan.alertes',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
