function checkAuth(){
	const user = localStorage.getItem("username");
	if(!user){
		window.location.href = "/frontend/login.html";
	}
}

function logoutUser(){
	localStorage.clear();
	window.location.href = "/frontend/login.html";
}