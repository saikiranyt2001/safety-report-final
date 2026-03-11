
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