# -*- coding: utf-8 -*-
import base64
import csv
import io
from datetime import datetime

from odoo import fields, models
from odoo.exceptions import UserError


class WizardImportCsv(models.TransientModel):
    _name = 'wizard.import.csv'
    _description = 'Import en masse d\'équipements via CSV'

    fichier_csv = fields.Binary(string='Fichier CSV', required=True)
    fichier_nom = fields.Char(string='Nom du fichier')
    separateur = fields.Selection([
        (';', 'Point-virgule ( ; )'),
        (',', 'Virgule ( , )'),
        ('\t', 'Tabulation'),
    ], string='Séparateur', default=';', required=True)

    # Résultats
    resultat_html = fields.Html(string='Rapport d\'import', readonly=True)
    nb_crees = fields.Integer(string='Lignes créées', readonly=True)
    nb_ignores = fields.Integer(string='Doublons ignorés', readonly=True)
    nb_erreurs = fields.Integer(string='Erreurs', readonly=True)
    import_fait = fields.Boolean(default=False)

    def action_importer(self):
        self.ensure_one()
        if not self.fichier_csv:
            raise UserError("Veuillez sélectionner un fichier CSV.")

        # Décodage du fichier
        try:
            content = base64.b64decode(self.fichier_csv).decode('utf-8-sig')
        except Exception:
            raise UserError(
                "Impossible de lire le fichier. Vérifiez l'encodage (UTF-8 recommandé)."
            )

        reader = csv.DictReader(
            io.StringIO(content),
            delimiter=self.separateur,
        )

        crees = 0
        ignores = 0
        lignes_resultat = []
        erreurs_count = 0

        CATEGORIES_VALIDES = {
            'poste_travail', 'serveur', 'imprimante',
            'reseau', 'telephone', 'autre',
        }

        for i, row in enumerate(reader, start=2):
            nom = (row.get('name') or row.get('nom') or '').strip()
            num_serie = (row.get('numero_serie') or row.get('serial') or '').strip()

            if not nom:
                lignes_resultat.append(
                    f'<tr class="table-danger"><td>{i}</td><td>—</td>'
                    f'<td>{num_serie}</td><td>❌ Nom manquant</td></tr>'
                )
                erreurs_count += 1
                continue

            # Détection doublon par numéro de série
            if num_serie:
                existing = self.env['it.equipement'].search(
                    [('numero_serie', '=', num_serie)], limit=1
                )
                if existing:
                    lignes_resultat.append(
                        f'<tr class="table-warning"><td>{i}</td><td>{nom}</td>'
                        f'<td>{num_serie}</td><td>⚠️ Doublon ignoré (réf. {existing.reference})</td></tr>'
                    )
                    ignores += 1
                    continue

            try:
                categorie = (row.get('categorie') or 'autre').strip().lower()
                if categorie not in CATEGORIES_VALIDES:
                    categorie = 'autre'

                vals = {
                    'name': nom,
                    'numero_serie': num_serie or False,
                    'categorie': categorie,
                    'marque': (row.get('marque') or '').strip() or False,
                    'modele': (row.get('modele') or '').strip() or False,
                    'localisation': (row.get('localisation') or '').strip() or False,
                }

                # Date d'achat
                raw_achat = (row.get('date_achat') or '').strip()
                if raw_achat:
                    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
                        try:
                            vals['date_achat'] = datetime.strptime(raw_achat, fmt).date()
                            break
                        except ValueError:
                            continue

                # Date garantie
                raw_garantie = (row.get('date_garantie') or '').strip()
                if raw_garantie:
                    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
                        try:
                            vals['date_garantie'] = datetime.strptime(raw_garantie, fmt).date()
                            break
                        except ValueError:
                            continue

                # Valeur d'achat
                raw_valeur = (row.get('valeur_achat') or '').strip()
                if raw_valeur:
                    try:
                        vals['valeur_achat'] = float(
                            raw_valeur.replace('\xa0', '').replace(' ', '').replace(',', '.')
                        )
                    except ValueError:
                        pass

                self.env['it.equipement'].create(vals)
                crees += 1
                lignes_resultat.append(
                    f'<tr class="table-success"><td>{i}</td><td>{nom}</td>'
                    f'<td>{num_serie or "—"}</td><td>✅ Créé</td></tr>'
                )

            except Exception as e:
                lignes_resultat.append(
                    f'<tr class="table-danger"><td>{i}</td><td>{nom}</td>'
                    f'<td>{num_serie or "—"}</td><td>❌ Erreur : {str(e)[:120]}</td></tr>'
                )
                erreurs_count += 1

        # Construction du rapport HTML
        badge_crees = f'<span class="badge bg-success">{crees} créés</span>'
        badge_ignores = f'<span class="badge bg-warning text-dark">{ignores} doublons</span>'
        badge_erreurs = f'<span class="badge bg-danger">{erreurs_count} erreurs</span>'

        html = f"""
        <div>
            <div class="alert alert-info mb-3">
                <strong>Résultat de l'import :</strong>&nbsp;
                {badge_crees}&nbsp;{badge_ignores}&nbsp;{badge_erreurs}
            </div>
            <table class="table table-sm table-bordered table-hover">
                <thead class="table-dark">
                    <tr>
                        <th>Ligne</th><th>Nom</th><th>N° Série</th><th>Résultat</th>
                    </tr>
                </thead>
                <tbody>{''.join(lignes_resultat) or '<tr><td colspan="4" class="text-center text-muted">Aucune ligne traitée</td></tr>'}</tbody>
            </table>
        </div>
        """

        self.write({
            'nb_crees': crees,
            'nb_ignores': ignores,
            'nb_erreurs': erreurs_count,
            'resultat_html': html,
            'import_fait': True,
        })

        # Retourner la vue mise à jour avec le rapport
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self.env.context),
        }
