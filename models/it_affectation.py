# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ItAffectation(models.Model):
    _name = 'it.affectation'
    _description = 'Historique d\'affectation d\'équipement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_debut desc'

    equipement_id = fields.Many2one(
        'it.equipement',
        string='Équipement',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employé',
        required=True,
        tracking=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Département',
        tracking=True,
    )
    date_debut = fields.Date(
        string='Date de début',
        required=True,
        default=fields.Date.today,
        tracking=True,
    )
    date_fin = fields.Date(string='Date de fin', tracking=True)
    motif = fields.Text(string='Motif de changement')
    active = fields.Boolean(default=True)
