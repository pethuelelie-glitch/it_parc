# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class WizardRenouvellementContrat(models.TransientModel):
    _name = 'wizard.renouvellement.contrat'
    _description = 'Wizard de renouvellement de contrat fournisseur'

    contrat_id = fields.Many2one(
        'it.contrat',
        string='Contrat à renouveler',
        required=True,
        readonly=True,
    )
    fournisseur_id = fields.Many2one(
        'res.partner',
        string='Fournisseur',
        readonly=True,
    )
    type_contrat = fields.Selection([
        ('maintenance', 'Maintenance matériel'),
        ('licence', 'Licence logicielle'),
        ('support', 'Support technique'),
        ('garantie_ext', 'Garantie étendue'),
        ('autre', 'Autre'),
    ], string='Type', readonly=True)

    ancienne_date_fin = fields.Date(
        related='contrat_id.date_fin',
        string='Ancienne date d\'expiration',
        readonly=True,
    )
    nouvelle_date_debut = fields.Date(
        string='Nouvelle date de début',
        required=True,
        default=fields.Date.today,
    )
    nouvelle_date_fin = fields.Date(
        string='Nouvelle date d\'expiration',
        required=True,
    )
    montant = fields.Float(string='Montant renouvelé (FCFA)', digits=(16, 0))
    note = fields.Text(string='Note de renouvellement')

    @api.constrains('nouvelle_date_debut', 'nouvelle_date_fin')
    def _check_dates(self):
        for rec in self:
            if rec.nouvelle_date_fin <= rec.nouvelle_date_debut:
                raise ValidationError(
                    "La date d'expiration doit être postérieure à la date de début."
                )

    def action_confirmer(self):
        self.ensure_one()
        old = self.contrat_id

        # Archiver l'ancien contrat
        old.write({'state': 'renouvele', 'active': False})

        # Créer le nouveau contrat
        nouveau = self.env['it.contrat'].create({
            'name': f"{old.name} - Renouvellement",
            'fournisseur_id': old.fournisseur_id.id,
            'type_contrat': old.type_contrat,
            'date_debut': self.nouvelle_date_debut,
            'date_fin': self.nouvelle_date_fin,
            'montant': self.montant or old.montant,
            'equipement_ids': [(6, 0, old.equipement_ids.ids)],
            'note': self.note or '',
            'state': 'actif',
        })

        # Marquer les alertes liées comme traitées
        self.env['it.alerte'].search([
            ('contrat_id', '=', old.id),
            ('state', '!=', 'traitee'),
        ]).write({'state': 'traitee'})

        return {
            'type': 'ir.actions.act_window',
            'name': 'Contrat renouvelé',
            'res_model': 'it.contrat',
            'res_id': nouveau.id,
            'view_mode': 'form',
            'target': 'current',
        }
