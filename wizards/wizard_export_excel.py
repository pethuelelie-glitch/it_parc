# -*- coding: utf-8 -*-
import base64
import io
from odoo import models, fields, _
from odoo.exceptions import UserError


class WizardExportExcel(models.TransientModel):
    _name = 'wizard.export.excel'
    _description = 'Export Excel du parc informatique'

    type_export = fields.Selection([
        ('inventaire', 'Inventaire complet'),
        ('couts_maintenance', 'Coûts de maintenance'),
        ('contrats_expiration', 'Contrats expirant dans 60 jours'),
    ], string="Type d'export", required=True, default='inventaire')
    date_debut = fields.Date(string='Date début (coûts)')
    date_fin = fields.Date(string='Date fin (coûts)')
    file_data = fields.Binary(string='Fichier Excel', readonly=True)
    file_name = fields.Char(string='Nom du fichier', readonly=True)
    genere = fields.Boolean(default=False)

    def _get_workbook(self):
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_("La bibliothèque xlsxwriter n'est pas installée.\nExécutez: pip install xlsxwriter"))
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        return workbook, output

    def _fmt(self, wb, bold=False, bg=None, color=None, border=False, align='left', num_format=None):
        props = {'align': align, 'valign': 'vcenter'}
        if bold:
            props['bold'] = True
        if bg:
            props['bg_color'] = bg
        if color:
            props['font_color'] = color
        if border:
            props['border'] = 1
        if num_format:
            props['num_format'] = num_format
        return wb.add_format(props)

    def action_generer(self):
        self.ensure_one()
        if self.type_export == 'inventaire':
            return self._export_inventaire()
        elif self.type_export == 'couts_maintenance':
            return self._export_couts()
        elif self.type_export == 'contrats_expiration':
            return self._export_contrats()

    def _export_inventaire(self):
        wb, output = self._get_workbook()
        ws = wb.add_worksheet('Inventaire')
        entete = self._fmt(wb, bold=True, bg='#1F4E79', color='white', border=True)
        normal = self._fmt(wb, border=True)
        warning = self._fmt(wb, bg='#FFF2CC', border=True)
        danger = self._fmt(wb, bg='#FFE0E0', border=True)
        money = self._fmt(wb, border=True, num_format='#,##0')

        headers = ['Référence', 'Désignation', 'Catégorie', 'Marque', 'Modèle',
                   'N° Série', 'Date achat', 'Fin garantie', 'Valeur (FCFA)',
                   'Fournisseur', 'Employé affecté', 'Département', 'Localisation', 'État']
        col_widths = [14, 28, 16, 14, 14, 18, 13, 13, 16, 22, 22, 18, 18, 14]
        for col, (h, w) in enumerate(zip(headers, col_widths)):
            ws.write(0, col, h, entete)
            ws.set_column(col, col, w)
        ws.freeze_panes(1, 0)

        equipements = self.env['it.equipement'].search([])
        for row, equip in enumerate(equipements, start=1):
            fmt = danger if equip.etat == 'retire' else (warning if equip.garantie_expiree else normal)
            data = [
                equip.reference or '',
                equip.name or '',
                dict(self.env['it.equipement']._fields['categorie'].selection).get(equip.categorie, ''),
                equip.marque or '',
                equip.modele or '',
                equip.numero_serie or '',
                str(equip.date_achat) if equip.date_achat else '',
                str(equip.date_fin_garantie) if equip.date_fin_garantie else '',
                equip.valeur_achat,
                equip.fournisseur_id.name if equip.fournisseur_id else '',
                equip.employee_id.name if equip.employee_id else '',
                equip.department_id.name if equip.department_id else '',
                equip.localisation or '',
                dict(self.env['it.equipement']._fields['etat'].selection).get(equip.etat, ''),
            ]
            for col, val in enumerate(data):
                if col == 8:
                    ws.write_number(row, col, val, money)
                else:
                    ws.write(row, col, val, fmt)

        wb.close()
        output.seek(0)
        self.write({
            'file_data': base64.b64encode(output.read()),
            'file_name': 'inventaire_it_parc.xlsx',
            'genere': True,
        })
        return self._return_form()

    def _export_couts(self):
        wb, output = self._get_workbook()
        ws = wb.add_worksheet('Coûts maintenance')
        entete = self._fmt(wb, bold=True, bg='#1F4E79', color='white', border=True)
        normal = self._fmt(wb, border=True)
        money = self._fmt(wb, border=True, num_format='#,##0')

        headers = ['Équipement', 'Référence', 'Catégorie', 'Mois', 'Nb interventions', 'Coût total (FCFA)']
        col_widths = [28, 14, 16, 12, 18, 20]
        for col, (h, w) in enumerate(zip(headers, col_widths)):
            ws.write(0, col, h, entete)
            ws.set_column(col, col, w)

        domain = [('etat', '=', 'termine')]
        if self.date_debut:
            domain.append(('date_debut', '>=', str(self.date_debut) + ' 00:00:00'))
        if self.date_fin:
            domain.append(('date_debut', '<=', str(self.date_fin) + ' 23:59:59'))

        interventions = self.env['it.intervention'].search(domain, order='equipement_id, date_debut')
        from collections import defaultdict
        data = defaultdict(lambda: defaultdict(lambda: {'nb': 0, 'cout': 0.0}))
        for inter in interventions:
            mois = inter.date_debut.strftime('%Y-%m') if inter.date_debut else 'N/A'
            key = inter.equipement_id
            data[key][mois]['nb'] += 1
            data[key][mois]['cout'] += inter.cout

        row = 1
        for equip, mois_data in sorted(data.items(), key=lambda x: x[0].name):
            for mois, stats in sorted(mois_data.items()):
                ws.write(row, 0, equip.name or '', normal)
                ws.write(row, 1, equip.reference or '', normal)
                cat_label = dict(self.env['it.equipement']._fields['categorie'].selection).get(equip.categorie, '')
                ws.write(row, 2, cat_label, normal)
                ws.write(row, 3, mois, normal)
                ws.write_number(row, 4, stats['nb'], normal)
                ws.write_number(row, 5, stats['cout'], money)
                row += 1

        wb.close()
        output.seek(0)
        self.write({
            'file_data': base64.b64encode(output.read()),
            'file_name': 'couts_maintenance_it_parc.xlsx',
            'genere': True,
        })
        return self._return_form()

    def _export_contrats(self):
        wb, output = self._get_workbook()
        ws = wb.add_worksheet('Contrats expiration')
        entete = self._fmt(wb, bold=True, bg='#1F4E79', color='white', border=True)
        normal = self._fmt(wb, border=True)
        orange = self._fmt(wb, bg='#FFF2CC', border=True)
        rouge = self._fmt(wb, bg='#FFE0E0', border=True)
        money = self._fmt(wb, border=True, num_format='#,##0')

        headers = ['Référence', 'Intitulé', 'Type', 'Fournisseur',
                   'Date fin', 'Jours restants', 'Montant (FCFA)', 'État']
        col_widths = [14, 28, 16, 22, 13, 15, 18, 12]
        for col, (h, w) in enumerate(zip(headers, col_widths)):
            ws.write(0, col, h, entete)
            ws.set_column(col, col, w)

        from datetime import date, timedelta
        today = date.today()
        seuil = today + timedelta(days=60)
        contrats = self.env['it.contrat'].search([
            ('etat', 'in', ['actif', 'expire']),
            ('date_fin', '<=', str(seuil)),
        ], order='date_fin')

        for row, contrat in enumerate(contrats, start=1):
            jours = contrat.jours_restants
            fmt = rouge if jours < 0 else (orange if jours <= 15 else normal)
            type_label = dict(self.env['it.contrat']._fields['type_contrat'].selection).get(contrat.type_contrat, '')
            etat_label = dict(self.env['it.contrat']._fields['etat'].selection).get(contrat.etat, '')
            ws.write(row, 0, contrat.reference or '', fmt)
            ws.write(row, 1, contrat.name or '', fmt)
            ws.write(row, 2, type_label, fmt)
            ws.write(row, 3, contrat.fournisseur_id.name if contrat.fournisseur_id else '', fmt)
            ws.write(row, 4, str(contrat.date_fin) if contrat.date_fin else '', fmt)
            ws.write_number(row, 5, jours, fmt)
            ws.write_number(row, 6, contrat.montant, money)
            ws.write(row, 7, etat_label, fmt)

        wb.close()
        output.seek(0)
        self.write({
            'file_data': base64.b64encode(output.read()),
            'file_name': 'contrats_expiration_it_parc.xlsx',
            'genere': True,
        })
        return self._return_form()

    def _return_form(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.export.excel',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
