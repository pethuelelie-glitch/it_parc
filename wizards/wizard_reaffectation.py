# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class WizardReaffectation(models.TransientModel):
    _name = 'wizard.reaffectation'
    _description = 'Wizard de réaffectation d\'équipement'

    equipement_id = fields.Many2one(
        'it.equipement',
        string='Équipement',
        required=True,
        readonly=True,
    )
    employee_id_actuel = fields.Many2one(
        related='equipement_id.employee_id',
        string='Employé actuel',
        readonly=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nouvel employé',
        required=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Nouveau département',
    )
    localisation = fields.Char(string='Nouvelle localisation')
    motif = fields.Text(
        string='Motif de réaffectation',
        required=True,
    )
    date_affectation = fields.Date(
        string='Date d\'effet',
        required=True,
        default=fields.Date.today,
    )

    @api.onchange('employee_id')
    def _onchange_employee(self):
        if self.employee_id and self.employee_id.department_id:
            self.department_id = self.employee_id.department_id

    def action_confirmer(self):
        self.ensure_one()
        equipement = self.equipement_id

        if self.employee_id == equipement.employee_id:
            raise ValidationError(
                "Le nouvel employé est identique à l'employé actuel."
            )

        # Clôturer l'affectation en cours
        affectation_courante = self.env['it.affectation'].search([
            ('equipement_id', '=', equipement.id),
            ('date_fin', '=', False),
        ], limit=1)
        if affectation_courante:
            affectation_courante.date_fin = self.date_affectation

        # Créer la nouvelle affectation
        self.env['it.affectation'].create({
            'equipement_id': equipement.id,
            'employee_id': self.employee_id.id,
            'department_id': self.department_id.id if self.department_id else False,
            'date_debut': self.date_affectation,
            'motif': self.motif,
        })

        # Mettre à jour l'équipement
        vals = {
            'employee_id': self.employee_id.id,
            'state': 'affecte',
        }
        if self.department_id:
            vals['department_id'] = self.department_id.id
        if self.localisation:
            vals['localisation'] = self.localisation

        equipement.write(vals)
        equipement.message_post(
            body=(
                f"<b>Réaffectation</b> : {equipement.employee_id.name or 'N/A'} "
                f"→ {self.employee_id.name}<br/>"
                f"<b>Motif</b> : {self.motif}"
            )
        )

        return {'type': 'ir.actions.act_window_close'}
