# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ItAlerte(models.Model):
    _name = 'it.alerte'
    _description = 'Alerte IT Parc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'jours_restants asc'
    _rec_name = 'name'

    name = fields.Char(string='Titre', required=True)
    type_alerte = fields.Selection([
        ('garantie', 'Expiration de garantie'),
        ('contrat', 'Expiration de contrat'),
    ], string='Type', required=True, tracking=True)

    equipement_id = fields.Many2one(
        'it.equipement',
        string='Équipement concerné',
        ondelete='cascade',
    )
    contrat_id = fields.Many2one(
        'it.contrat',
        string='Contrat concerné',
        ondelete='cascade',
    )
    date_expiration = fields.Date(string='Date d\'expiration')
    jours_restants = fields.Integer(string='Jours restants')

    state = fields.Selection([
        ('nouvelle', 'Nouvelle'),
        ('vue', 'Vue'),
        ('traitee', 'Traitée'),
    ], string='État', default='nouvelle', tracking=True)

    message = fields.Text(string='Message détaillé')
    urgence = fields.Selection([
        ('faible', 'Faible'),
        ('moyenne', 'Moyenne'),
        ('haute', 'Haute'),
        ('critique', 'Critique'),
    ], string='Urgence', compute='_compute_urgence', store=True)

    @api.depends('jours_restants')
    def _compute_urgence(self):
        for rec in self:
            j = rec.jours_restants
            if j < 0:
                rec.urgence = 'critique'
            elif j <= 7:
                rec.urgence = 'haute'
            elif j <= 30:
                rec.urgence = 'moyenne'
            else:
                rec.urgence = 'faible'

    def action_marquer_vue(self):
        self.write({'state': 'vue'})

    def action_marquer_traitee(self):
        self.write({'state': 'traitee'})

    # ──────────────────────────────────────────────
    # Scan automatique (appelé par ir.cron)
    # ──────────────────────────────────────────────
    @api.model
    def scan_alertes_auto(self, delai_jours=30):
        """
        Génère des alertes pour les garanties et contrats
        qui expirent dans les `delai_jours` prochains jours.
        Évite les doublons.
        """
        from datetime import date, timedelta
        today = date.today()
        limite = today + timedelta(days=delai_jours)

        # --- Scan des garanties équipements ---
        equipements = self.env['it.equipement'].search([
            ('date_garantie', '!=', False),
            ('date_garantie', '<=', str(limite)),
            ('state', 'not in', ['retire']),
        ])
        for eq in equipements:
            existing = self.search([
                ('type_alerte', '=', 'garantie'),
                ('equipement_id', '=', eq.id),
                ('state', '!=', 'traitee'),
            ], limit=1)
            if not existing:
                jours = (eq.date_garantie - today).days
                self.create({
                    'name': f"Garantie : {eq.name} ({eq.reference})",
                    'type_alerte': 'garantie',
                    'equipement_id': eq.id,
                    'date_expiration': eq.date_garantie,
                    'jours_restants': jours,
                    'message': (
                        f"La garantie de l'équipement {eq.name} "
                        f"(réf. {eq.reference}, S/N : {eq.numero_serie or 'N/A'}) "
                        f"expire {'dans ' + str(jours) + ' jours' if jours >= 0 else 'depuis ' + str(abs(jours)) + ' jours'} "
                        f"(le {eq.date_garantie.strftime('%d/%m/%Y')})."
                    ),
                })

        # --- Scan des contrats fournisseurs ---
        contrats = self.env['it.contrat'].search([
            ('date_fin', '!=', False),
            ('date_fin', '<=', str(limite)),
            ('state', '=', 'actif'),
        ])
        for contrat in contrats:
            existing = self.search([
                ('type_alerte', '=', 'contrat'),
                ('contrat_id', '=', contrat.id),
                ('state', '!=', 'traitee'),
            ], limit=1)
            if not existing:
                jours = (contrat.date_fin - today).days
                self.create({
                    'name': f"Contrat : {contrat.name}",
                    'type_alerte': 'contrat',
                    'contrat_id': contrat.id,
                    'date_expiration': contrat.date_fin,
                    'jours_restants': jours,
                    'message': (
                        f"Le contrat '{contrat.name}' "
                        f"({dict(self.env['it.contrat']._fields['type_contrat'].selection).get(contrat.type_contrat, '')}) "
                        f"avec {contrat.fournisseur_id.name} "
                        f"expire {'dans ' + str(jours) + ' jours' if jours >= 0 else 'depuis ' + str(abs(jours)) + ' jours'} "
                        f"(le {contrat.date_fin.strftime('%d/%m/%Y')})."
                    ),
                })

        return True
