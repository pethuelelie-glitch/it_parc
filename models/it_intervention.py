# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ItIntervention(models.Model):
    _name = 'it.intervention'
    _description = 'Intervention de maintenance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_debut desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Titre de l\'intervention',
        required=True,
        tracking=True,
    )
    equipement_id = fields.Many2one(
        'it.equipement',
        string='Équipement',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    type_intervention = fields.Selection([
        ('correctif', 'Correctif'),
        ('preventif', 'Préventif'),
        ('upgrade', 'Mise à niveau'),
        ('autre', 'Autre'),
    ], string='Type', required=True, default='correctif', tracking=True)

    technicien_id = fields.Many2one(
        'hr.employee',
        string='Technicien responsable',
        tracking=True,
    )

    date_debut = fields.Datetime(
        string='Date de début',
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    date_fin = fields.Datetime(
        string='Date de fin',
        tracking=True,
    )
    duree = fields.Float(
        string='Durée (heures)',
        compute='_compute_duree',
        store=True,
        digits=(10, 2),
    )

    cout = fields.Float(
        string='Coût (FCFA)',
        digits=(16, 0),
        tracking=True,
    )
    rapport = fields.Html(string='Rapport d\'intervention')

    state = fields.Selection([
        ('planifie', 'Planifiée'),
        ('en_cours', 'En cours'),
        ('termine', 'Terminée'),
        ('annule', 'Annulée'),
    ], string='État', default='planifie', tracking=True)

    @api.depends('date_debut', 'date_fin')
    def _compute_duree(self):
        for rec in self:
            if rec.date_debut and rec.date_fin:
                delta = rec.date_fin - rec.date_debut
                rec.duree = delta.total_seconds() / 3600
            else:
                rec.duree = 0.0

    def action_demarrer(self):
        self.write({'state': 'en_cours'})

    def action_terminer(self):
        for rec in self:
            if not rec.date_fin:
                rec.date_fin = fields.Datetime.now()
            rec.state = 'termine'
            # Remettre l'équipement en état affecté si disponible
            if rec.equipement_id.state == 'en_maintenance':
                rec.equipement_id.state = 'affecte' if rec.equipement_id.employee_id else 'brouillon'

    def action_annuler(self):
        self.write({'state': 'annule'})
