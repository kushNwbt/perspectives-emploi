const API_BASE = window.PERSPECTIVES_API_URL || "";
const fileInput=document.getElementById("cvFile");
const choose=document.getElementById("cvChoose");
const drop=document.getElementById("cvDropZone");
const title=document.getElementById("cvFileTitle");
const info=document.getElementById("cvFileInfo");
const status=document.getElementById("cvStatus");

function showStatus(message,type="loading"){
  status.hidden=false; status.className="cv-status "+type; status.textContent=message;
}
function validate(file){
  const ext=(file.name.split(".").pop()||"").toLowerCase();
  if(!["pdf","docx","txt"].includes(ext)) return "Format non accepté. Utilisez un PDF, DOCX ou TXT.";
  if(file.size>10*1024*1024) return "Le fichier dépasse 10 Mo.";
  return "";
}
async function handleFile(file){
  if(!file)return;
  const error=validate(file);
  if(error){showStatus(error,"error");return;}
  title.textContent=file.name;
  info.textContent=(file.size/1024/1024).toFixed(2)+" Mo · prêt à être analysé";
  if(!API_BASE){
    showStatus("CV sélectionné. Le backend d’analyse doit maintenant être connecté pour lancer le diagnostic.","ok");
    return;
  }
  choose.disabled=true; showStatus("Analyse du CV en cours…","loading");
  try{
    const data=new FormData(); data.append("cv",file);
    const response=await fetch(API_BASE.replace(/\/$/,"")+"/api/cv/analyse",{method:"POST",body:data});
    if(!response.ok) throw new Error("HTTP "+response.status);
    const result=await response.json();
    sessionStorage.setItem("perspectives_cv_analysis",JSON.stringify(result));
    showStatus("CV analysé avec succès. Le diagnostic est disponible dans Mon CV.","ok");
  }catch(e){
    showStatus("Impossible de joindre le serveur d’analyse. Le CV n’a pas été envoyé.","error");
  }finally{choose.disabled=false;}
}
choose.addEventListener("click",()=>fileInput.click());
fileInput.addEventListener("change",()=>handleFile(fileInput.files[0]));
["dragenter","dragover"].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.add("drag")}));
["dragleave","drop"].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.remove("drag")}));
drop.addEventListener("drop",e=>handleFile(e.dataTransfer.files[0]));
