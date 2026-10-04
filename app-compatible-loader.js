/* Perspectives Emploi — branche le parcours CV -> métiers compatibles sans dépendre du sélecteur historique */
(function(){
  function read(key){try{return JSON.parse(sessionStorage.getItem(key)||'null')}catch(e){return null}}
  async function showCompatible(){
    const cv=read('perspectives_cv_analysis');
    const job=read('perspectives_target_job');
    if(!cv || job || !window.PerspectivesCompatibleJobs) return false;
    if(typeof window.hideAllViews==='function') window.hideAllViews();
    else {
      document.querySelectorAll('.diagnostic-view').forEach(x=>x.hidden=true);
      document.querySelectorAll('main > section:not(.diagnostic-view), main > footer').forEach(x=>x.hidden=true);
    }
    const view=document.getElementById('skillsView');
    const content=document.getElementById('skillsContent');
    const empty=document.getElementById('skillsEmpty');
    if(!view||!empty) return false;
    view.hidden=false;
    if(content) content.hidden=true;
    empty.hidden=false;
    empty.innerHTML='<div id="compatibleJobsHost"></div>';
    const intro=document.getElementById('skillsIntro');
    if(intro) intro.textContent='À partir des compétences détectées dans votre CV, explorez des métiers ROME compatibles sans avoir à choisir un métier cible au préalable.';
    document.querySelectorAll('.sidebar a').forEach(a=>a.classList.remove('active'));
    const link=document.querySelector('.sidebar a[href="#competences"]');
    if(link) link.classList.add('active');
    await window.PerspectivesCompatibleJobs.render(document.getElementById('compatibleJobsHost'));
    window.scrollTo({top:0,behavior:'smooth'});
    return true;
  }
  function intercept(e){
    const target=e.target.closest && e.target.closest('.sidebar a[href="#competences"], [data-view="skills"]');
    if(!target) return;
    const cv=read('perspectives_cv_analysis'),job=read('perspectives_target_job');
    if(!cv||job) return;
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    showCompatible();
  }
  /* Capture sur document : installé après app.js mais exécuté avant les handlers de la cible. */
  document.addEventListener('click',intercept,true);
  window.openCompatibleJobsView=showCompatible;
})();