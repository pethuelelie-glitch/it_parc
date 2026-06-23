# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class ItContrat(models.Model):
    _name = 'it.contrat'
    _description = 'Contrat fournisseur'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_fin'

    name = fields.Char(string='Intitulé du contrat', required=True)
    reference = fields.Char(string='Référence', readonly=True, copy=False, default='Nouveau')
    fournisseur_id = fields.Many2one('res.partner', string='Fournisseur', required=True)
    type_contrat = fields.Selection([
        ('maintenance', 'Maintenance'),
        ('licence', 'Licence logicielle'),
        ('assurance', 'Assurance'),
        ('support', 'Support technique'),
        ('autre', 'Autre'),
    ], string='Type de contrat', required=True)
    date_debut = fields.Date(string='Date début', required=True)
    date_fin = fields.Date(string='Date fin', required=True, tracking=True)
    montant = fields.Float(string='Montant annuel (FCFA)', digits=(16, 0))
    equipement_ids = fields.Many2many(
        'it.equipement', 'it_equipement_contrat_rel', 'contrat_id', 'equipement_id',
        string='Équipements couverts'
    )
    etat = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('actif', 'Actif'),
        ('expire', 'Expiré'),
        ('renouvele', 'Renouvelé'),
        ('resilie', 'Résilié'),
    ], string='État', default='brouillon', required=True, tracking=True)
    notes = fields.Text(string='Notes')
    alerte_ids = fields.One2many('it.alerte', 'contrat_id', string='Alertes')

    jours_restants = fields.Integer(
        string='Jours restants', compute='_compute_jours_restants', store=True)
    expire = fields.Boolean(
        string='Expiré', compute='_compute_jours_restants', store=True)

    @api.depends('date_fin')
    def _compute_jours_restants(self):
        today = date.today()
        for rec in self:
            if rec.date_fin:
                delta = (rec.date_fin - today).days
                rec.jours_restants = delta
                rec.expire = delta < 0
            else:
                rec.jours_restants = 0
                rec.expire = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'Nouveau') == 'Nouveau':
                vals['reference'] = self.env['ir.sequence'].next_by_code('it.contrat') or 'Nouveau'
        return super().create(vals_list)

    def action_activer(self):
        self.write({'etat': 'actif'})

    def action_resilier(self):
        self.write({'etat': 'resilie'})

    def action_renouveler(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renouveler le contrat'),
            'res_model': 'wizard.renouvellement',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_contrat_id': self.id},
        }

    @api.constrains('date_debut', 'date_fin')
    def _check_dates(self):
        for rec in self:
            if rec.date_debut and rec.date_fin and rec.date_fin <= rec.date_debut:
                raise ValidationError(_("La date de fin doit être postérieure à la date de début."))

    @api.model
    def cron_update_etats(self):
        """Tâche planifiée : met à jour l'état des contrats expirés et génère les alertes."""
        today = fields.Date.today()
        expires = self.search([('etat', '=', 'actif'), ('date_fin', '<', today)])
        expires.write({'etat': 'expire'})

        seuil = today + timedelta(days=60)
        contrats = self.search([('etat', '=', 'actif'), ('date_fin', '<=', seuil)])
        Alerte = self.env['it.alerte']
        for contrat in contrats:
            existe = Alerte.search([
                ('contrat_id', '=', contrat.id),
                ('type_alerte', '=', 'contrat'),
                ('etat', '=', 'actif'),
            ], limit=1)
            if not existe:
                Alerte.create({
                    'name': _("Expiration contrat — %s") % contrat.name,
                    'type_alerte': 'contrat',
                    'contrat_id': contrat.id,
                    'date_echeance': contrat.date_fin,
                    'message': _(
                        "Le contrat '%s' (réf. %s) avec %s expire le %s (%d jours restants)."
                    ) % (contrat.name, contrat.reference, contrat.fournisseur_id.name,
                         contrat.date_fin, contrat.jours_restants),
                })
