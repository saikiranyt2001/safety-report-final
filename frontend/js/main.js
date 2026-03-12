
function highlightActivePage(){

const links = document.querySelectorAll(".sidebar a")

links.forEach(link => {

if(window.location.href.includes(link.getAttribute("href"))){
link.classList.add("active")
}

})

}

function initSidebar(){

const toggleBtn = document.getElementById("menuToggle")
const sidebar = document.querySelector(".sidebar")

if(toggleBtn && sidebar){

toggleBtn.addEventListener("click", () => {

sidebar.classList.toggle("collapsed")
document.body.classList.toggle("sidebar-collapsed")

})

}

}



function searchFeature(){

const features = {
"dashboard":"dashboard.html",
"analytics":"analytics.html",
"upload":"upload_data.html",
"analyze":"analyze_image.html",
"report":"report_history.html",
"profile":"profile.html",
"heatmap":"analytics.html"
}

let query = document.getElementById("appSearch").value.toLowerCase().trim()

for(let key in features){

if(query.includes(key)){
window.location.href = "/frontend/pages/" + features[key]
return
}

}

}

/* GLOBAL SEARCH DROPDOWN */

function initSearch(){

const features = [
{ name:"Dashboard", page:"/frontend/pages/dashboard.html" },
{ name:"Upload Data", page:"/frontend/pages/upload.html" },
{ name:"Analyze Image", page:"/frontend/pages/analyze_image.html" },
{ name:"Generate Report", page:"/frontend/pages/generate_report.html" },
{ name:"RAG Report", page:"/frontend/pages/rag_report.html" },
{ name:"Report History", page:"/frontend/pages/report_history.html" },
{ name:"Analytics", page:"/frontend/pages/analytics.html" },
{ name:"Download Report", page:"/frontend/pages/download_report.html" },
{ name:"Recommendations", page:"/frontend/pages/recommendations.html" },
{ name:"Risk Assessment", page:"/frontend/pages/risk_assessment.html" },
{ name:"Validator", page:"/frontend/pages/validator.html" },
{ name:"Incident Prediction", page:"/frontend/ai_modules/incident_prediction.html" },
{ name:"Hazard Detection", page:"/frontend/ai_modules/hazard_detection.html" }
];

const input = document.getElementById("appSearch");
const results = document.getElementById("searchResults");

if(!input || !results) return;

input.addEventListener("input", function(){

let query = input.value.toLowerCase();
results.innerHTML="";

if(query === ""){
results.style.display="none";
return;
}

let matches = features.filter(f =>
f.name.toLowerCase().includes(query)
);

matches.forEach(feature => {

let div=document.createElement("div");
div.className="search-item";
div.innerText=feature.name;

div.onclick=function(){
window.location.href = feature.page
}

results.appendChild(div);

});

results.style.display = matches.length ? "block" : "none";

});

}

function toggleChat(){

const chat = document.getElementById("aiChat")
const button = document.querySelector(".chat-toggle-btn")

if(!chat || !button) return

chat.classList.toggle("open")

if(chat.classList.contains("open")){
button.style.display = "none"
}else{
button.style.display = "block"
}

}