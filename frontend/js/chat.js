function toggleChat(){
    let sidebar = document.querySelector(".ai-chat-sidebar");
    sidebar.classList.toggle("active");
}

function sendChat(){
    let input=document.getElementById("chatInput")
    let text=input.value
    if(text.trim()==="") return
    addChat(text,"user-msg")
    input.value=""
    setTimeout(()=>{
        addChat(generateReply(text),"ai-msg")
    },500)
}

function addChat(text,type){
    let box=document.getElementById("chatMessages")
    let div=document.createElement("div")
    div.className=type
    div.innerText=text
    box.appendChild(div)
    box.scrollTop=box.scrollHeight
}

function generateReply(q){
    q=q.toLowerCase()
    if(q.includes("hazard"))
        return "Common hazards include slips, falls, electrical risks and unsafe machinery."
    if(q.includes("ppe"))
        return "PPE includes helmets, gloves, goggles and safety boots."
    if(q.includes("accident"))
        return "Accidents can be reduced through safety training and hazard reporting."
    return "Safety tip: Always conduct a risk assessment before starting work."
}
