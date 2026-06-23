/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class ItParcDashboard extends Component {
    static template = "it_parc.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            total: 0,
            actifs: 0,
            en_maintenance: 0,
            retires: 0,
            alertes_actives: 0,
            cout_mois: 0,
            par_categorie: [],
        });
        this._chart = null;

        onMounted(async () => {
            await this._loadData();
        });

        onWillUnmount(() => {
            if (this._chart) {
                this._chart.destroy();
            }
        });
    }

    async _loadData() {
        try {
            const data = await this.orm.call("it.equipement", "get_dashboard_data", []);
            Object.assign(this.state, data);
            this._renderChart(data.par_categorie || []);
        } catch (e) {
            console.error("Erreur chargement dashboard IT Parc:", e);
        }
    }

    _renderChart(par_categorie) {
        const canvas = document.getElementById("it_parc_cat_chart");
        if (!canvas || !par_categorie.length) return;

        if (typeof Chart === "undefined") {
            return;
        }

        if (this._chart) {
            this._chart.destroy();
        }

        const colors = [
            "#1F4E79", "#2196F3", "#4CAF50", "#FFC107",
            "#E91E63", "#9C27B0", "#FF5722", "#00BCD4",
        ];

        this._chart = new Chart(canvas.getContext("2d"), {
            type: "doughnut",
            data: {
                labels: par_categorie.map(c => c.label),
                datasets: [{
                    data: par_categorie.map(c => c.count),
                    backgroundColor: colors.slice(0, par_categorie.length),
                    borderWidth: 2,
                    borderColor: "#fff",
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { position: "right" },
                },
            },
        });
    }

    navTo(model) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
        });
    }
}

registry.category("actions").add("it_parc_dashboard_action", ItParcDashboard);
