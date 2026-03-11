// Helper to get JWT token
function getAuthToken() {
	return localStorage.getItem("auth_token");
}

// Fetch analytics
async function fetchAnalytics() {
	const token = getAuthToken();

	const res = await fetch("http://localhost:8000/api/analytics", {
		method: "GET",
		headers: {
			"Authorization": `Bearer ${token}`
		}
	});

	return await res.json();
}

const API_URL = "http://localhost:8000";

// Generate AI report
async function generateReport(data){

	const response = await fetch(API_URL + "/generate-report",{
		method:"POST",
		headers:{
			"Content-Type":"application/json"
		},
		body:JSON.stringify(data)
	});

	const result = await response.json();

	const resultDiv = document.getElementById("result");

	if(resultDiv){
		resultDiv.innerText = JSON.stringify(result, null, 2);
	}

	return result;
}