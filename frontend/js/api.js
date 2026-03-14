const API_URL = "http://127.0.0.1:8000";

// Helper to get JWT token
function getAuthToken(){
    return localStorage.getItem("auth_token") || localStorage.getItem("token");
}

// Fetch analytics
async function fetchAnalytics(){

    const res = await fetch(API_URL + "/api/analytics",{
        method:"GET",
        headers:{
            "Authorization": `Bearer ${getAuthToken()}`
        }
    });

    return await res.json();
}

// Generate AI report
async function generateReport(data){

    const response = await fetch(API_URL + "/api/generate-report",{
        method:"POST",
        headers:{
            "Content-Type":"application/json",
            "Authorization": `Bearer ${getAuthToken()}`
        },
        body:JSON.stringify(data)
    });

    const result = await response.json();

    const resultDiv = document.getElementById("result");

    if(resultDiv){
        resultDiv.innerText = JSON.stringify(result,null,2);
    }

    return result;
}

// Auth check
function checkAuth(){

    const token = getAuthToken();

    if(!token){
        window.location.href = "/frontend/pages/login.html";
    }
}

// Role system
function getCurrentRole(){
    return (localStorage.getItem("user_role") || "worker").toLowerCase();
}

function requireRoles(allowedRoles){

    const role = getCurrentRole();
    const allowed = allowedRoles.map(r => r.toLowerCase());

    if(!allowed.includes(role)){
        alert("You do not have permission to access this page.");
        window.location.href = "/frontend/pages/dashboard.html";
    }
}

// Logout
function logoutUser(){
    localStorage.clear();
    window.location.href = "/frontend/pages/login.html";
}

// Chat
async function sendChat(){

    let input = document.getElementById("chatInput");
    let text = input.value;

    if(text.trim()==="") return;

    addChat(text,"user-msg");
    input.value="";

    try{

        const response = await fetch(API_URL + "/api/ai-chat",{
            method:"POST",
            headers:{
                "Content-Type":"application/json",
                "Authorization": `Bearer ${getAuthToken()}`
            },
            body:JSON.stringify({
                prompt:text
            })
        });

        const data = await response.json();

        addChat(data.response || "No response","ai-msg");

    }catch(error){

        console.error(error);

        addChat("AI safety assistant unavailable. Try again.","ai-msg");

    }
}

function addChat(text,type){

    let box=document.getElementById("chatMessages");

    let div=document.createElement("div");

    div.className=type;
    div.innerText=text;

    box.appendChild(div);

    box.scrollTop=box.scrollHeight;

}