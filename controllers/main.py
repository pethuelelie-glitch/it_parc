# -*- coding: utf-8 -*-
import io
from datetime import date, timedelta

from odoo import http
from odoo.http import request


class ItParcController(http.Controller):

    # ──────────────────────────────────────────────
    # Export 1 : Inventaire complet
    # ──────────────────────────────────────────────
    @http.route('/it_parc/export/inventaire', type='http', auth='user')
    def export_inventaire(self, **kwargs):
        try:
            import xlsxwriter
        except ImportError:
            return request.make_response(
                "xlsxwriter non installé. Lancez : pip install xlsxwriter",
                headers=[('Content-Type', 'text/plain')]
            )

        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = wb.add_worksheet('Inventaire')

        # Styles
        header_fmt = wb.add_format({
            'bold': True, 'bg_color': '#1565C0', 'font_color': 'white',
            'border': 1, 'align': 'center', 'valign': 'vcenter',
        })
        money_fmt = wb.add_format({'num_format': '#,##0', 'border': 1})
        cell_fmt = wb.add_format({'border': 1})
        date_fmt = wb.add_format({'num_format': 'dd/mm/yyyy', 'border': 1})
        red_fmt = wb.add_format({'bg_color': '#FFCDD2', 'border': 1})
        green_fmt = wb.add_format({'bg_color': '#C8E6C9', 'border': 1})

        headers = [
            ('Référence', 15), ('Nom équipement', 30), ('Catégorie', 18),
            ('Marque', 15), ('Modèle', 15), ('N° Série', 20),
            ('État', 15), ('Employé affecté', 25), ('Département', 20),
            ('Localisation', 18), ('Date achat', 14), ('Valeur achat (FCFA)', 20),
            ('Fin garantie', 14), ('Garantie OK?', 14),
            ('Nb interventions', 18), ('Coût maintenance (FCFA)', 22),
        ]
        for col, (h, w) in enumerate(headers):
            ws.write(0, col, h, header_fmt)
            ws.set_column(col, col, w)
        ws.set_row(0, 20)
        ws.freeze_panes(1, 0)

        Eq = request.env['it.equipement']
        cat_labels = dict(Eq._fields['categorie'].selection)
        st_labels = dict(Eq._fields['state'].selection)
        equipements = Eq.search([], order='reference')

        for row, eq in enumerate(equipements, start=1):
            ws.write(row, 0, eq.reference or '', cell_fmt)
            ws.write(row, 1, eq.name or '', cell_fmt)
            ws.write(row, 2, cat_labels.get(eq.categorie, '') or '', cell_fmt)
            ws.write(row, 3, eq.marque or '', cell_fmt)
            ws.write(row, 4, eq.modele or '', cell_fmt)
            ws.write(row, 5, eq.numero_serie or '', cell_fmt)
            ws.write(row, 6, st_labels.get(eq.state, '') or '', cell_fmt)
            ws.write(row, 7, eq.employee_id.name or '', cell_fmt)
            ws.write(row, 8, eq.department_id.name or '', cell_fmt)
            ws.write(row, 9, eq.localisation or '', cell_fmt)
            if eq.date_achat:
                ws.write_datetime(row, 10, eq.date_achat, date_fmt)
            else:
                ws.write(row, 10, '', cell_fmt)
            ws.write(row, 11, eq.valeur_achat or 0, money_fmt)
            if eq.date_garantie:
                ws.write_datetime(row, 12, eq.date_garantie, date_fmt)
            else:
                ws.write(row, 12, '', cell_fmt)
            garantie_ok = 'Non' if eq.garantie_expire else 'Oui'
            ws.write(row, 13, garantie_ok, red_fmt if eq.garantie_expire else green_fmt)
            ws.write(row, 14, eq.nb_interventions, cell_fmt)
            ws.write(row, 15, eq.cout_total_maintenance or 0, money_fmt)

        wb.close()
        output.seek(0)
        filename = f'inventaire_it_{date.today().strftime("%Y%m%d")}.xlsx'
        return request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename="{filename}"'),
            ],
        )

    # ──────────────────────────────────────────────
    # Export 2 : Synthèse coûts de maintenance
    #   Feuille 1 : Total par équipement
    #   Feuille 2 : Pivot mensuel (12 derniers mois)
    # ──────────────────────────────────────────────
    @http.route('/it_parc/export/couts_maintenance', type='http', auth='user')
    def export_couts_maintenance(self, **kwargs):
        try:
            import xlsxwriter
        except ImportError:
            return request.make_response(
                "xlsxwriter non installé.",
                headers=[('Content-Type', 'text/plain')]
            )

        from collections import defaultdict
        from datetime import date

        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})

        # ── Styles ──────────────────────────────────
        def hdr(bg='#1B5E20'):
            return wb.add_format({
                'bold': True, 'bg_color': bg, 'font_color': 'white',
                'border': 1, 'align': 'center', 'valign': 'vcenter',
            })
        money_fmt = wb.add_format({'num_format': '#,##0', 'border': 1})
        cell_fmt  = wb.add_format({'border': 1})
        int_fmt   = wb.add_format({'num_format': '0', 'border': 1, 'align': 'center'})
        total_fmt = wb.add_format({'bold': True, 'bg_color': '#E8F5E9', 'border': 1, 'num_format': '#,##0'})
        zero_fmt  = wb.add_format({'font_color': '#cccccc', 'border': 1, 'num_format': '#,##0', 'align': 'center'})

        Eq   = request.env['it.equipement']
        cat_labels = dict(Eq._fields['categorie'].selection)
        equipements = Eq.search([], order='cout_total_maintenance desc')

        # ════════════════════════════════════════════
        # FEUILLE 1 : Résumé par équipement
        # ════════════════════════════════════════════
        ws1 = wb.add_worksheet('Par équipement')
        headers1 = [
            ('Référence', 15), ('Équipement', 30), ('Catégorie', 18),
            ('Nb Interventions', 18), ('Coût Total (FCFA)', 22),
            ('Coût Moyen/Intervention (FCFA)', 30),
        ]
        for col, (h, w) in enumerate(headers1):
            ws1.write(0, col, h, hdr())
            ws1.set_column(col, col, w)
        ws1.set_row(0, 22)
        ws1.freeze_panes(1, 0)

        total_cout = 0
        for row, eq in enumerate(equipements, start=1):
            nb   = eq.nb_interventions
            cout = eq.cout_total_maintenance or 0
            total_cout += cout
            ws1.write(row, 0, eq.reference or '', cell_fmt)
            ws1.write(row, 1, eq.name or '', cell_fmt)
            ws1.write(row, 2, cat_labels.get(eq.categorie, '') or '', cell_fmt)
            ws1.write(row, 3, nb, int_fmt)
            ws1.write(row, 4, cout, money_fmt)
            ws1.write(row, 5, (cout / nb) if nb else 0, money_fmt)

        total_row = len(equipements) + 1
        ws1.write(total_row, 3, 'TOTAL', wb.add_format({'bold': True, 'border': 1}))
        ws1.write(total_row, 4, total_cout, total_fmt)

        # ════════════════════════════════════════════
        # FEUILLE 2 : Pivot mensuel — 12 derniers mois
        # ════════════════════════════════════════════
        ws2 = wb.add_worksheet('Par mois (12 derniers mois)')

        today = date.today()
        # Calculer les 12 derniers mois (y inclus le mois courant)
        months = []
        for i in range(11, -1, -1):
            m = today.month - i
            y = today.year
            while m <= 0:
                m += 12
                y -= 1
            months.append((y, m))
        month_labels = [f"{y}/{str(m).zfill(2)}" for y, m in months]

        # Requête : toutes les interventions sur les 12 derniers mois
        first_month_start = date(months[0][0], months[0][1], 1)
        Intervention = request.env['it.intervention']
        interventions = Intervention.search([
            ('date_debut', '>=', str(first_month_start)),
            ('state', '!=', 'annule'),
        ])

        # Pivot : {eq_id: {(y,m): cout}}
        pivot = defaultdict(lambda: defaultdict(float))
        total_par_mois = defaultdict(float)
        for interv in interventions:
            if interv.date_debut:
                key = (interv.date_debut.year, interv.date_debut.month)
                pivot[interv.equipement_id.id][key] += interv.cout or 0
                total_par_mois[key] += interv.cout or 0

        # En-têtes feuille 2
        ws2.write(0, 0, 'Référence', hdr('#1565C0'))
        ws2.write(0, 1, 'Équipement', hdr('#1565C0'))
        ws2.set_column(0, 0, 14)
        ws2.set_column(1, 1, 28)
        for col_idx, lbl in enumerate(month_labels, start=2):
            ws2.write(0, col_idx, lbl, hdr('#1565C0'))
            ws2.set_column(col_idx, col_idx, 14)
        ws2.write(0, len(months) + 2, 'Total 12 mois', hdr('#B71C1C'))
        ws2.set_column(len(months) + 2, len(months) + 2, 16)
        ws2.set_row(0, 22)
        ws2.freeze_panes(1, 2)

        # Lignes équipements
        eq_with_data = [eq for eq in equipements if eq.id in pivot]
        for row, eq in enumerate(eq_with_data, start=1):
            ws2.write(row, 0, eq.reference or '', cell_fmt)
            ws2.write(row, 1, eq.name or '', cell_fmt)
            total_eq = 0
            for col_idx, (y, m) in enumerate(months, start=2):
                val = pivot[eq.id].get((y, m), 0)
                total_eq += val
                if val:
                    ws2.write(row, col_idx, val, money_fmt)
                else:
                    ws2.write(row, col_idx, '—', zero_fmt)
            ws2.write(row, len(months) + 2, total_eq, money_fmt)

        # Ligne totaux par mois
        total_row2 = len(eq_with_data) + 1
        ws2.write(total_row2, 1, 'TOTAL MENSUEL', wb.add_format({'bold': True, 'border': 1}))
        grand_total = 0
        for col_idx, (y, m) in enumerate(months, start=2):
            val = total_par_mois.get((y, m), 0)
            grand_total += val
            ws2.write(total_row2, col_idx, val, total_fmt)
        ws2.write(total_row2, len(months) + 2, grand_total, total_fmt)

        wb.close()
        output.seek(0)
        filename = f'couts_maintenance_{date.today().strftime("%Y%m%d")}.xlsx'
        return request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename="{filename}"'),
            ],
        )

    # ──────────────────────────────────────────────
    # Export 3 : Contrats expirant dans 60 jours
    # ──────────────────────────────────────────────
    @http.route('/it_parc/export/contrats_expirants', type='http', auth='user')
    def export_contrats_expirants(self, **kwargs):
        try:
            import xlsxwriter
        except ImportError:
            return request.make_response(
                "xlsxwriter non installé.",
                headers=[('Content-Type', 'text/plain')]
            )

        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = wb.add_worksheet('Contrats Expirants 60j')

        header_fmt = wb.add_format({
            'bold': True, 'bg_color': '#B71C1C', 'font_color': 'white',
            'border': 1, 'align': 'center',
        })
        cell_fmt = wb.add_format({'border': 1})
        money_fmt = wb.add_format({'num_format': '#,##0', 'border': 1})
        date_fmt = wb.add_format({'num_format': 'dd/mm/yyyy', 'border': 1})
        int_fmt = wb.add_format({'num_format': '0', 'border': 1, 'align': 'center'})
        red_fmt = wb.add_format({'bg_color': '#FFCDD2', 'border': 1})
        orange_fmt = wb.add_format({'bg_color': '#FFE0B2', 'border': 1})

        headers = [
            ('Référence contrat', 25), ('Fournisseur', 25), ('Type', 20),
            ('Date début', 14), ('Date expiration', 14),
            ('Jours restants', 15), ('Montant (FCFA)', 18),
            ('État', 12), ('Équipements couverts', 30),
        ]
        for col, (h, w) in enumerate(headers):
            ws.write(0, col, h, header_fmt)
            ws.set_column(col, col, w)
        ws.freeze_panes(1, 0)

        Contrat = request.env['it.contrat']
        type_labels = dict(Contrat._fields['type_contrat'].selection)
        state_labels = dict(Contrat._fields['state'].selection)

        limite = date.today() + timedelta(days=60)
        contrats = Contrat.search([
            ('date_fin', '<=', str(limite)),
        ], order='date_fin asc')

        for row, c in enumerate(contrats, start=1):
            jours = c.jours_restants
            if jours < 0:
                row_fmt = red_fmt
            elif jours <= 30:
                row_fmt = orange_fmt
            else:
                row_fmt = cell_fmt

            ws.write(row, 0, c.name or '', row_fmt)
            ws.write(row, 1, c.fournisseur_id.name or '', row_fmt)
            ws.write(row, 2, type_labels.get(c.type_contrat, '') or '', row_fmt)
            if c.date_debut:
                ws.write_datetime(row, 3, c.date_debut, date_fmt)
            else:
                ws.write(row, 3, '', row_fmt)
            if c.date_fin:
                ws.write_datetime(row, 4, c.date_fin, date_fmt)
            else:
                ws.write(row, 4, '', row_fmt)
            ws.write(row, 5, jours, int_fmt)
            ws.write(row, 6, c.montant or 0, money_fmt)
            ws.write(row, 7, state_labels.get(c.state, '') or '', row_fmt)
            equipements = ', '.join(c.equipement_ids.mapped('name'))
            ws.write(row, 8, equipements or '', row_fmt)

        wb.close()
        output.seek(0)
        filename = f'contrats_expirants_{date.today().strftime("%Y%m%d")}.xlsx'
        return request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename="{filename}"'),
            ],
        )
