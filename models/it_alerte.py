# -*- coding: utf-8 -*-
from odoo import models, fields


class ItAlerte(models.Model):
    _name = 'it.alerte'
    _description = 'Alerte parc informatique'
    _order = 'date_echeance'
    _rec_name = 'name'

    name = fields.Char(string='Alerte', required=True)
    type_alerte = fields.Selection([
        ('garantie', 'Fin de garantie'),
        ('contrat', 'Expiration contrat'),
        ('maintenance', 'Maintenance préventive'),
    ], string='Type', required=True)
    equipement_id = fields.Many2one('it.equipement', string='Équipement', ondelete='cascade')
    contrat_id = fields.Many2one('it.contrat', string='Contrat', ondelete='cascade')
    date_echeance = fields.Date(string='Date échéance', required=True)
    message = fields.Text(string='Message')
    etat = fields.Selection([
        ('actif', 'Active'),
        ('traite', 'Traitée'),
        ('ignore', 'Ignorée'),
    ], string='État', default='actif', required=True)

    def action_traiter(self):
        self.write({'etat': 'traite'})

    def action_ignorer(self):
        self.write({'etat': 'ignore'})
