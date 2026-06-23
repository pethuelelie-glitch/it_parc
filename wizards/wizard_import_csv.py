# -*- coding: utf-8 -*-
import base64
import csv
import io
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class WizardImportCsv(models.TransientModel):
    _name = 'wizard.import.csv'
    _description = 'Import en masse par CSV'

    fichier_csv = fields.Binary(string='Fichier CSV', required=True)
    nom_fichier = fields.Char(string='Nom du fichier')
    separateur = fields.Selection([
        (';', 'Point-virgule (;)'),
        (',', 'Virgule (,)'),
        ('\t', 'Tabulation'),
    ], string='Séparateur', default=';', required=True)

    nb_crees = fields.Integer(string='Créés', readonly=True)
    nb_ignores = fields.Integer(string='Ignorés (doublons)', readonly=True)
    nb_erreurs = fields.Integer(string='Erreurs', readonly=True)
    rapport = fields.Text(string='Rapport détaillé', readonly=True)
    traite = fields.Boolean(default=False)

    def action_importer(self):
        self.ensure_one()
        try:
            contenu = base64.b64decode(self.fichier_csv).decode('utf-8-sig')
        except Exception:
            raise UserError(_("Impossible de lire le fichier. Assurez-vous qu'il est encodé en UTF-8."))

        reader = csv.DictReader(io.StringIO(contenu), delimiter=self.separateur)
        categories_valides = [c[0] for c in self.env['it.equipement']._fields['categorie'].selection]

        crees, ignores, erreurs = 0, 0, []

        for i, row in enumerate(reader, start=2):
            row = {k.strip(): (v.strip() if v else '') for k, v in row.items() if k}

            # Champs obligatoires
            if not row.get('name') or not row.get('categorie'):
                erreurs.append(f"Ligne {i}: 'name' et 'categorie' sont obligatoires.")
                continue

            if row['categorie'] not in categories_valides:
                erreurs.append(
                    f"Ligne {i}: catégorie '{row['categorie']}' invalide. "
                    f"Valeurs acceptées: {', '.join(categories_valides)}"
                )
                continue

            # Détection doublon par numéro de série
            if row.get('numero_serie'):
                existant = self.env['it.equipement'].search(
                    [('numero_serie', '=', row['numero_serie'])], limit=1
                )
                if existant:
                    ignores += 1
                    erreurs.append(
                        f"Ligne {i}: doublon ignoré — n° de série '{row['numero_serie']}' "
                        f"déjà utilisé par '{existant.name}'."
                    )
                    continue

            vals = {
                'name': row['name'],
                'categorie': row['categorie'],
                'marque': row.get('marque', ''),
                'modele': row.get('modele', ''),
                'numero_serie': row.get('numero_serie', ''),
                'localisation': row.get('localisation', ''),
                'notes': row.get('notes', ''),
            }

            if row.get('valeur_achat'):
                try:
                    vals['valeur_achat'] = float(row['valeur_achat'].replace(' ', '').replace(',', '.'))
                except ValueError:
                    erreurs.append(f"Ligne {i}: valeur_achat invalide '{row['valeur_achat']}'.")

            for champ_date in ('date_achat', 'date_fin_garantie'):
                if row.get(champ_date):
                    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
                        try:
                            vals[champ_date] = datetime.strptime(row[champ_date], fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        erreurs.append(f"Ligne {i}: {champ_date} invalide '{row[champ_date]}'. Format attendu: JJ/MM/AAAA")

            try:
                self.env['it.equipement'].create(vals)
                crees += 1
            except Exception as e:
                erreurs.append(f"Ligne {i}: erreur création — {e}")

        rapport_lignes = [
            f"✓ {crees} équipement(s) créé(s)",
            f"⊘ {ignores} doublon(s) ignoré(s)",
            f"✗ {len(erreurs) - ignores} erreur(s)",
        ]
        if erreurs:
            rapport_lignes.append("\nDétail :")
            rapport_lignes.extend(erreurs)

        self.write({
            'nb_crees': crees,
            'nb_ignores': ignores,
            'nb_erreurs': len(erreurs) - ignores,
            'rapport': '\n'.join(rapport_lignes),
            'traite': True,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.import.csv',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
