// Helper to get JWT token
function getAuthToken() {
	return localStorage.getItem("auth_token");
}

// Example: fetch analytics with Authorization header
async function fetchAnalytics() {
	const token = getAuthToken();
	const res = await fetch("/api/analytics", {
		method: "GET",
		headers: {
			"Authorization": `Bearer ${token}`
		}
	});
	return await res.json();
}
const API_URL = "http://localhost:8000";

async function generateReport(data){
	const response = await fetch(API_URL + "/generate-report",{
		method:"POST",
		headers:{
			"Content-Type":"application/json"
		},
		body:JSON.stringify(data)
	});
	return await response.json();
}

document.getElementById("result").innerText = data.report


