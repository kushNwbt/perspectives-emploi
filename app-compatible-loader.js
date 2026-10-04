/* Perspectives Emploi — CV -> métiers compatibles, garde-fou persistant */
(function(){
  let rendering=false;
  function read(key){try{return JSON.parse(sessionStorage.getItem(key)||'null')}catch(e){return null}}
  function eligible(){return !!read('perspectives_cv_analysis')&&!read('perspectives_target_job')&&!!window.PerspectivesCompatibleJobs}
  async function showCompatible(){
    if(rendering||!eligible())return false;
    const view=document.getElementById('skillsView'),empty=document.getElementById('skillsEmpty'),content=document.getElementById('skillsContent');
    if(!view||!empty||view.hidden)return false;
    rendering=true;
    try{
      if(content)content.hidden=true;
      empty.hidden=false;
      let host=document.getElementById('compatibleJobsHost');
      if(!host){empty.innerHTML='<div id="compatibleJobsHost"></div>';host=document.getElementById('compatibleJobsHost')}
      const intro=document.getElementById('skillsIntro');
      if(intro)intro.textContent='À partir des compétences détectées dans votre CV, explorez des métiers ROME compatibles sans avoir à choisir un métier cible au préalable.';
      if(!host.dataset.loaded){host.dataset.loaded='1';await window.PerspectivesCompatibleJobs.render(host)}
      return true;
    }finally{rendering=false}
  }
  /* L'ancien renderSkills peut réécrire skillsEmpty après le clic. On observe donc l'écran lui-même :
     dès qu'il devient visible avec CV + aucun métier, le parcours automatique remplace l'ancien message. */
  const observer=new MutationObserver(()=>{if(eligible())queueMicrotask(showCompatible)});
  function start(){
    const view=document.getElementById('skillsView'),empty=document.getElementById('skillsEmpty');
    if(view)observer.observe(view,{attributes:true,attributeFilter:['hidden']});
    if(empty)observer.observe(empty,{childList:true,subtree:true,characterData:true});
    document.addEventListener('click',e=>{
      const t=e.target.closest&&e.target.closest('.sidebar a[href="#competences"],[data-view="skills"]');
      if(t&&eligible())setTimeout(showCompatible,0);
    },true);
    setTimeout(showCompatible,0);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
  window.openCompatibleJobsView=showCompatible;
})();