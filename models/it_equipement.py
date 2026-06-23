# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class ItEquipement(models.Model):
    _name = 'it.equipement'
    _description = 'Équipement informatique'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'reference desc'

    name = fields.Char(string='Désignation', required=True, tracking=True)
    reference = fields.Char(string='Référence', readonly=True, copy=False, default='Nouveau')
    categorie = fields.Selection([
        ('ordinateur', 'Ordinateur fixe'),
        ('portable', 'Ordinateur portable'),
        ('serveur', 'Serveur'),
        ('imprimante', 'Imprimante'),
        ('reseau', 'Équipement réseau'),
        ('telephone_ip', 'Téléphone IP'),
        ('autre', 'Autre'),
    ], string='Catégorie', required=True, tracking=True)
    marque = fields.Char(string='Marque')
    modele = fields.Char(string='Modèle')
    numero_serie = fields.Char(string='Numéro de série', copy=False)
    date_achat = fields.Date(string="Date d'achat")
    date_fin_garantie = fields.Date(string='Fin de garantie', tracking=True)
    valeur_achat = fields.Float(string="Valeur d'achat (FCFA)", digits=(16, 0))
    fournisseur_id = fields.Many2one('res.partner', string='Fournisseur')
    localisation = fields.Char(string='Localisation / Site')
    notes = fields.Text(string='Notes techniques')

    employee_id = fields.Many2one('hr.employee', string='Employé affecté', tracking=True)
    department_id = fields.Many2one('hr.department', string='Département', tracking=True)

    etat = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('affecte', 'Affecté'),
        ('en_maintenance', 'En maintenance'),
        ('retire', 'Retiré'),
    ], string='État', default='brouillon', required=True, tracking=True)

    affectation_ids = fields.One2many('it.affectation', 'equipement_id', string='Historique affectations')
    intervention_ids = fields.One2many('it.intervention', 'equipement_id', string='Interventions')
    contrat_ids = fields.Many2many(
        'it.contrat', 'it_equipement_contrat_rel', 'equipement_id', 'contrat_id',
        string='Contrats de maintenance'
    )
    alerte_ids = fields.One2many('it.alerte', 'equipement_id', string='Alertes')

    nb_interventions = fields.Integer(
        string='Nb interventions', compute='_compute_stats', store=True)
    cout_total_maintenance = fields.Float(
        string='Coût total maintenance (FCFA)', compute='_compute_stats', store=True, digits=(16, 0))
    garantie_expiree = fields.Boolean(
        string='Garantie expirée', compute='_compute_garantie', store=True)
    jours_avant_fin_garantie = fields.Integer(
        string='Jours avant fin garantie', compute='_compute_garantie', store=True)

    @api.depends('intervention_ids', 'intervention_ids.cout', 'intervention_ids.etat')
    def _compute_stats(self):
        for rec in self:
            interventions = rec.intervention_ids.filtered(lambda i: i.etat == 'termine')
            rec.nb_interventions = len(rec.intervention_ids)
            rec.cout_total_maintenance = sum(interventions.mapped('cout'))

    @api.depends('date_fin_garantie')
    def _compute_garantie(self):
        today = date.today()
        for rec in self:
            if rec.date_fin_garantie:
                delta = (rec.date_fin_garantie - today).days
                rec.jours_avant_fin_garantie = delta
                rec.garantie_expiree = delta < 0
            else:
                rec.jours_avant_fin_garantie = 0
                rec.garantie_expiree = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'Nouveau') == 'Nouveau':
                vals['reference'] = self.env['ir.sequence'].next_by_code('it.equipement') or 'Nouveau'
        return super().create(vals_list)

    @api.constrains('date_achat', 'date_fin_garantie')
    def _check_dates(self):
        for rec in self:
            if rec.date_achat and rec.date_fin_garantie and rec.date_fin_garantie < rec.date_achat:
                raise ValidationError(_("La fin de garantie ne peut pas être antérieure à la date d'achat."))

    @api.constrains('numero_serie')
    def _check_serie_unique(self):
        for rec in self:
            if rec.numero_serie:
                duplicate = self.search([
                    ('numero_serie', '=', rec.numero_serie),
                    ('id', '!=', rec.id),
                ])
                if duplicate:
                    raise ValidationError(
                        _("Le numéro de série '%s' est déjà utilisé par '%s'.") % (rec.numero_serie, duplicate[0].name)
                    )

    def action_affecter(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Affecter / Réaffecter'),
            'res_model': 'wizard.reaffectation',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_equipement_id': self.id},
        }

    def action_mettre_en_maintenance(self):
        for rec in self:
            rec.etat = 'en_maintenance'

    def action_retirer(self):
        for rec in self:
            rec.etat = 'retire'

    def action_remettre_en_service(self):
        for rec in self:
            rec.etat = 'affecte' if rec.employee_id else 'brouillon'

    def action_voir_interventions(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Interventions'),
            'res_model': 'it.intervention',
            'view_mode': 'list,form,calendar',
            'domain': [('equipement_id', '=', self.id)],
            'context': {'default_equipement_id': self.id},
        }

    @api.model
    def cron_generer_alertes(self):
        """Tâche planifiée : génère les alertes d'expiration."""
        jours = 30
        today = fields.Date.today()
        from datetime import timedelta
        seuil = today + timedelta(days=jours)

        # Alertes garantie
        equipements = self.search([
            ('date_fin_garantie', '!=', False),
            ('date_fin_garantie', '<=', seuil),
            ('etat', 'not in', ['retire']),
        ])
        Alerte = self.env['it.alerte']
        for equip in equipements:
            existe = Alerte.search([
                ('equipement_id', '=', equip.id),
                ('type_alerte', '=', 'garantie'),
                ('etat', '=', 'actif'),
            ], limit=1)
            if not existe:
                Alerte.create({
                    'name': _("Fin de garantie — %s") % equip.name,
                    'type_alerte': 'garantie',
                    'equipement_id': equip.id,
                    'date_echeance': equip.date_fin_garantie,
                    'message': _(
                        "La garantie de l'équipement '%s' (réf. %s) expire le %s."
                    ) % (equip.name, equip.reference, equip.date_fin_garantie),
                })

    @api.model
    def get_dashboard_data(self):
        Inter = self.env['it.intervention']
        Alerte = self.env['it.alerte']

        total = self.search_count([])
        actifs = self.search_count([('etat', '=', 'affecte')])
        en_maintenance = self.search_count([('etat', '=', 'en_maintenance')])
        retires = self.search_count([('etat', '=', 'retire')])
        alertes_actives = Alerte.search_count([('etat', '=', 'actif')])

        par_categorie = []
        for code, label in self._fields['categorie'].selection:
            count = self.search_count([('categorie', '=', code)])
            if count:
                par_categorie.append({'code': code, 'label': label, 'count': count})
        par_categorie.sort(key=lambda x: -x['count'])

        today = fields.Date.today()
        premier_mois = today.replace(day=1)
        inter_mois = Inter.search([
            ('etat', '=', 'termine'),
            ('date_debut', '>=', str(premier_mois) + ' 00:00:00'),
        ])
        cout_mois = sum(inter_mois.mapped('cout'))

        return {
            'total': total,
            'actifs': actifs,
            'en_maintenance': en_maintenance,
            'retires': retires,
            'alertes_actives': alertes_actives,
            'cout_mois': cout_mois,
            'par_categorie': par_categorie,
        }
