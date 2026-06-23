# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ItAffectation(models.Model):
    _name = 'it.affectation'
    _description = 'Affectation équipement'
    _inherit = ['mail.thread']
    _order = 'date_debut desc'
    _rec_name = 'equipement_id'

    equipement_id = fields.Many2one('it.equipement', string='Équipement', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employé', required=True)
    department_id = fields.Many2one('hr.department', string='Département')
    date_debut = fields.Date(string='Date début', required=True, default=fields.Date.today)
    date_fin = fields.Date(string='Date fin')
    motif = fields.Text(string='Motif')
    etat = fields.Selection([
        ('actif', 'Active'),
        ('termine', 'Terminée'),
    ], string='État', default='actif', tracking=True)

    @api.onchange('employee_id')
    def _onchange_employee(self):
        if self.employee_id and self.employee_id.department_id:
            self.department_id = self.employee_id.department_id

    @api.constrains('date_debut', 'date_fin')
    def _check_dates(self):
        for rec in self:
            if rec.date_debut and rec.date_fin and rec.date_fin < rec.date_debut:
                raise ValidationError(_("La date de fin doit être postérieure à la date de début."))

    def action_terminer(self):
        for rec in self:
            rec.write({'etat': 'termine', 'date_fin': fields.Date.today()})
