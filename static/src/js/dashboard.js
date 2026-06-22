/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Dashboard principal IT Parc
 * Charge les données depuis it.equipement.get_dashboard_data()
 * et affiche KPIs + graphique SVG catégories + barres d'état.
 */
export class ItParcDashboard extends Component {
    static template = "it_parc.Dashboard";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.state = useState({
            loaded: false,
            total_equipements: 0,
            affectes: 0,
            en_maintenance: 0,
            retires: 0,
            alertes_actives: 0,
            contrats_expirants: 0,
            by_categorie: [],
            by_state: [],
            // Données SVG précomputées
            bars: [],
            stateData: [],
            chartWidth: 560,
            chartHeight: 260,
            barW: 60,
        });
    }

    async willStart() {
        await this._loadData();
    }

    async _loadData() {
        try {
            const data = await this.orm.call(
                "it.equipement",
                "get_dashboard_data",
                []
            );
            this._processData(data);
        } catch (e) {
            console.error("IT Parc Dashboard error:", e);
        }
    }

    _processData(data) {
        const COLORS = ["#1565C0", "#2e7d32", "#e65100", "#c62828", "#6a1b9a", "#00838f"];
        const STATE_COLORS = {
            brouillon: "#90a4ae",
            affecte: "#2e7d32",
            en_maintenance: "#e65100",
            retire: "#c62828",
        };

        const chartW = 560;
        const chartH = 260;
        const maxH = chartH - 60;   // hauteur max des barres
        const cats = data.by_categorie || [];
        const n = cats.length || 1;
        const barW = Math.min(70, Math.floor((chartW - 90) / n) - 12);
        const spacing = (chartW - 90) / n;
        const maxVal = Math.max(...cats.map((c) => c.count), 1);

        const bars = cats.map((item, i) => {
            const bh = Math.max(Math.round((item.count / maxVal) * maxH), 4);
            const x = Math.round(70 + i * spacing + (spacing - barW) / 2);
            const y = chartH - 40 - bh;
            return {
                key: item.key,
                label: item.label.length > 11 ? item.label.substring(0, 10) + "…" : item.label,
                count: item.count,
                x, y, bh,
                color: COLORS[i % COLORS.length],
                labelX: x + Math.floor(barW / 2),
            };
        });

        // Grille Y (4 lignes horizontales)
        const gridLines = [25, 50, 75, 100].map((pct) => {
            const val = Math.round((maxVal * pct) / 100);
            const yPos = Math.round((chartH - 40) - (maxH * pct) / 100);
            return { val, yPos };
        });

        const total = data.total_equipements || 0;
        const stateData = (data.by_state || []).map((s) => ({
            key: s.key,
            label: s.label,
            count: s.count,
            color: STATE_COLORS[s.key] || "#90a4ae",
            pct: total > 0 ? Math.round((s.count / total) * 100) : 0,
        }));

        Object.assign(this.state, {
            ...data,
            bars,
            stateData,
            gridLines,
            chartWidth: chartW,
            chartHeight: chartH,
            barW,
            loaded: true,
        });
    }

    // ──── Actions de navigation ────

    openEquipements(domain = []) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Équipements",
            res_model: "it.equipement",
            view_mode: "list,kanban,form",
            domain,
        });
    }

    openAlertes() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Alertes actives",
            res_model: "it.alerte",
            view_mode: "list,form",
            domain: [["state", "=", "nouvelle"]],
        });
    }

    openContratsExpirants() {
        const today = new Date();
        const in30 = new Date(today.getTime() + 30 * 86400000);
        const dateStr = in30.toISOString().split("T")[0];
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Contrats expirant bientôt",
            res_model: "it.contrat",
            view_mode: "list,form",
            domain: [
                ["date_fin", "<=", dateStr],
                ["state", "=", "actif"],
            ],
        });
    }

    async refresh() {
        this.state.loaded = false;
        await this._loadData();
    }
}

registry.category("actions").add("it_parc_dashboard_action", ItParcDashboard);
