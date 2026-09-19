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

const homeSections=[...document.querySelectorAll("main > section:not(.diagnostic-view), main > footer")];
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
  document.querySelectorAll(".diagnostic-view").forEach(x=>x.hidden=true); homeSections.forEach(x=>x.hidden=false); window.scrollTo({top:0,behavior:"smooth"});
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

const skillsView=document.getElementById("skillsView");
async function renderSkills(){
  const empty=document.getElementById("skillsEmpty"),content=document.getElementById("skillsContent"),list=document.getElementById("skillsList"),target=document.getElementById("skillsTarget");
  let job=null,cv=null;try{job=JSON.parse(sessionStorage.getItem("perspectives_target_job"))}catch(e){}try{cv=JSON.parse(sessionStorage.getItem("perspectives_cv_analysis"))}catch(e){}
  if(!cv){empty.hidden=false;content.hidden=true;empty.textContent="Importez d’abord un CV pour analyser les compétences.";return}
  if(!job){empty.hidden=false;content.hidden=true;empty.textContent="Aucun métier visé sélectionné. Choisissez un métier ROME depuis l’accueil pour lancer la comparaison.";return}
  empty.hidden=true;content.hidden=false;target.innerHTML='<span>Métier comparé</span><strong>'+esc(job.libelle)+'</strong><b>ROME '+esc(job.code)+'</b>';
  list.innerHTML='<div class="rome-loading">Chargement des compétences officielles ROME…</div>';
  try{
    const r=await fetch(API_BASE.replace(/\/$/,"")+"/api/rome/competences?code_rome="+encodeURIComponent(job.code));
    if(!r.ok)throw new Error();
    const data=await r.json(),items=data.competences||[];
    if(!items.length){list.innerHTML='<div class="rome-loading">Aucune compétence ROME disponible pour ce métier.</div>';return}
    const evidence=(cv.competences_cv||[]).map(x=>String(x).trim()).filter(Boolean);
    const norm=s=>String(s||"").toLowerCase().normalize("NFD").replace(/[\\u0300-\\u036f]/g,"").replace(/[^a-z0-9 ]/g," ").replace(/\\s+/g," ").trim();
    const tokens=s=>norm(s).split(" ").filter(w=>w.length>=4);
    const evidenceFor=label=>{
      const lt=tokens(label);
      if(!lt.length)return {proof:null,level:null};
      let best=null,bestScore=0;
      evidence.forEach(ev=>{
        const et=tokens(ev);
        const common=lt.filter(t=>et.includes(t)).length;
        const score=common/Math.max(1,Math.min(lt.length,et.length));
        if(common>=1&&score>bestScore){best=ev;bestScore=score}
      });
      if(best&&bestScore>=0.60)return {proof:best,level:"check"};
      if(best&&bestScore>=0.34)return {proof:best,level:"mid"};
      return {proof:null,level:null};
    };
    const counts={check:0,mid:0,ask:0};
    list.innerHTML=items.map(item=>{
      const match=evidenceFor(item.libelle);
      const proof=match.proof;
      const state=match.level||"ask";
      counts[state]++;
      counts[state]++;\n      const symbol=state==="check"?"✓":state==="mid"?"△":"?";
      const note=state==="check"
        ? 'Élément proche repéré dans le CV : « '+esc(proof)+' ». À confirmer dans son contexte.'
        : state==="mid"
          ? 'Indice partiel repéré dans le CV : « '+esc(proof)+' ». À préciser avec le candidat avant de considérer la compétence comme maîtrisée.'
          : "Compétence attendue par le métier : à vérifier avec le candidat. Elle ne doit pas être considérée comme acquise sans élément dans le CV.";
      return '<div class="skill-row" data-skill-state="'+state+'"><span class="skill-state '+state+'">'+symbol+'</span><div><strong>'+esc(item.libelle)+'</strong><p>'+note+'</p></div></div>';
    }).join("");
    document.getElementById("skillCountCheck").textContent=counts.check;
    document.getElementById("skillCountMid").textContent=counts.mid;
    document.getElementById("skillCountAsk").textContent=counts.ask;
    document.getElementById("skillCountAll").textContent=items.length;
    document.querySelectorAll("[data-skill-filter]").forEach(btn=>{
      btn.classList.toggle("active",btn.dataset.skillFilter==="all");
      btn.onclick=()=>{
        const filter=btn.dataset.skillFilter;
        document.querySelectorAll("[data-skill-filter]").forEach(x=>x.classList.toggle("active",x===btn));
        document.querySelectorAll("#skillsList .skill-row").forEach(row=>{row.hidden=filter!=="all"&&row.dataset.skillState!==filter});
      };
    });
  }catch(e){
    list.innerHTML='<div class="rome-loading">Les compétences ROME sont momentanément indisponibles. Réessayez dans quelques instants.</div>';
  }
}
function openSkillsView(){
  homeSections.forEach(x=>x.hidden=true);cvDiagnostic.hidden=true;skillsView.hidden=false;renderSkills();window.scrollTo({top:0,behavior:"smooth"});
  document.querySelectorAll(".sidebar a").forEach(a=>a.classList.remove("active"));const link=document.querySelector('.sidebar a[href="#competences"]');if(link)link.classList.add("active");
}
document.querySelectorAll('[data-view="skills"],.sidebar a[href="#competences"]').forEach(el=>el.addEventListener("click",e=>{e.preventDefault();openSkillsView()}));
document.getElementById("skillsBackHome").addEventListener("click",()=>{skillsView.hidden=true;openHome()});


const offersView=document.getElementById("offersView");
async function renderOffers(){
  const empty=document.getElementById("offersEmpty"),content=document.getElementById("offersContent"),list=document.getElementById("offersList"),target=document.getElementById("offersTarget");
  let job=null;try{job=JSON.parse(sessionStorage.getItem("perspectives_target_job"))}catch(e){}
  if(!job){empty.hidden=false;content.hidden=true;empty.textContent="Choisissez d’abord un métier ROME depuis l’accueil pour rechercher des offres.";return}
  empty.hidden=true;content.hidden=false;
  target.innerHTML='<span>Métier recherché</span><strong>'+esc(job.libelle)+'</strong><b>ROME '+esc(job.code)+'</b>';
  list.innerHTML='<div class="rome-loading">Recherche des offres France Travail…</div>';
  try{
    const r=await fetch(API_BASE.replace(/\/$/,"")+"/api/offres?code_rome="+encodeURIComponent(job.code));
    if(!r.ok)throw new Error();
    const data=await r.json(),items=data.offres||[];
    if(!items.length){list.innerHTML='<div class="rome-loading">Aucune offre trouvée pour ce métier.</div>';return}
    const saved=JSON.parse(sessionStorage.getItem("perspectives_compare_offers")||"[]");
    const selected=new Set(saved.map(x=>x.id));
    list.innerHTML=items.map(o=>'<div class="skill-row offer-row"><div><strong>'+esc(o.intitule)+'</strong><p>'+esc([o.entreprise,o.lieu,o.typeContrat].filter(Boolean).join(" · "))+'</p></div><div class="offer-actions"><button type="button" class="compare-offer '+(selected.has(o.id)?'selected':'')+'" data-offer-id="'+esc(o.id)+'">'+(selected.has(o.id)?'✓ Ajoutée':'＋ Comparer')+'</button><a href="'+esc(o.url)+'" target="_blank" rel="noopener">Voir l’offre →</a></div></div>').join("");
    document.querySelectorAll(".compare-offer").forEach(btn=>btn.onclick=()=>{
      const offer=items.find(x=>String(x.id)===btn.dataset.offerId); if(!offer)return;
      let current=JSON.parse(sessionStorage.getItem("perspectives_compare_offers")||"[]");
      const exists=current.some(x=>String(x.id)===String(offer.id));
      current=exists?current.filter(x=>String(x.id)!==String(offer.id)):[...current,offer];
      sessionStorage.setItem("perspectives_compare_offers",JSON.stringify(current));
      btn.classList.toggle("selected",!exists);btn.textContent=!exists?"✓ Ajoutée":"＋ Comparer";
    });
  }catch(e){list.innerHTML='<div class="rome-loading">Les offres France Travail sont momentanément indisponibles.</div>'}
}
function openOffersView(){
  homeSections.forEach(x=>x.hidden=true);cvDiagnostic.hidden=true;skillsView.hidden=true;offersView.hidden=false;renderOffers();window.scrollTo({top:0,behavior:"smooth"});
  document.querySelectorAll(".sidebar a").forEach(a=>a.classList.remove("active"));const link=document.querySelector('.sidebar a[href="#offres"]');if(link)link.classList.add("active");
}
document.querySelectorAll('[data-view="offers"],.sidebar a[href="#offres"]').forEach(el=>el.addEventListener("click",e=>{e.preventDefault();openOffersView()}));
document.getElementById("offersBackHome").addEventListener("click",()=>{offersView.hidden=true;openHome()});


const comparisonView=document.getElementById("comparisonView");
function renderComparison(){
  const empty=document.getElementById("comparisonEmpty"),content=document.getElementById("comparisonContent");
  let offers=[],cv=null;
  try{offers=JSON.parse(sessionStorage.getItem("perspectives_compare_offers")||"[]")}catch(e){}
  try{cv=JSON.parse(sessionStorage.getItem("perspectives_cv_analysis"))}catch(e){}
  if(!offers.length){empty.hidden=false;content.hidden=true;empty.textContent="Sélectionnez au moins une offre depuis le module Offres avec le bouton « ＋ Comparer ».";return}
  empty.hidden=true;content.hidden=false;
  const evidence=(cv&&cv.competences_cv)||[];
  content.innerHTML=offers.map(o=>{
    const requirements=[...(o.competences||[])];
    if(o.experience) requirements.push("Expérience : "+o.experience);
    let counts={check:0,mid:0,ask:0};\n    const rows=requirements.slice(0,12).map(req=>{
      const nr=normalizeSkill(req);let best="",score=0;
      evidence.forEach(ev=>{const s=overlapScore(nr,normalizeSkill(ev));if(s>score){score=s;best=ev}});
      const state=score>=.60?"check":score>=.34?"mid":"ask";
      const symbol=state==="check"?"✓":state==="mid"?"△":"?";
      const note=state==="check"?'Élément proche dans le CV : « '+esc(best)+' ».':state==="mid"?'Indice partiel dans le CV : « '+esc(best)+' ». À préciser.':"Aucun élément suffisamment explicite détecté dans le CV.";
      return '<div class="comparison-requirement"><span class="skill-state '+state+'">'+symbol+'</span><div><strong>'+esc(req)+'</strong><p>'+note+'</p></div></div>';
    }).join("");
    const desc=o.description?'<details class="offer-description"><summary>Voir le contenu de l’offre utilisé pour l’analyse</summary><p>'+esc(o.description)+'</p></details>':"";
    const summary='<div class="comparison-summary"><span class="check">✓ Identifiée <b>'+counts.check+'</b></span><span class="mid">△ À préciser <b>'+counts.mid+'</b></span><span class="ask">? À vérifier <b>'+counts.ask+'</b></span></div>';\n    return '<article class="comparison-card"><div class="comparison-title"><div><span>Offre sélectionnée</span><h3>'+esc(o.intitule)+'</h3><p>'+esc([o.entreprise,o.lieu,o.typeContrat].filter(Boolean).join(" · "))+'</p></div></div>'+summary+'<div class="comparison-requirements">'+(rows||'<p>Aucune compétence structurée fournie par cette offre.</p>')+'</div>'+desc+'<a href="'+esc(o.url)+'" target="_blank" rel="noopener">Consulter l’offre France Travail →</a></article>';
  }).join("");
}
function openComparisonView(){
  homeSections.forEach(x=>x.hidden=true);document.querySelectorAll(".diagnostic-view").forEach(x=>x.hidden=true);comparisonView.hidden=false;renderComparison();window.scrollTo({top:0,behavior:"smooth"});
  document.querySelectorAll(".sidebar a").forEach(a=>a.classList.remove("active"));const link=document.querySelector('.sidebar a[href="#comparaison"]');if(link)link.classList.add("active");
}
document.querySelectorAll('[data-view="comparison"],.sidebar a[href="#comparaison"]').forEach(el=>el.addEventListener("click",e=>{e.preventDefault();openComparisonView()}));
document.getElementById("comparisonBackHome").addEventListener("click",openHome);


const trainingView=document.getElementById("trainingView");
function renderTraining(){
  const empty=document.getElementById("trainingEmpty"),content=document.getElementById("trainingContent"),target=document.getElementById("trainingTarget"),open=document.getElementById("trainingOpen");
  let job=null;try{job=JSON.parse(sessionStorage.getItem("perspectives_target_job"))}catch(e){}
  if(!job){empty.hidden=false;content.hidden=true;empty.textContent="Choisissez d’abord un métier ROME depuis l’accueil pour rechercher une formation.";return}
  empty.hidden=true;content.hidden=false;
  target.innerHTML='<span>Métier recherché</span><strong>'+esc(job.libelle)+'</strong><b>ROME '+esc(job.code)+'</b>';
  open.href="https://candidat.francetravail.fr/formations/recherche?quoi="+encodeURIComponent(job.libelle);
}
function openTrainingView(){
  homeSections.forEach(x=>x.hidden=true);document.querySelectorAll(".diagnostic-view").forEach(x=>x.hidden=true);trainingView.hidden=false;renderTraining();window.scrollTo({top:0,behavior:"smooth"});
  document.querySelectorAll(".sidebar a").forEach(a=>a.classList.remove("active"));const link=document.querySelector('.sidebar a[href="#formations"]');if(link)link.classList.add("active");
}
document.querySelectorAll('[data-view="training"],.sidebar a[href="#formations"]').forEach(el=>el.addEventListener("click",e=>{e.preventDefault();openTrainingView()}));
document.getElementById("trainingBackHome").addEventListener("click",openHome);
