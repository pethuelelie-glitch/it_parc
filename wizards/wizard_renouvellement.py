# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class WizardRenouvellement(models.TransientModel):
    _name = 'wizard.renouvellement'
    _description = 'Wizard de renouvellement de contrat'

    contrat_id = fields.Many2one('it.contrat', string='Contrat à renouveler', required=True)
    nouvelle_date_debut = fields.Date(string='Nouvelle date début', required=True, default=fields.Date.today)
    nouvelle_date_fin = fields.Date(string='Nouvelle date fin', required=True)
    nouveau_montant = fields.Float(string='Nouveau montant (FCFA)', digits=(16, 0))
    notes = fields.Text(string='Notes')

    @api.constrains('nouvelle_date_debut', 'nouvelle_date_fin')
    def _check_dates(self):
        for rec in self:
            if rec.nouvelle_date_debut and rec.nouvelle_date_fin and rec.nouvelle_date_fin <= rec.nouvelle_date_debut:
                raise UserError(_("La nouvelle date de fin doit être postérieure à la date de début."))

    def action_renouveler(self):
        self.ensure_one()
        old = self.contrat_id
        old.write({'etat': 'renouvele'})
        new_ref = self.env['ir.sequence'].next_by_code('it.contrat') or 'CTR/NEW'
        nouveau = old.copy({
            'reference': new_ref,
            'date_debut': self.nouvelle_date_debut,
            'date_fin': self.nouvelle_date_fin,
            'montant': self.nouveau_montant or old.montant,
            'etat': 'actif',
            'notes': self.notes or old.notes,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nouveau contrat'),
            'res_model': 'it.contrat',
            'view_mode': 'form',
            'res_id': nouveau.id,
        }
