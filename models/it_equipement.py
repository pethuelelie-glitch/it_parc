# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class ItEquipement(models.Model):
    _name = 'it.equipement'
    _description = 'Équipement informatique'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'reference desc'

    # ──────────────────────────────────────────────
    # Champs d'identification
    # ──────────────────────────────────────────────
    name = fields.Char(
        string='Nom de l\'équipement',
        required=True,
        tracking=True,
    )
    reference = fields.Char(
        string='Référence interne',
        readonly=True,
        copy=False,
        default='Nouveau',
    )
    active = fields.Boolean(default=True)

    categorie = fields.Selection([
        ('poste_travail', 'Poste de travail'),
        ('serveur', 'Serveur'),
        ('imprimante', 'Imprimante'),
        ('reseau', 'Équipement réseau'),
        ('telephone', 'Téléphone IP'),
        ('autre', 'Autre'),
    ], string='Catégorie', required=True, default='poste_travail', tracking=True)

    marque = fields.Char(string='Marque')
    modele = fields.Char(string='Modèle')
    numero_serie = fields.Char(string='Numéro de série', tracking=True)

    # ──────────────────────────────────────────────
    # Champs financiers & garantie
    # ──────────────────────────────────────────────
    valeur_achat = fields.Float(string='Valeur d\'achat (FCFA)', digits=(16, 0))
    date_achat = fields.Date(string='Date d\'achat')
    date_garantie = fields.Date(string='Fin de garantie', tracking=True)

    garantie_expire = fields.Boolean(
        string='Garantie expirée',
        compute='_compute_garantie',
        store=True,
    )
    jours_garantie = fields.Integer(
        string='Jours restants garantie',
        compute='_compute_garantie',
        store=True,
    )

    # ──────────────────────────────────────────────
    # Affectation & localisation
    # ──────────────────────────────────────────────
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employé affecté',
        tracking=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Département',
        tracking=True,
    )
    localisation = fields.Char(string='Localisation / Site', tracking=True)

    # ──────────────────────────────────────────────
    # Workflow état
    # ──────────────────────────────────────────────
    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('affecte', 'Affecté'),
        ('en_maintenance', 'En maintenance'),
        ('retire', 'Retiré'),
    ], string='État', default='brouillon', tracking=True)

    # ──────────────────────────────────────────────
    # Relations
    # ──────────────────────────────────────────────
    affectation_ids = fields.One2many(
        'it.affectation', 'equipement_id',
        string='Historique des affectations',
    )
    intervention_ids = fields.One2many(
        'it.intervention', 'equipement_id',
        string='Interventions',
    )
    contrat_ids = fields.Many2many(
        'it.contrat',
        'it_contrat_equipement_rel',
        'equipement_id', 'contrat_id',
        string='Contrats fournisseurs',
    )
    alerte_ids = fields.One2many(
        'it.alerte', 'equipement_id',
        string='Alertes',
    )

    # ──────────────────────────────────────────────
    # Statistiques calculées
    # ──────────────────────────────────────────────
    nb_interventions = fields.Integer(
        string='Nb interventions',
        compute='_compute_stats',
        store=True,
    )
    cout_total_maintenance = fields.Float(
        string='Coût total maintenance (FCFA)',
        compute='_compute_stats',
        store=True,
        digits=(16, 0),
    )
    nb_alertes_actives = fields.Integer(
        string='Alertes actives',
        compute='_compute_nb_alertes',
    )

    note = fields.Html(string='Notes internes')

    # ──────────────────────────────────────────────
    # Séquence automatique
    # ──────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'Nouveau') == 'Nouveau':
                vals['reference'] = (
                    self.env['ir.sequence'].next_by_code('it.equipement') or 'Nouveau'
                )
        return super().create(vals_list)

    # ──────────────────────────────────────────────
    # Computed fields
    # ──────────────────────────────────────────────
    @api.depends('date_garantie')
    def _compute_garantie(self):
        today = fields.Date.today()
        for rec in self:
            if rec.date_garantie:
                delta = (rec.date_garantie - today).days
                rec.jours_garantie = delta
                rec.garantie_expire = delta < 0
            else:
                rec.jours_garantie = 0
                rec.garantie_expire = False

    @api.depends('intervention_ids', 'intervention_ids.cout')
    def _compute_stats(self):
        for rec in self:
            rec.nb_interventions = len(rec.intervention_ids)
            rec.cout_total_maintenance = sum(rec.intervention_ids.mapped('cout'))

    def _compute_nb_alertes(self):
        for rec in self:
            rec.nb_alertes_actives = self.env['it.alerte'].search_count([
                ('equipement_id', '=', rec.id),
                ('state', '=', 'nouvelle'),
            ])

    # ──────────────────────────────────────────────
    # Transitions de workflow
    # ──────────────────────────────────────────────
    def action_affecter(self):
        for rec in self:
            if not rec.employee_id:
                raise UserError(
                    "Veuillez renseigner un employé avant d'affecter l'équipement."
                )
            rec.state = 'affecte'

    def action_mettre_maintenance(self):
        self.write({'state': 'en_maintenance'})

    def action_retirer(self):
        self.write({'state': 'retire'})

    def action_remettre_brouillon(self):
        self.write({'state': 'brouillon'})

    # ──────────────────────────────────────────────
    # Actions
    # ──────────────────────────────────────────────
    def action_ouvrir_reaffectation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Réaffecter l\'équipement',
            'res_model': 'wizard.reaffectation',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_equipement_id': self.id,
                'default_employee_id': self.employee_id.id,
                'default_department_id': self.department_id.id,
            },
        }

    def action_voir_interventions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Interventions – {self.name}',
            'res_model': 'it.intervention',
            'view_mode': 'list,form',
            'domain': [('equipement_id', '=', self.id)],
        }

    def action_voir_alertes(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Alertes – {self.name}',
            'res_model': 'it.alerte',
            'view_mode': 'list,form',
            'domain': [('equipement_id', '=', self.id)],
        }

    # ──────────────────────────────────────────────
    # Données pour le dashboard OWL
    # ──────────────────────────────────────────────
    @api.model
    def get_dashboard_data(self):
        from datetime import date, timedelta
        today = date.today()
        in_30_days = today + timedelta(days=30)

        Equipement = self.env['it.equipement']
        Alerte = self.env['it.alerte']
        Contrat = self.env['it.contrat']

        total = Equipement.search_count([])
        affectes = Equipement.search_count([('state', '=', 'affecte')])
        en_maintenance = Equipement.search_count([('state', '=', 'en_maintenance')])
        retires = Equipement.search_count([('state', '=', 'retire')])
        alertes_actives = Alerte.search_count([('state', '=', 'nouvelle')])
        contrats_expirants = Contrat.search_count([
            ('date_fin', '<=', str(in_30_days)),
            ('state', '=', 'actif'),
        ])

        # Répartition par catégorie
        cat_selection = dict(Equipement._fields['categorie'].selection)
        by_categorie = []
        for key, label in cat_selection.items():
            count = Equipement.search_count([('categorie', '=', key)])
            if count:
                by_categorie.append({'key': key, 'label': label, 'count': count})

        # Répartition par état
        state_selection = dict(Equipement._fields['state'].selection)
        by_state = []
        for key, label in state_selection.items():
            count = Equipement.search_count([('state', '=', key)])
            by_state.append({'key': key, 'label': label, 'count': count})

        return {
            'total_equipements': total,
            'affectes': affectes,
            'en_maintenance': en_maintenance,
            'retires': retires,
            'alertes_actives': alertes_actives,
            'contrats_expirants': contrats_expirants,
            'by_categorie': by_categorie,
            'by_state': by_state,
        }
