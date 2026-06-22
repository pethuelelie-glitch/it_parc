# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ItContrat(models.Model):
    _name = 'it.contrat'
    _description = 'Contrat fournisseur'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_fin asc'
    _rec_name = 'name'

    name = fields.Char(
        string='Référence du contrat',
        required=True,
        tracking=True,
    )
    fournisseur_id = fields.Many2one(
        'res.partner',
        string='Fournisseur',
        required=True,
        domain=[('is_company', '=', True)],
        tracking=True,
    )
    type_contrat = fields.Selection([
        ('maintenance', 'Maintenance matériel'),
        ('licence', 'Licence logicielle'),
        ('support', 'Support technique'),
        ('garantie_ext', 'Garantie étendue'),
        ('autre', 'Autre'),
    ], string='Type de contrat', required=True, default='maintenance', tracking=True)

    date_debut = fields.Date(string='Date de début', tracking=True)
    date_fin = fields.Date(string='Date d\'expiration', required=True, tracking=True)

    montant = fields.Float(string='Montant (FCFA)', digits=(16, 0))

    state = fields.Selection([
        ('actif', 'Actif'),
        ('expire', 'Expiré'),
        ('renouvele', 'Renouvelé'),
        ('resilie', 'Résilié'),
    ], string='État', default='actif', tracking=True)

    jours_restants = fields.Integer(
        string='Jours restants',
        compute='_compute_jours_restants',
        store=True,
    )
    equipement_ids = fields.Many2many(
        'it.equipement',
        'it_contrat_equipement_rel',
        'contrat_id', 'equipement_id',
        string='Équipements couverts',
    )
    note = fields.Text(string='Observations')
    active = fields.Boolean(default=True)

    @api.depends('date_fin')
    def _compute_jours_restants(self):
        today = fields.Date.today()
        for rec in self:
            if rec.date_fin:
                rec.jours_restants = (rec.date_fin - today).days
            else:
                rec.jours_restants = 0

    def action_renouveler(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Renouveler le contrat',
            'res_model': 'wizard.renouvellement.contrat',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_contrat_id': self.id,
                'default_fournisseur_id': self.fournisseur_id.id,
                'default_type_contrat': self.type_contrat,
                'default_montant': self.montant,
            },
        }

    def action_resilier(self):
        self.write({'state': 'resilie'})

    @api.model
    def _cron_update_expired(self):
        """Cron : mettre à jour l'état des contrats expirés."""
        today = fields.Date.today()
        expired = self.search([
            ('date_fin', '<', today),
            ('state', '=', 'actif'),
        ])
        expired.write({'state': 'expire'})
