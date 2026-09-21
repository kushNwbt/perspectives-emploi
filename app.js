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
    showStatus("CV analysé avec succès. Ouverture du diagnostic…","ok");
    renderSessionSummary();
    setTimeout(()=>openCvView(),250);
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
function normalizeSkill(value){return String(value||"").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9 ]/g," ").replace(/\s+/g," ").trim()}
function overlapScore(a,b){const left=a.split(" ").filter(x=>x.length>=4),right=new Set(b.split(" ").filter(x=>x.length>=4));if(!left.length||!right.size)return 0;return left.filter(x=>right.has(x)).length/Math.max(1,Math.min(left.length,right.size))}
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
function cvSectionAdvice(name,ok){const map={Expériences:["Décrire les postes, structures, dates et missions principales.","Les expériences sont repérées dans le document."],Compétences:["Créer une rubrique lisible avec les savoir-faire réellement maîtrisés.","Une rubrique de compétences est repérée."],Formation:["Indiquer les diplômes, titres et certifications utiles avec leurs dates.","La formation est repérée."],Coordonnées:["Ajouter un téléphone ou une adresse e-mail professionnelle clairement visible.","Un moyen de contact est repéré."]};const m=map[name]||["À vérifier avec le candidat.","Élément repéré."];return ok?m[1]:m[0]}
function openCvView(){
  hideAllViews(); cvDiagnostic.hidden=false; renderCvDiagnostic(); window.scrollTo({top:0,behavior:"smooth"});
  document.querySelectorAll(".sidebar a").forEach(a=>a.classList.remove("active")); const link=document.querySelector('.sidebar a[href="#cv"]'); if(link)link.classList.add("active");
}
function renderSessionSummary(){
  const box=document.getElementById("sessionSummary");if(!box)return;
  let cv=null,job=null,offers=[];try{cv=JSON.parse(sessionStorage.getItem("perspectives_cv_analysis"))}catch(e){}try{job=JSON.parse(sessionStorage.getItem("perspectives_target_job"))}catch(e){}try{offers=JSON.parse(sessionStorage.getItem("perspectives_compare_offers")||"[]")}catch(e){}
  const commune=sessionStorage.getItem("perspectives_offers_commune")||"";
  if(!cv&&!job&&!offers.length&&!commune){box.hidden=true;box.innerHTML="";return}
  const parts=[cv?"CV analysé":"CV à importer",job?esc(job.label||job.libelle||job.intitule||job.code||"Métier sélectionné"):"Métier à définir",offers.length+" offre"+(offers.length>1?"s":"")+" sélectionnée"+(offers.length>1?"s":"")];if(commune)parts.push("Zone : "+esc(commune));
  box.hidden=false;box.innerHTML='<strong>Session en cours</strong><span>'+parts.join(" · ")+'</span><button id="sessionContinue" type="button">Continuer →</button>';
  document.getElementById("sessionContinue").addEventListener("click",()=>{if(offers.length&&cv)return openComparisonView();if(job)return openOffersView();if(cv)return openSkillsView();openCvView()});
}

function hideAllViews(){document.querySelectorAll(".diagnostic-view").forEach(x=>x.hidden=true);homeSections.forEach(x=>x.hidden=true)}
function openHome(){renderSessionSummary();
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
    window.currentRomeSkillsData=data;
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
      const symbol=state==="check"?"✓":state==="mid"?"△":"?";
      const note=state==="check"
        ? 'Élément proche repéré dans le CV : « '+esc(proof)+' ». À confirmer dans son contexte.'
        : state==="mid"
          ? 'Indice partiel repéré dans le CV : « '+esc(proof)+' ». À préciser avec le candidat avant de considérer la compétence comme maîtrisée.'
          : "Compétence attendue par le métier : à vérifier avec le candidat. Elle ne doit pas être considérée comme acquise sans élément dans le CV.";
      return '<div class="skill-row" data-skill-type="'+esc(item.type||"savoir_faire")+'" data-skill-state="'+state+'"><span class="skill-state '+state+'">'+symbol+'</span><div><strong>'+esc(item.libelle)+'</strong><p>'+note+'</p></div></div>';
    }).join("");
    document.getElementById("skillCountCheck").textContent=counts.check;
    document.getElementById("skillCountMid").textContent=counts.mid;
    document.getElementById("skillCountAsk").textContent=counts.ask;
    document.getElementById("skillCountAll").textContent=items.length;
    applySkillsTab();
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
  hideAllViews(); skillsView.hidden=false;renderSkills();window.scrollTo({top:0,behavior:"smooth"});
  document.querySelectorAll(".sidebar a").forEach(a=>a.classList.remove("active"));const link=document.querySelector('.sidebar a[href="#competences"]');if(link)link.classList.add("active");
}
document.querySelectorAll('[data-view="skills"],.sidebar a[href="#competences"]').forEach(el=>el.addEventListener("click",e=>{e.preventDefault();openSkillsView()}));
document.getElementById("skillsBackHome").addEventListener("click",()=>{skillsView.hidden=true;openHome()});


const offersView=document.getElementById("offersView");
async function renderOffers(){
  const selectionSummary=document.getElementById("offersSelectionSummary");
  const selectedOffers=JSON.parse(sessionStorage.getItem("perspectives_compare_offers")||"[]");
  if(selectedOffers.length){selectionSummary.hidden=false;selectionSummary.innerHTML='<strong>'+selectedOffers.length+' offre'+(selectedOffers.length>1?'s':'')+' sélectionnée'+(selectedOffers.length>1?'s':'')+'</strong> sur 5 pour comparaison <button id="offersGoComparison" type="button">Voir la comparaison →</button>';document.getElementById("offersGoComparison").addEventListener("click",openComparisonView)}else{selectionSummary.hidden=true;selectionSummary.innerHTML=""}

  const empty=document.getElementById("offersEmpty"),content=document.getElementById("offersContent"),list=document.getElementById("offersList"),target=document.getElementById("offersTarget");
  const communeInput=document.getElementById("offersZoneValue");
  const zoneType=document.getElementById("offersZoneType");
  const radius=document.getElementById("offersDistance");
  if(communeInput&&!communeInput.value) communeInput.value=sessionStorage.getItem("perspectives_offers_commune")||"";
  let job=null;try{job=JSON.parse(sessionStorage.getItem("perspectives_target_job"))}catch(e){}
  if(!job){empty.hidden=false;content.hidden=true;empty.textContent="Choisissez d’abord un métier ROME depuis l’accueil pour rechercher des offres.";return}
  empty.hidden=true;content.hidden=false;
  target.innerHTML='<span>Métier recherché</span><strong>'+esc(job.libelle)+'</strong><b>ROME '+esc(job.code)+'</b>';
  list.innerHTML='<div class="rome-loading">Recherche des offres France Travail…</div>';
  try{
    const commune=(document.getElementById("offersZoneValue").value||"").trim();
    if(commune) sessionStorage.setItem("perspectives_offers_commune",commune); else sessionStorage.removeItem("perspectives_offers_commune");
    const geoType=zoneType?.value||"national";
    const distanceValue=parseInt(radius?.value||"0",10)||0;
    let geoQuery="";
    if(geoType==="commune"&&commune)geoQuery="&commune="+encodeURIComponent(commune)+(distanceValue?"&distance="+encodeURIComponent(distanceValue):"");
    else if(geoType==="departement"&&commune)geoQuery="&departement="+encodeURIComponent(commune);
    else if(geoType==="region"&&commune)geoQuery="&region="+encodeURIComponent(commune);
    const r=await fetch(API_BASE.replace(/\/$/,"")+"/api/offres?code_rome="+encodeURIComponent(job.code)+geoQuery);
    if(!r.ok)throw new Error();
    const data=await r.json(),items=data.offres||[];
    if(!items.length){list.innerHTML='<div class="rome-loading">Aucune offre trouvée pour ce métier'+(commune?' dans la zone « '+esc(commune)+' »':'')+'. '+(commune?'Essayez une autre commune ou videz le filtre pour élargir la recherche.':'Vous pouvez réessayer plus tard ou modifier le métier ciblé.')+'</div>';return}
    const saved=JSON.parse(sessionStorage.getItem("perspectives_compare_offers")||"[]");
    const selected=new Set(saved.map(x=>x.id));
    list.innerHTML=items.map(o=>'<div class="skill-row offer-row"><div><strong>'+esc(o.intitule)+'</strong><p>'+esc([o.entreprise,o.lieu,o.typeContrat].filter(Boolean).join(" · "))+'</p></div><div class="offer-actions"><button type="button" class="compare-offer '+(selected.has(o.id)?'selected':'')+'" data-offer-id="'+esc(o.id)+'">'+(selected.has(o.id)?'✓ Ajoutée':'＋ Comparer')+'</button><a href="'+esc(o.url)+'" target="_blank" rel="noopener">Voir l’offre →</a></div></div>').join("");
    document.querySelectorAll(".compare-offer").forEach(btn=>btn.onclick=()=>{
      const offer=items.find(x=>String(x.id)===btn.dataset.offerId); if(!offer)return;
      let current=JSON.parse(sessionStorage.getItem("perspectives_compare_offers")||"[]");
      const exists=current.some(x=>String(x.id)===String(offer.id));
      if(!exists&&current.length>=5){const selectionSummary=document.getElementById("offersSelectionSummary");selectionSummary.hidden=false;selectionSummary.innerHTML='<strong>5 offres sélectionnées sur 5.</strong> Retirez une offre avant d’en ajouter une autre. <button id="offersGoComparison" type="button">Gérer la sélection →</button>';document.getElementById("offersGoComparison").addEventListener("click",openComparisonView);return}
      current=exists?current.filter(x=>String(x.id)!==String(offer.id)):[...current,offer];
      sessionStorage.setItem("perspectives_compare_offers",JSON.stringify(current));
      btn.classList.toggle("selected",!exists);btn.textContent=!exists?"✓ Ajoutée":"＋ Comparer";
      const selectionSummary=document.getElementById("offersSelectionSummary");
      if(current.length){selectionSummary.hidden=false;selectionSummary.innerHTML='<strong>'+current.length+' offre'+(current.length>1?'s':'')+' sélectionnée'+(current.length>1?'s':'')+'</strong> pour comparaison <button id="offersGoComparison" type="button">Voir la comparaison →</button>';document.getElementById("offersGoComparison").addEventListener("click",openComparisonView)}else{selectionSummary.hidden=true;selectionSummary.innerHTML=""}
    });
  }catch(e){list.innerHTML='<div class="rome-loading">Les offres France Travail sont momentanément indisponibles.</div>'}
}
function openOffersView(){
  hideAllViews(); offersView.hidden=false;renderOffers();window.scrollTo({top:0,behavior:"smooth"});
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
  const selectionCount=document.getElementById("comparisonSelectionCount");selectionCount.textContent=offers.length?offers.length+" offre"+(offers.length>1?"s":"")+" sélectionnée"+(offers.length>1?"s":"")+" sur 5":"";selectionCount.hidden=!offers.length;
  const clearOffers=document.getElementById("comparisonClearOffers");clearOffers.hidden=!offers.length;
  document.getElementById("comparisonReviewCv").hidden=!cv;
  let targetJob=null;try{targetJob=JSON.parse(sessionStorage.getItem("perspectives_target_job"))}catch(e){}
  document.getElementById("comparisonReviewSkills").hidden=!targetJob;
  const addOffers=document.getElementById("comparisonAddOffers");addOffers.hidden=!targetJob;
  if(!offers.length){empty.hidden=false;content.hidden=true;empty.innerHTML='<p>Sélectionnez au moins une offre depuis le module Offres avec le bouton « ＋ Comparer ».</p><button id="comparisonEmptyOffers" type="button">Rechercher des offres →</button>';document.getElementById("comparisonEmptyOffers").addEventListener("click",openOffersView);return}
  if(!cv){empty.hidden=false;content.hidden=true;empty.innerHTML='<p>Les offres sont sélectionnées, mais aucun CV n’est encore analysé.</p><button id="comparisonEmptyCv" type="button">Importer et analyser un CV →</button>';document.getElementById("comparisonEmptyCv").addEventListener("click",openCvView);return}
  empty.hidden=true;content.hidden=false;
  const evidence=(cv&&cv.competences_cv)||[];
  content.innerHTML=offers.map(o=>{
    const requirements=[...(o.competences||[])];
    if(o.experience) requirements.push("Expérience : "+o.experience);
    let counts={check:0,mid:0,ask:0};
    const rows=requirements.slice(0,12).map(req=>{
      const nr=normalizeSkill(req);let best="",score=0;
      evidence.forEach(ev=>{const s=overlapScore(nr,normalizeSkill(ev));if(s>score){score=s;best=ev}});
      const state=score>=.60?"check":score>=.34?"mid":"ask";
      counts[state]++;
      const symbol=state==="check"?"✓":state==="mid"?"△":"?";
      const note=state==="check"?'Élément proche dans le CV : « '+esc(best)+' ».':state==="mid"?'Indice partiel dans le CV : « '+esc(best)+' ». À préciser.':"Aucun élément suffisamment explicite détecté dans le CV.";
      return '<div class="comparison-requirement"><span class="skill-state '+state+'">'+symbol+'</span><div><strong>'+esc(req)+'</strong><p>'+note+'</p></div></div>';
    }).join("");
    const desc=o.description?'<details class="offer-description"><summary>Voir le contenu de l’offre utilisé pour l’analyse</summary><p>'+esc(o.description)+'</p></details>':"";
    const summary='<div class="comparison-summary"><span class="check">✓ Identifiée <b>'+counts.check+'</b></span><span class="mid">△ À préciser <b>'+counts.mid+'</b></span><span class="ask">? À vérifier <b>'+counts.ask+'</b></span></div>';
    return '<article class="comparison-card"><div class="comparison-title"><div><span>Offre sélectionnée</span><h3>'+esc(o.intitule)+'</h3><p>'+esc([o.entreprise,o.lieu,o.typeContrat].filter(Boolean).join(" · "))+'</p></div><button type="button" class="comparison-remove" data-remove-offer="'+esc(o.id)+'">Retirer</button></div>'+summary+'<div class="comparison-requirements">'+(rows||'<p>Aucune compétence structurée fournie par cette offre.</p>')+'</div>'+desc+'<a href="'+esc(o.url)+'" target="_blank" rel="noopener">Consulter l’offre France Travail →</a></article>';
  }).join("");
  content.querySelectorAll(".comparison-remove").forEach(btn=>btn.addEventListener("click",()=>{
    const updated=offers.filter(o=>String(o.id)!==String(btn.dataset.removeOffer));
    sessionStorage.setItem("perspectives_compare_offers",JSON.stringify(updated));
    renderComparison();
  }));
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
  const zone=document.getElementById("trainingZone"),summary=document.getElementById("trainingSearchSummary");
  if(zone&&!zone.value)zone.value=sessionStorage.getItem("perspectives_training_zone")||sessionStorage.getItem("perspectives_offers_commune")||"";
  const territory=(zone?.value||"").trim();
  open.href="https://candidat.francetravail.fr/formations/recherche?quoi="+encodeURIComponent(job.libelle)+(territory?"&ou="+encodeURIComponent(territory):"");
  if(summary)summary.textContent=territory?"Recherche préparée pour « "+job.libelle+" » autour de "+territory+".":"Recherche préparée pour « "+job.libelle+" ». Vous pourrez préciser le lieu dans le catalogue France Travail.";
}
function openTrainingView(){
  homeSections.forEach(x=>x.hidden=true);document.querySelectorAll(".diagnostic-view").forEach(x=>x.hidden=true);trainingView.hidden=false;renderTraining();window.scrollTo({top:0,behavior:"smooth"});
  document.querySelectorAll(".sidebar a").forEach(a=>a.classList.remove("active"));const link=document.querySelector('.sidebar a[href="#formations"]');if(link)link.classList.add("active");
}
document.querySelectorAll('[data-view="training"],.sidebar a[href="#formations"]').forEach(el=>el.addEventListener("click",e=>{e.preventDefault();openTrainingView()}));
document.getElementById("trainingBackHome").addEventListener("click",openHome);
document.getElementById("trainingOpenSkills").addEventListener("click",openSkillsView);
document.getElementById("trainingOpenPlan").addEventListener("click",openPlanView);
const trainingZone=document.getElementById("trainingZone"),trainingClearZone=document.getElementById("trainingClearZone");
if(trainingZone){
  trainingZone.addEventListener("change",()=>{const v=trainingZone.value.trim();if(v)sessionStorage.setItem("perspectives_training_zone",v);else sessionStorage.removeItem("perspectives_training_zone");renderTraining()});
  trainingZone.addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();trainingZone.blur();}});
}
if(trainingClearZone)trainingClearZone.addEventListener("click",()=>{trainingZone.value="";sessionStorage.removeItem("perspectives_training_zone");renderTraining()});


const marketView=document.getElementById("marketView");
async function renderMarket(){
  const empty=document.getElementById("marketEmpty"),content=document.getElementById("marketContent"),target=document.getElementById("marketTarget"),count=document.getElementById("marketOffersCount"),link=document.getElementById("marketJobLink");
  let job=null;try{job=JSON.parse(sessionStorage.getItem("perspectives_target_job"))}catch(e){}
  if(!job){empty.hidden=false;content.hidden=true;empty.textContent="Choisissez d’abord un métier ROME depuis l’accueil pour explorer son marché du travail.";return}
  empty.hidden=true;content.hidden=false;target.innerHTML='<span>Métier analysé</span><strong>'+esc(job.libelle)+'</strong><b>ROME '+esc(job.code)+'</b>';count.textContent="…";
  link.href="https://www.francetravail.fr/candidat/recherche-emploi.html?motsCles="+encodeURIComponent(job.libelle);
  try{const r=await fetch(API_BASE+"/api/offres?code_rome="+encodeURIComponent(job.code));if(!r.ok)throw new Error();const data=await r.json();const offers=Array.isArray(data)?data:(data.offres||[]);count.textContent=offers.length;
    const signals=document.getElementById("marketOfferSignals");
    if(signals){const contracts={};const places={};offers.forEach(o=>{const c=(o.typeContrat||"Non précisé").trim();contracts[c]=(contracts[c]||0)+1;const p=(o.lieu||"Non précisé").trim();places[p]=(places[p]||0)+1});const topContracts=Object.entries(contracts).sort((a,b)=>b[1]-a[1]).slice(0,3);const topPlaces=Object.entries(places).sort((a,b)=>b[1]-a[1]).slice(0,3);signals.innerHTML='<p><b>Contrats dans cet échantillon :</b> '+(topContracts.map(([k,v])=>esc(k)+' ('+v+')').join(" · ")||"—")+'</p><p><b>Localisations les plus présentes :</b> '+(topPlaces.map(([k,v])=>esc(k)+' ('+v+')').join(" · ")||"—")+'</p>';}}
  catch(e){count.textContent="Indisponible";const signals=document.getElementById("marketOfferSignals");if(signals)signals.innerHTML="";}
}
function openMarketView(){
  homeSections.forEach(x=>x.hidden=true);document.querySelectorAll(".diagnostic-view").forEach(x=>x.hidden=true);marketView.hidden=false;renderMarket();window.scrollTo({top:0,behavior:"smooth"});
  document.querySelectorAll(".sidebar a").forEach(a=>a.classList.remove("active"));const link=document.querySelector('.sidebar a[href="#marche"]');if(link)link.classList.add("active");
}
document.querySelectorAll('[data-view="market"],.sidebar a[href="#marche"]').forEach(el=>el.addEventListener("click",e=>{e.preventDefault();openMarketView()}));
document.getElementById("marketBackHome").addEventListener("click",openHome);
document.getElementById("marketOpenOffers").addEventListener("click",openOffersView);
document.getElementById("marketOpenSkills").addEventListener("click",openSkillsView);


const planView=document.getElementById("planView");
function renderPlan(){
  const box=document.getElementById("planContent");let job=null,cv=null,offers=[];
  try{job=JSON.parse(sessionStorage.getItem("perspectives_target_job"))}catch(e){}
  try{cv=JSON.parse(sessionStorage.getItem("perspectives_cv_analysis"))}catch(e){}
  try{offers=JSON.parse(sessionStorage.getItem("perspectives_compare_offers")||"[]")}catch(e){}
  const steps=[
    {done:!!cv,title:"CV",text:cv?"Diagnostic du CV réalisé.":"Importer un CV et consulter son diagnostic."},
    {done:!!job,title:"Projet professionnel",text:job?esc(job.libelle)+" — ROME "+esc(job.code):"Choisir un métier ROME pour cibler la suite du parcours."},
    {done:offers.length>0,title:"Offres à comparer",text:offers.length?offers.length+" offre"+(offers.length>1?"s":"")+" sélectionnée"+(offers.length>1?"s":"")+".":"Sélectionner une ou plusieurs offres à comparer."},
    {done:!!job,title:"Compétences",text:job?"Consulter les compétences du métier et préciser les éléments à vérifier.":"Le métier ROME est nécessaire pour préparer cette étape."},
    {done:false,title:"Prochaine action",text:offers.length?"Ouvrir CV ↔ Offre pour préparer les points à valoriser et à préciser avec le candidat.":job?"Explorer les offres correspondant au métier ciblé.":"Commencer par préciser le métier recherché."}
  ];
  const actions=["cv","skills","offers","skills","next"];
  const completed=[!!cv,!!job,offers.length>0,!!job].filter(Boolean).length;
  const summary='<section class="plan-summary"><div><span>Avancement du parcours</span><strong>'+completed+' / 4 étapes préparées</strong></div><p>'+(job?'Projet : '+esc(job.libelle)+' — ROME '+esc(job.code):'Projet professionnel à préciser')+(offers.length?' · '+offers.length+' offre'+(offers.length>1?'s':'')+' retenue'+(offers.length>1?'s':''):'')+'</p></section>';
  box.innerHTML=summary+steps.map((s,i)=>'<article class="plan-step '+(s.done?"done":"")+'"><span class="plan-number">'+(s.done?"✓":i+1)+'</span><div><h3>'+s.title+'</h3><p>'+s.text+'</p><button class="plan-action" data-plan-action="'+actions[i]+'" type="button">'+(s.done?"Revoir cette étape →":"Ouvrir cette étape →")+'</button></div></article>').join("");
  box.querySelectorAll(".plan-action").forEach(btn=>btn.addEventListener("click",()=>{
    const a=btn.dataset.planAction;
    if(a==="cv"){openCvView();return}
    if(a==="skills"){openSkillsView();return}
    if(a==="offers"){openOffersView();return}
    if(a==="next"){if(offers.length){openComparisonView()}else if(job){openOffersView()}else{openHome()}}
  }));
}
function openPlanView(){
  homeSections.forEach(x=>x.hidden=true);document.querySelectorAll(".diagnostic-view").forEach(x=>x.hidden=true);planView.hidden=false;renderPlan();window.scrollTo({top:0,behavior:"smooth"});
  document.querySelectorAll(".sidebar a").forEach(a=>a.classList.remove("active"));const link=document.querySelector('.sidebar a[href="#plan"]');if(link)link.classList.add("active");
}
document.querySelectorAll('[data-view="plan"],.sidebar a[href="#plan"]').forEach(el=>el.addEventListener("click",e=>{e.preventDefault();openPlanView()}));
document.getElementById("planBackHome").addEventListener("click",openHome);
document.getElementById("planOpenTraining")?.addEventListener("click",openTrainingView);
document.getElementById("planOpenMarket")?.addEventListener("click",openMarketView);
document.getElementById("planPrint")?.addEventListener("click",()=>window.print());


document.getElementById("newSessionBtn").addEventListener("click",()=>{
  const hasData=sessionStorage.getItem("perspectives_cv_analysis")||sessionStorage.getItem("perspectives_target_job")||sessionStorage.getItem("perspectives_compare_offers");
  if(hasData&&!window.confirm("Démarrer une nouvelle analyse ? Le CV, le métier et les offres sélectionnées de cette session seront retirés."))return;
  ["perspectives_cv_analysis","perspectives_target_job","perspectives_compare_offers","perspectives_offers_commune","perspectives_offers_contract","perspectives_training_zone"].forEach(k=>sessionStorage.removeItem(k));
  if(typeof selectedJob!=="undefined") selectedJob=null;
  const jobInput=document.getElementById("jobInput");if(jobInput)jobInput.value="";
  openHome();window.scrollTo({top:0,behavior:"smooth"});
});

document.getElementById("offersSearch").addEventListener("click",renderOffers);
document.getElementById("offersZoneValue").addEventListener("keydown",e=>{if(e.key==="Enter")renderOffers()});
document.getElementById("offersClearGeo").addEventListener("click",()=>{
  document.getElementById("offersZoneType").value="national";
  document.getElementById("offersZoneValue").value="";
  document.getElementById("offersDistance").value="10";
  sessionStorage.removeItem("perspectives_offers_commune");
  syncGeoControls();
  renderOffers();
});

document.getElementById("comparisonAddOffers").addEventListener("click",openOffersView);

document.getElementById("comparisonReviewCv").addEventListener("click",openCvView);

document.getElementById("comparisonReviewSkills").addEventListener("click",openSkillsView);

document.getElementById("comparisonClearOffers").addEventListener("click",()=>{const current=JSON.parse(sessionStorage.getItem("perspectives_compare_offers")||"[]");if(!current.length)return;if(confirm("Vider les offres sélectionnées pour la comparaison ?")){sessionStorage.removeItem("perspectives_compare_offers");renderComparison()}});

const offersZoneType=document.getElementById("offersZoneType"),offersRadius=document.getElementById("offersDistance"),offersZone=document.getElementById("offersZoneValue");
const offersZoneValueWrap=document.getElementById("offersZoneValueWrap"),offersDistanceWrap=document.getElementById("offersDistanceWrap");
function syncGeoControls(){
  const t=offersZoneType.value;
  offersZoneValueWrap.hidden=t==="national";
  offersDistanceWrap.hidden=t!=="commune";
  if(t==="national")offersZone.value="";
  offersZone.placeholder=t==="region"?"Ex. Île-de-France":t==="departement"?"Ex. Yvelines ou 78":"Ex. Trappes, Versailles…";
}
offersZoneType.addEventListener("change",syncGeoControls);syncGeoControls();

// Parité logiciel : navigation interne de Compétences & métiers.
let activeSkillsTab="overview";
function applySkillsTab(){
  document.querySelectorAll("[data-skills-tab]").forEach(b=>b.classList.toggle("active",b.dataset.skillsTab===activeSkillsTab));
  const rows=[...document.querySelectorAll("#skillsList .skill-row")];
  const intro=document.getElementById("skillsIntro");
  const labels={overview:"Vue d’ensemble des compétences ROME comparées au CV.",knowhow:"Savoir-faire professionnels associés au métier.",knowledge:"Savoirs associés au métier.",soft:"Savoir-être professionnels associés au métier.",transfer:"Compétences transférables à valoriser dans plusieurs contextes.",jobs:"Métiers proches à explorer à partir du profil."};
  if(intro)intro.textContent=labels[activeSkillsTab]||labels.overview;
  document.querySelectorAll(".skills-tab-message").forEach(x=>x.remove());
  if(activeSkillsTab==="overview"){rows.forEach(r=>r.hidden=false);return}
  if(activeSkillsTab==="knowhow"){rows.forEach(r=>r.hidden=r.dataset.skillType!=="savoir_faire");return}
  if(activeSkillsTab==="knowledge"){rows.forEach(r=>r.hidden=r.dataset.skillType!=="savoir");return}
  if(activeSkillsTab==="transfer"){rows.forEach(r=>r.hidden=r.dataset.skillState!=="check");return}
  if(activeSkillsTab==="soft"){rows.forEach(r=>r.hidden=true);const list=document.getElementById("skillsList");if(list)list.insertAdjacentHTML("afterbegin",'<div class="skills-tab-message">Les savoir-être ne sont pas déduits automatiquement du CV. Ils doivent être vérifiés avec le candidat avant d’être retenus.</div>');return}
  if(activeSkillsTab==="jobs"){rows.forEach(r=>r.hidden=true);const list=document.getElementById("skillsList");if(list)list.insertAdjacentHTML("afterbegin",'<div class="skills-tab-message">Les métiers proches seront proposés uniquement à partir de données ROME officielles vérifiées. Aucune suggestion n’est inventée à partir du CV.</div>');return}
}
document.querySelectorAll("[data-skills-tab]").forEach(b=>b.addEventListener("click",()=>{document.querySelectorAll(".skills-tab-message").forEach(x=>x.remove());activeSkillsTab=b.dataset.skillsTab;applySkillsTab()}));

const offersContract=document.getElementById("offersContract");if(offersContract){offersContract.value=sessionStorage.getItem("perspectives_offers_contract")||"";offersContract.addEventListener("change",()=>{if(offersContract.value)sessionStorage.setItem("perspectives_offers_contract",offersContract.value);else sessionStorage.removeItem("perspectives_offers_contract")})}

// Une actualisation navigateur démarre une session de travail propre :
// la navigation interne conserve les données, mais F5 ne recharge pas un ancien dossier candidat.
try{
  const navEntry=performance.getEntriesByType("navigation")[0];
  if(navEntry&&navEntry.type==="reload"){
    ["perspectives_cv_analysis","perspectives_target_job","perspectives_compare_offers","perspectives_offers_commune","perspectives_offers_contract"].forEach(k=>sessionStorage.removeItem(k));
    if(typeof selectedJob!=="undefined")selectedJob=null;
  }
}catch(e){}

// Parité logiciel : fil de parcours persistant entre les modules.
const journeyBar=document.getElementById("journeyBar");
const journeyOpeners={cv:openCvView,skills:openSkillsView,offers:openOffersView,comparison:openComparisonView,training:openTrainingView,plan:openPlanView};
function updateJourney(active){if(!journeyBar)return;journeyBar.hidden=!active;document.querySelectorAll("[data-journey]").forEach(b=>{b.classList.toggle("active",b.dataset.journey===active);b.onclick=()=>journeyOpeners[b.dataset.journey]?.()})}
[["openCvView","cv"],["openSkillsView","skills"],["openOffersView","offers"],["openComparisonView","comparison"],["openTrainingView","training"],["openPlanView","plan"]].forEach(([name,key])=>{const original=window[name];if(typeof original==="function")window[name]=function(){original();updateJourney(key)}});

// Synchronisation fiable du fil de parcours, y compris pour les écouteurs déjà enregistrés.
const journeyViewMap={cvDiagnostic:"cv",skillsView:"skills",offersView:"offers",comparisonView:"comparison",trainingView:"training",planView:"plan"};
const journeyObserver=new MutationObserver(()=>{
  const visible=Object.entries(journeyViewMap).find(([id])=>{const el=document.getElementById(id);return el&&!el.hidden});
  if(visible)updateJourney(visible[1]);else if(journeyBar)journeyBar.hidden=true;
});
Object.keys(journeyViewMap).forEach(id=>{const el=document.getElementById(id);if(el)journeyObserver.observe(el,{attributes:true,attributeFilter:["hidden"]})});
