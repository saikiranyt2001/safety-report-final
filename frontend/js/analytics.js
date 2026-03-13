const analyticsToken = localStorage.getItem("auth_token") || localStorage.getItem("token")

if (!analyticsToken) {
	window.location.href = "login.html"
}

function analyticsHeaders() {
	const headers = { "Content-Type": "application/json" }
	if (analyticsToken && analyticsToken !== "loggedin") {
		headers.Authorization = `Bearer ${analyticsToken}`
	}
	return headers
}

function setText(id, value) {
	const el = document.getElementById(id)
	if (el) el.textContent = value
}

const analyticsCharts = {}

function destroyChart(id) {
	if (analyticsCharts[id]) {
		analyticsCharts[id].destroy()
		delete analyticsCharts[id]
	}
}

function buildLineChart(id, label, labels, data, borderColor, backgroundColor) {
	destroyChart(id)
	const ctx = document.getElementById(id)
	if (!ctx) return
	analyticsCharts[id] = new Chart(ctx, {
		type: "line",
		data: {
			labels,
			datasets: [{
				label,
				data,
				borderColor,
				backgroundColor,
				fill: true,
				tension: 0.32,
			}],
		},
		options: {
			responsive: true,
			maintainAspectRatio: false,
			plugins: { legend: { display: false } },
		},
	})
}

function buildBarChart(id, label, labels, data, color) {
	destroyChart(id)
	const ctx = document.getElementById(id)
	if (!ctx) return
	analyticsCharts[id] = new Chart(ctx, {
		type: "bar",
		data: {
			labels,
			datasets: [{ label, data, backgroundColor: color, borderRadius: 8 }],
		},
		options: {
			responsive: true,
			maintainAspectRatio: false,
			plugins: { legend: { display: false } },
		},
	})
}

function buildDoughnutChart(id, labels, data, colors) {
	destroyChart(id)
	const ctx = document.getElementById(id)
	if (!ctx) return
	analyticsCharts[id] = new Chart(ctx, {
		type: "doughnut",
		data: {
			labels,
			datasets: [{ data, backgroundColor: colors }],
		},
		options: {
			responsive: true,
			maintainAspectRatio: false,
		},
	})
}

function renderTopSites(items) {
	const container = document.getElementById("topSites")
	if (!container) return
	if (!items || !items.length) {
		container.innerHTML = '<div class="empty">No project trend data available yet.</div>'
		return
	}
	container.innerHTML = items.map((item) => `
		<div class="site-item">
			<div>
				<strong>${item.project_name}</strong>
				<small>Project #${item.project_id}</small>
			</div>
			<div style="text-align:right">
				<strong>${item.hazards + item.incidents}</strong>
				<small>${item.hazards} hazards, ${item.incidents} incidents</small>
			</div>
		</div>
	`).join("")
}

function renderRiskMatrix(matrix) {
	const container = document.getElementById("riskMatrix")
	if (!container) return

	const severityLevels = ["low", "medium", "high"]
	const likelihoodLevels = ["low", "medium", "high"]
	const label = (value) => value.charAt(0).toUpperCase() + value.slice(1)

	let html = '<div class="heatmap-header-cell"></div>'
	severityLevels.forEach((severity) => {
		html += `<div class="heatmap-header-cell">${label(severity)} Severity</div>`
	})

	likelihoodLevels.forEach((likelihood) => {
		html += `<div class="heatmap-axis">${label(likelihood)} Likelihood</div>`
		severityLevels.forEach((severity) => {
			const count = matrix?.[likelihood]?.[severity] || 0
			const style = count >= 3 ? "high" : count >= 1 ? "medium" : "low"
			html += `<div class="heatmap-cell ${style}"><strong>${count}</strong></div>`
		})
	})

	container.innerHTML = html
}

async function loadAnalyticsDashboard() {
	try {
		const [summaryRes, trendsRes, typesRes, distributionRes, matrixRes] = await Promise.all([
			fetch("/api/analytics/safety-summary", { headers: analyticsHeaders() }),
			fetch("/api/analytics/risk-trends", { headers: analyticsHeaders() }),
			fetch("/api/analytics/hazard-types", { headers: analyticsHeaders() }),
			fetch("/api/analytics/risk-distribution", { headers: analyticsHeaders() }),
			fetch("/api/analytics/risk-matrix", { headers: analyticsHeaders() }),
		])

		if (!summaryRes.ok || !trendsRes.ok || !typesRes.ok || !distributionRes.ok || !matrixRes.ok) {
			throw new Error("Analytics load failed")
		}

		const summary = await summaryRes.json()
		const trends = await trendsRes.json()
		const types = await typesRes.json()
		const distribution = await distributionRes.json()
		const matrix = await matrixRes.json()

		setText("hazardsStat", summary.hazards_detected || 0)
		setText("highRiskStat", summary.high_risk_hazards || 0)
		setText("incidentsStat", summary.incidents_reported || 0)
		setText("scoreStat", summary.average_safety_score || 0)
		setText("tasksStat", summary.open_tasks || 0)
		setText("inspectionRateStat", `${summary.inspection_completion_rate || 0}%`)

		buildLineChart(
			"hazardTrendChart",
			"Hazards",
			trends.labels || [],
			trends.hazards || [],
			"#0b7285",
			"rgba(11, 114, 133, 0.15)"
		)
		buildBarChart(
			"incidentTrendChart",
			"Incidents",
			trends.labels || [],
			trends.incidents || [],
			"#d9480f"
		)
		buildLineChart(
			"scoreTrendChart",
			"Safety Score",
			trends.labels || [],
			trends.safety_scores || [],
			"#2f9e44",
			"rgba(47, 158, 68, 0.16)"
		)
		buildDoughnutChart(
			"hazardTypesChart",
			(types.items || []).map((item) => item.label),
			(types.items || []).map((item) => item.count),
			["#0b7285", "#2f9e44", "#f59f00", "#d9480f", "#7048e8", "#495057"]
		)
		buildDoughnutChart(
			"riskDistributionChart",
			["Low", "Medium", "High", "Critical"],
			[distribution.low || 0, distribution.medium || 0, distribution.high || 0, distribution.critical || 0],
			["#b2f2bb", "#ffe066", "#ffa8a8", "#c92a2a"]
		)

		renderTopSites(summary.top_sites || [])
		renderRiskMatrix(matrix)
	} catch (_error) {
		setText("hazardsStat", "-")
		setText("highRiskStat", "-")
		setText("incidentsStat", "-")
		setText("scoreStat", "-")
		setText("tasksStat", "-")
		setText("inspectionRateStat", "-")
		renderTopSites([])
		renderRiskMatrix({})
	}
}

loadAnalyticsDashboard()