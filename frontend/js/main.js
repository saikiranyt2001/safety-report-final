function highlightActivePage(){

const links = document.querySelectorAll(".sidebar a")

links.forEach(link => {

const href = link.getAttribute("href")

if(!href) return

if(window.location.pathname.includes(href.replace("../",""))){
link.classList.add("active")
}

function getApiBaseUrl() {
return window.location.origin
}

function buildApiUrl(path) {
return path.startsWith("http") ? path : getApiBaseUrl() + path
}

function getStoredToken() {
return localStorage.getItem("auth_token") || localStorage.getItem("token") || localStorage.getItem("access_token")
}

function clearStoredSession() {
localStorage.removeItem("auth_token")
localStorage.removeItem("token")
localStorage.removeItem("access_token")
localStorage.removeItem("username")
localStorage.removeItem("user_name")
localStorage.removeItem("user_role")
localStorage.removeItem("company_id")
localStorage.removeItem("company_name")
localStorage.removeItem("user")
}

function redirectToLogin() {
window.location.href = "/frontend/pages/login.html"
}

function ensureAuthenticated() {
if(!getStoredToken()){
redirectToLogin()
return false
}
return true
}

function logoutUser() {
clearStoredSession()
redirectToLogin()
}

function addChatMessage(text, type, messagesId = "chatMessages") {
const box = document.getElementById(messagesId)
if(!box) return

const div = document.createElement("div")
div.className = type
div.innerText = text
box.appendChild(div)
box.scrollTop = box.scrollHeight
}

async function sendBackendChatMessage(message) {
const response = await fetch(buildApiUrl("/api/ai-chat"), {
method: "POST",
headers: {
"Content-Type": "application/json",
"Authorization": "Bearer " + (getStoredToken() || "")
},
body: JSON.stringify({ prompt: message })
})

if(!response.ok){
throw new Error("AI safety assistant unavailable")
}

const data = await response.json()
return data.response || "No response available."
}

function wireBackendChat(inputId = "chatInput", messagesId = "chatMessages") {
const input = document.getElementById(inputId)
if(!input){
return
}

window.sendChat = async function(){
const text = input.value.trim()
if(text === ""){
return
}

addChatMessage(text, "user-msg", messagesId)
input.value = ""

try {
const reply = await sendBackendChatMessage(text)
addChatMessage(reply, "ai-msg", messagesId)
} catch (_error) {
addChatMessage("AI safety assistant unavailable. Try again.", "ai-msg", messagesId)
}
}

if(!input.dataset.backendChatBound){
input.addEventListener("keypress", function(e){
if(e.key === "Enter"){
window.sendChat()
}
})
input.dataset.backendChatBound = "1"
}
}

})

}
const ROLE_ACCESS_RULES = {
"/frontend/pages/users.html": ["admin"],
"/frontend/pages/settings.html": ["admin"],
"/frontend/pages/activity_log.html": ["admin", "manager"],
"/frontend/pages/analytics.html": ["admin", "manager"],
"/frontend/pages/generate_report.html": ["admin", "manager","worker"],
"/frontend/pages/rag_report.html": ["admin", "manager"],
"/frontend/pages/recommendations.html": ["admin", "manager"],
"/frontend/pages/risk_assessment.html": ["admin", "manager"],
"/frontend/pages/validator.html": ["admin", "manager"],
"/frontend/pages/upload.html": ["admin", "manager", "worker"],
"/frontend/pages/download_report.html": ["admin", "manager", "worker"],
"/frontend/pages/report_history.html": ["admin", "manager", "worker"],
"/frontend/pages/dashboard.html": ["admin", "manager", "worker"],
"/frontend/pages/live_detection.html": ["admin", "manager", "worker"],
"/frontend/ai_modules/hazard_detection.html": ["admin", "manager", "worker"],
"/frontend/ai_modules/compliance_agent.html": ["admin", "manager", "worker"],
"/frontend/ai_modules/incident_prediction.html": ["admin", "manager", "worker"],
"/frontend/ai_modules/risk_heatmap.html": ["admin", "manager", "worker"]
};

function getCurrentRole(){

const storedUser = JSON.parse(localStorage.getItem("user") || "null")

if(storedUser && storedUser.role){
return storedUser.role.toLowerCase()
}

const role = localStorage.getItem("user_role") || localStorage.getItem("role")

return (role || "worker").toLowerCase()

}

function canAccessPath(path, role){
const currentPath = path.toLowerCase();

for(const rulePath in ROLE_ACCESS_RULES){
if(currentPath.endsWith(rulePath.toLowerCase())){
return ROLE_ACCESS_RULES[rulePath].includes(role);
}
}

return true;
}

function enforcePageAccess(){
const token = getStoredToken();
if(!token){
return;
}

const role = getCurrentRole();
const currentPath = window.location.pathname;

if(!canAccessPath(currentPath, role)){
alert("You do not have permission to access this page.");
window.location.href = "/frontend/pages/dashboard.html";
}
}

function applyRoleBasedNavigation(){
const role = getCurrentRole();
	const storedUser = JSON.parse(localStorage.getItem("user") || "null");
	const resolvedRole = (storedUser && storedUser.role ? storedUser.role : role).toLowerCase();
const links = document.querySelectorAll(".sidebar a, .nav-links a");
	const usersMenu = document.getElementById("users-menu");

	if(usersMenu && resolvedRole !== "admin"){
		usersMenu.style.display = "none";
	}

links.forEach(function(link){
const href = link.getAttribute("href");
if(!href){
return;
}

let resolvedPath = href;
if(href.startsWith("../")){
resolvedPath = "/frontend/" + href.replace("../", "");
} else if(!href.startsWith("/")){
resolvedPath = "/frontend/pages/" + href;
}

		if(!canAccessPath(resolvedPath, resolvedRole)){
link.style.display = "none";
}
});
}



function initSidebar(){

const toggleBtn = document.getElementById("menuToggle")
const sidebar = document.querySelector(".sidebar")
const navbar = document.querySelector(".navbar")
const mainContent = document.querySelector(".main-content")
const footer = document.querySelector(".footer")

if(toggleBtn && sidebar){

toggleBtn.addEventListener("click", () => {

sidebar.classList.toggle("collapsed")

if(navbar){
navbar.classList.toggle("expanded")
}

if(mainContent){
mainContent.classList.toggle("expanded")
}

if(footer)
footer.classList.toggle("expanded")


})

}

}


function searchFeature(){

const features = {
"dashboard":"dashboard.html",
"analytics":"analytics.html",
"upload":"upload_data.html",
"analyze":"analyze_image.html",
"live":"live_detection.html",
"webcam":"live_detection.html",
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
{ name:"Dashboard", page:"/frontend/pages/dashboard.html", cat:"Pages" },
{ name:"Upload Data", page:"/frontend/pages/upload.html", cat:"Pages" },
{ name:"Analyze Image", page:"/frontend/pages/analyze_image.html", cat:"Pages" },
{ name:"Live Detection", page:"/frontend/pages/live_detection.html", cat:"Pages" },
{ name:"Generate Report", page:"/frontend/pages/generate_report.html", cat:"Reports" },
{ name:"RAG Report", page:"/frontend/pages/rag_report.html", cat:"Reports" },
{ name:"Report History", page:"/frontend/pages/report_history.html", cat:"Reports" },
{ name:"Download Report", page:"/frontend/pages/download_report.html", cat:"Reports" },
{ name:"Analytics", page:"/frontend/pages/analytics.html", cat:"Pages" },
{ name:"KPI Dashboard", page:"/frontend/pages/kpi_dashboard.html", cat:"Pages" },
{ name:"Recommendations", page:"/frontend/pages/recommendations.html", cat:"Pages" },
{ name:"Risk Assessment", page:"/frontend/pages/risk_assessment.html", cat:"Pages" },
{ name:"Risk Register", page:"/frontend/pages/risk_register.html", cat:"Pages" },
{ name:"Validator", page:"/frontend/pages/validator.html", cat:"Pages" },
{ name:"Compliance Tracker", page:"/frontend/pages/compliance_tracker.html", cat:"Pages" },
{ name:"Incidents", page:"/frontend/pages/incidents.html", cat:"Pages" },
{ name:"Inspection", page:"/frontend/pages/inspection.html", cat:"Pages" },
{ name:"Documents", page:"/frontend/pages/documents.html", cat:"Pages" },
{ name:"Training", page:"/frontend/pages/training.html", cat:"Pages" },
{ name:"Users", page:"/frontend/pages/users.html", cat:"Pages" },
{ name:"Settings", page:"/frontend/pages/settings.html", cat:"Pages" },
{ name:"Site Map", page:"/frontend/pages/site_map.html", cat:"Pages" },
{ name:"Activity Log", page:"/frontend/pages/activity_log.html", cat:"Pages" },
{ name:"Incident Prediction", page:"/frontend/ai_modules/incident_prediction.html", cat:"AI Modules" },
{ name:"Hazard Detection", page:"/frontend/ai_modules/hazard_detection.html", cat:"Hazards" },
{ name:"Compliance Agent", page:"/frontend/ai_modules/compliance_agent.html", cat:"AI Modules" },
{ name:"Risk Heatmap", page:"/frontend/ai_modules/risk_heatmap.html", cat:"Hazards" }
];

const input = document.getElementById("appSearch");
const results = document.getElementById("searchResults");

if(!input || !results) return;

applyRoleBasedNavigation();

input.addEventListener("input", function(){

let query = input.value.toLowerCase().trim();
results.innerHTML="";

if(query === ""){
results.style.display="none";
return;
}

let matches = features.filter(f =>
f.name.toLowerCase().includes(query)
);

if(matches.length === 0){
results.style.display="none";
return;
}

// Group by category
let grouped = {};
matches.forEach(f => {
if(!grouped[f.cat]) grouped[f.cat]=[];
grouped[f.cat].push(f);
});

Object.keys(grouped).forEach(cat => {
let catDiv = document.createElement("div");
catDiv.className = "search-category";
catDiv.innerText = cat;
results.appendChild(catDiv);

grouped[cat].forEach(feature => {
let div = document.createElement("div");
div.className = "search-item";
div.innerText = feature.name;
div.onclick = function(){
showLoader();
window.location.href = feature.page;
};
results.appendChild(div);
});
});

results.style.display = "block";

});

// Close dropdown when clicking outside
document.addEventListener("click", function(e){
if(!input.contains(e.target) && !results.contains(e.target)){
results.style.display="none";
}
});

}

/* ============================= */
/* DARK MODE */
/* ============================= */

function toggleDark(){
document.body.classList.toggle("dark");
const isDark = document.body.classList.contains("dark");
localStorage.setItem("darkMode", isDark ? "1" : "0");
}

function applyDarkMode(){
if(localStorage.getItem("darkMode") === "1"){
document.body.classList.add("dark");
}
}

/* ============================= */
/* NOTIFICATION BELL */
/* ============================= */

function toggleNotifPanel(){
const panel = document.getElementById("notifPanel");
if(!panel) return;
panel.style.display = panel.style.display === "block" ? "none" : "block";
}

function clearNotifications(e){
e.stopPropagation();
const list = document.getElementById("notifList");
const empty = document.getElementById("notifEmpty");
const badge = document.getElementById("notifCount");
if(list) list.style.display="none";
if(empty) empty.style.display="block";
if(badge) badge.style.display="none";
}

// Close notif panel when clicking outside
function initNotifications(){
document.addEventListener("click", function(e){
const panel = document.getElementById("notifPanel");
const bell = document.querySelector(".notification");
if(panel && bell && !bell.contains(e.target)){
panel.style.display="none";
}
});
}

/* ============================= */
/* BREADCRUMB */
/* ============================= */

function initBreadcrumb(){
const mainContent = document.querySelector(".main-content");
if(!mainContent) return;

// Inject breadcrumb div if not present
let container = document.getElementById("breadcrumb");
if(!container){
container = document.createElement("div");
container.id = "breadcrumb";
mainContent.insertBefore(container, mainContent.firstChild);
}

const path = window.location.pathname;
const filename = path.split("/").pop();
const parts = path.split("/").filter(p => p && p !== "frontend" && p !== "pages" && p !== "ai_modules");

let crumbs = ["<a href='/frontend/pages/dashboard.html'>Dashboard</a>"];

// Section label from folder
if(path.includes("/ai_modules/")) crumbs.push("<span>AI Modules</span>");
else if(path.includes("/pages/")) crumbs.push("<span>Pages</span>");

// Current page name
if(filename && filename.endsWith(".html")){
const label = filename.replace(".html","").replace(/_/g," ")
.replace(/\b\w/g, c => c.toUpperCase());
crumbs.push("<span>" + label + "</span>");
}

container.innerHTML = crumbs.join(" <span class='crumb-sep'>/</span> ");
}

/* ============================= */
/* PAGE LOADER */
/* ============================= */

function showLoader(){
const loader = document.getElementById("loader");
if(loader) loader.style.display="flex";
}

function hideLoader(){
const loader = document.getElementById("loader");
if(loader) loader.style.display="none";
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

document.addEventListener("DOMContentLoaded", function(){

enforcePageAccess()
initSidebar()
initSearch()
applyRoleBasedNavigation()
highlightActivePage()
applyDarkMode()
initNotifications()
initBreadcrumb()
hideLoader()

})

const analyzeBtn = document.getElementById("analyzeBtn")

if(analyzeBtn){
analyzeBtn.addEventListener("click", function(e){
e.preventDefault()
e.stopPropagation()
analyzeImage()
})
}

const imageInput = document.getElementById("imageInput")

if(imageInput){
imageInput.addEventListener("change", previewImage)
}

function setResultImage(path) {
const resultImage = document.getElementById("resultImage")
if(resultImage && path){
resultImage.src = buildApiUrl(path.startsWith("/") ? path : "/" + path)
}
}



async function uploadEvidence(file){

const formData = new FormData()
formData.append("file", file)

const token = getStoredToken()

const res = await fetch(buildApiUrl("/api/upload"),{

method:"POST",
headers:{
"Authorization":"Bearer "+token
},
body:formData

})

if(!res.ok){
throw new Error("Failed to upload evidence")
}

return await res.json()

}	
