# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class WizardReaffectation(models.TransientModel):
    _name = 'wizard.reaffectation'
    _description = 'Wizard de réaffectation'

    equipement_id = fields.Many2one('it.equipement', string='Équipement', required=True)
    ancien_employee_id = fields.Many2one('hr.employee', string='Ancien employé', compute='_compute_ancien')
    ancien_department_id = fields.Many2one('hr.department', string='Ancien département', compute='_compute_ancien')
    nouvel_employee_id = fields.Many2one('hr.employee', string='Nouvel employé', required=True)
    nouveau_department_id = fields.Many2one('hr.department', string='Nouveau département')
    date_reaffectation = fields.Date(string='Date de réaffectation', required=True, default=fields.Date.today)
    motif = fields.Text(string='Motif de réaffectation', required=True)

    @api.depends('equipement_id')
    def _compute_ancien(self):
        for rec in self:
            rec.ancien_employee_id = rec.equipement_id.employee_id
            rec.ancien_department_id = rec.equipement_id.department_id

    @api.onchange('nouvel_employee_id')
    def _onchange_employee(self):
        if self.nouvel_employee_id and self.nouvel_employee_id.department_id:
            self.nouveau_department_id = self.nouvel_employee_id.department_id

    def action_reaffecter(self):
        self.ensure_one()
        equip = self.equipement_id
        if equip.employee_id == self.nouvel_employee_id:
            raise UserError(_("L'équipement est déjà affecté à cet employé."))

        # Terminer l'affectation active
        affectations_actives = self.env['it.affectation'].search([
            ('equipement_id', '=', equip.id),
            ('etat', '=', 'actif'),
        ])
        affectations_actives.write({'etat': 'termine', 'date_fin': self.date_reaffectation})

        # Créer la nouvelle affectation
        self.env['it.affectation'].create({
            'equipement_id': equip.id,
            'employee_id': self.nouvel_employee_id.id,
            'department_id': self.nouveau_department_id.id if self.nouveau_department_id else False,
            'date_debut': self.date_reaffectation,
            'motif': self.motif,
            'etat': 'actif',
        })

        # Mettre à jour l'équipement
        equip.write({
            'employee_id': self.nouvel_employee_id.id,
            'department_id': self.nouveau_department_id.id if self.nouveau_department_id else False,
            'etat': 'affecte',
        })
        return {'type': 'ir.actions.act_window_close'}
