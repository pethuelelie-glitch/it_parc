# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ItIntervention(models.Model):
    _name = 'it.intervention'
    _description = 'Intervention de maintenance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_debut desc'

    name = fields.Char(string='Référence', readonly=True, copy=False, default='Nouveau')
    equipement_id = fields.Many2one('it.equipement', string='Équipement', required=True, ondelete='cascade')
    type_intervention = fields.Selection([
        ('corrective', 'Corrective'),
        ('preventive', 'Préventive'),
        ('evolutive', 'Évolutive'),
    ], string='Type', required=True, default='corrective')
    description = fields.Text(string='Description du problème', required=True)
    resolution = fields.Text(string='Résolution / Rapport')
    technicien_id = fields.Many2one('res.users', string='Technicien', default=lambda self: self.env.user, tracking=True)
    date_debut = fields.Datetime(string='Date début', required=True, default=fields.Datetime.now)
    date_fin = fields.Datetime(string='Date fin')
    duree = fields.Float(string='Durée (heures)', compute='_compute_duree', store=True)
    cout = fields.Float(string='Coût (FCFA)', digits=(16, 0))
    etat = fields.Selection([
        ('planifie', 'Planifiée'),
        ('en_cours', 'En cours'),
        ('termine', 'Terminée'),
        ('annule', 'Annulée'),
    ], string='État', default='planifie', required=True, tracking=True)

    @api.depends('date_debut', 'date_fin')
    def _compute_duree(self):
        for rec in self:
            if rec.date_debut and rec.date_fin:
                delta = rec.date_fin - rec.date_debut
                rec.duree = round(delta.total_seconds() / 3600, 2)
            else:
                rec.duree = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('it.intervention') or 'Nouveau'
        return super().create(vals_list)

    def action_demarrer(self):
        for rec in self:
            rec.write({'etat': 'en_cours'})
            if rec.equipement_id.etat not in ('en_maintenance', 'retire'):
                rec.equipement_id.write({'etat': 'en_maintenance'})

    def action_terminer(self):
        for rec in self:
            if not rec.date_fin:
                rec.date_fin = fields.Datetime.now()
            rec.write({'etat': 'termine'})
            actives = rec.equipement_id.intervention_ids.filtered(
                lambda i: i.etat == 'en_cours' and i.id != rec.id
            )
            if not actives and rec.equipement_id.etat == 'en_maintenance':
                new_etat = 'affecte' if rec.equipement_id.employee_id else 'brouillon'
                rec.equipement_id.write({'etat': new_etat})

    def action_annuler(self):
        self.write({'etat': 'annule'})

    @api.constrains('date_debut', 'date_fin')
    def _check_dates(self):
        for rec in self:
            if rec.date_debut and rec.date_fin and rec.date_fin < rec.date_debut:
                raise ValidationError(_("La date de fin doit être postérieure à la date de début."))

    @api.constrains('cout')
    def _check_cout(self):
        for rec in self:
            if rec.cout < 0:
                raise ValidationError(_("Le coût ne peut pas être négatif."))
