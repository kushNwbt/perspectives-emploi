const API_BASE = window.PERSPECTIVES_API_URL || "https://perspectives-emploi-api-production.up.railway.app";
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

const homeSections=[...document.querySelectorAll("main > section:not(#cvDiagnostic), main > footer")];
const cvDiagnostic=document.getElementById("cvDiagnostic");
function esc(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function renderCvDiagnostic(){
  const raw=sessionStorage.getItem("perspectives_cv_analysis");
  document.getElementById("diagEmpty").hidden=!!raw;
  document.getElementById("diagContent").hidden=!raw;
  if(!raw)return;
  const a=JSON.parse(raw);
  document.getElementById("diagScore").firstChild.nodeValue=(a.score??"--");
  const st=document.getElementById("diagStatus"); st.textContent=a.statut||"Non évalué"; st.className="status-pill "+((a.statut||"").toLowerCase().includes("bon")?"good":(a.statut||"").toLowerCase().includes("prior")?"bad":"warn");
  document.getElementById("diagDisclaimer").textContent=a.avertissement||"";
  const sections=document.getElementById("diagSections"); sections.innerHTML="";
  Object.entries(a.sections||{}).forEach(([name,ok])=>{sections.insertAdjacentHTML("beforeend",'<div class="diag-card"><span class="diag-icon '+(ok?"good":"warn")+'">'+(ok?"✓":"!")+'</span><div><strong>'+esc(name)+'</strong><p>'+(ok?"Rubrique identifiée dans le CV.":"Rubrique à rendre plus visible ou à vérifier.")+'</p></div></div>')});
  const priorities=document.getElementById("diagPriorities"); priorities.innerHTML="";
  (a.priorites||[]).forEach(p=>{const cls=(p.niveau||"").toLowerCase().includes("bon")?"good":(p.niveau||"").toLowerCase().includes("prior")?"bad":"warn";priorities.insertAdjacentHTML("beforeend",'<div class="priority-card '+cls+'"><span>'+esc(p.niveau)+'</span><h4>'+esc(p.titre)+'</h4><p><b>👉 À faire :</b> '+esc(p.conseil)+'</p></div>')});
}
function openCvView(){
  homeSections.forEach(x=>x.hidden=true); cvDiagnostic.hidden=false; renderCvDiagnostic(); window.scrollTo({top:0,behavior:"smooth"});
  document.querySelectorAll(".sidebar a").forEach(a=>a.classList.remove("active")); const link=document.querySelector('.sidebar a[href="#cv"]'); if(link)link.classList.add("active");
}
function openHome(){
  cvDiagnostic.hidden=true; homeSections.forEach(x=>x.hidden=false); window.scrollTo({top:0,behavior:"smooth"});
  document.querySelectorAll(".sidebar a").forEach(a=>a.classList.remove("active")); const link=document.querySelector('.sidebar a[href="#accueil"]'); if(link)link.classList.add("active");
}
document.querySelectorAll('[data-view="cv"],.sidebar a[href="#cv"]').forEach(el=>el.addEventListener("click",e=>{e.preventDefault();openCvView()}));
document.querySelector('.sidebar a[href="#accueil"]').addEventListener("click",e=>{e.preventDefault();openHome()});
document.getElementById("backHome").addEventListener("click",openHome);

const romeSearch=document.getElementById("romeSearch"),romeResults=document.getElementById("romeResults"),romeSelected=document.getElementById("romeSelected");
let romeTimer=null;
function renderRomeSelected(job){
  if(!job){romeSelected.hidden=true;romeSelected.innerHTML="";return;}
  romeSelected.hidden=false;romeSelected.innerHTML='<div><strong>'+esc(job.libelle)+'</strong><span>ROME '+esc(job.code)+'</span></div><button type="button" id="clearRome">×</button>';
  document.getElementById("clearRome").onclick=()=>{sessionStorage.removeItem("perspectives_target_job");romeSearch.value="";renderRomeSelected(null)};
}
async function searchRome(q){
  if(q.trim().length<2){romeResults.hidden=true;romeResults.innerHTML="";return;}
  romeResults.hidden=false;romeResults.innerHTML='<div class="rome-loading">Recherche…</div>';
  try{
    const r=await fetch(API_BASE.replace(/\/$/,"")+"/api/rome/metiers?q="+encodeURIComponent(q.trim()));
    if(!r.ok)throw new Error();
    const jobs=await r.json();romeResults.innerHTML="";
    if(!jobs.length){romeResults.innerHTML='<div class="rome-loading">Aucun métier trouvé.</div>';return;}
    jobs.slice(0,8).forEach(job=>{const b=document.createElement("button");b.type="button";b.className="rome-option";b.innerHTML='<strong>'+esc(job.libelle)+'</strong><span>'+esc(job.code)+'</span>';b.onclick=()=>{sessionStorage.setItem("perspectives_target_job",JSON.stringify(job));romeSearch.value=job.libelle;romeResults.hidden=true;renderRomeSelected(job)};romeResults.appendChild(b)});
  }catch(e){romeResults.innerHTML='<div class="rome-loading">Recherche momentanément indisponible.</div>'}
}
romeSearch.addEventListener("input",()=>{clearTimeout(romeTimer);romeTimer=setTimeout(()=>searchRome(romeSearch.value),280)});
romeSearch.addEventListener("focus",()=>{if(romeSearch.value.trim().length>=2)searchRome(romeSearch.value)});
document.addEventListener("click",e=>{if(!e.target.closest(".rome-wrap"))romeResults.hidden=true});
try{const saved=JSON.parse(sessionStorage.getItem("perspectives_target_job"));if(saved){romeSearch.value=saved.libelle||"";renderRomeSelected(saved)}}catch(e){}
