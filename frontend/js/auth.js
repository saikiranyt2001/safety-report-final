function getStoredToken(){
	return localStorage.getItem("auth_token") || localStorage.getItem("token") || localStorage.getItem("access_token");
}

function clearStoredSession(){
	localStorage.removeItem("auth_token");
	localStorage.removeItem("token");
	localStorage.removeItem("access_token");
	localStorage.removeItem("username");
	localStorage.removeItem("user_name");
	localStorage.removeItem("user_role");
	localStorage.removeItem("company_id");
	localStorage.removeItem("company_name");
	localStorage.removeItem("user");
}

function checkAuth(){

	const token = getStoredToken();

	if(!token){
		window.location.href = "/frontend/pages/login.html";
	}

}

function getCurrentRole(){

	return (localStorage.getItem("user_role") || "worker").toLowerCase();

}

function requireRoles(allowedRoles){

	const role = getCurrentRole();

	const allowed = allowedRoles.map(function(r){
		return r.toLowerCase();
	});

	if(!allowed.includes(role)){

		alert("You do not have permission to access this page.");

		window.location.href = "/frontend/pages/dashboard.html";

	}

}

function logoutUser(){

	clearStoredSession();

	window.location.href = "/frontend/pages/login.html";

}
