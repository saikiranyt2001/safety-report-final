function checkAuth(){
	const token = localStorage.getItem("auth_token") || localStorage.getItem("token");
	if(!token){
		window.location.href = "/frontend/login.html";
	}
}

function getCurrentRole(){
	return (localStorage.getItem("user_role") || "worker").toLowerCase();
}

function requireRoles(allowedRoles){
	const role = getCurrentRole();
	const allowed = allowedRoles.map(function(r){ return r.toLowerCase(); });

	if(!allowed.includes(role)){
		alert("You do not have permission to access this page.");
		window.location.href = "/frontend/pages/dashboard.html";
	}
}

function logoutUser(){
	localStorage.clear();
	window.location.href = "/frontend/login.html";
}