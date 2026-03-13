function toggleChat(){
    let sidebar = document.querySelector(".ai-chat-sidebar");
    sidebar.classList.toggle("active");
}

async function sendChat(){
    let input = document.getElementById("chatInput");
    let text = input.value;

    if(text.trim() === "") return;

    addChat(text,"user-msg");
    input.value = "";

    try {

        const response = await fetch("http://127.0.0.1:8001/api/ai-chat",{
            method:"POST",
            headers:{
                "Content-Type":"application/json"
            },
            body: JSON.stringify({
                prompt:text
            })
        });

        const data = await response.json();

        addChat(data.response || "No response","ai-msg");

    } catch(error){
        console.error(error);
        addChat("AI safety assistant is temporarily unavailable. Please try again.","ai-msg");
    }
}

function addChat(text,type){
    let box=document.getElementById("chatMessages")
    let div=document.createElement("div")
    div.className=type
    div.innerText=text
    box.appendChild(div)
    box.scrollTop=box.scrollHeight
}


