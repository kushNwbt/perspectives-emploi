/* Perspectives Emploi — branchement stable du parcours Compétences V2
   Remplace directement la fonction globale renderSkills d'app.js.
   Plus de MutationObserver, plus d'interception de clic. */
(function(){
  const legacyRenderSkills=window.renderSkills;
  function read(key){try{return JSON.parse(sessionStorage.getItem(key)||'null')}catch(e){return null}}

  async function renderCompatibleJobs(cv){
    const empty=document.getElementById('skillsEmpty');
    const content=document.getElementById('skillsContent');
    const intro=document.getElementById('skillsIntro');
    if(content) content.hidden=true;
    empty.hidden=false;
    if(intro) intro.textContent='À partir des métiers, expériences et compétences détectés dans votre CV, explorez les correspondances ROME les plus solides.';
    empty.innerHTML='<div id="compatibleJobsHost"><div class="rome-loading">Analyse des expériences et compétences du CV avec le référentiel ROME…</div></div>';
    const host=document.getElementById('compatibleJobsHost');
    if(!window.PerspectivesCompatibleJobs){
      host.innerHTML='<div class="rome-loading">Le module de recherche de métiers n’est pas disponible. Rechargez la page.</div>';
      return;
    }
    try{
      await window.PerspectivesCompatibleJobs.render(host);
    }catch(e){
      console.error('Compatible jobs error',e);
      host.innerHTML='<div class="rome-loading">La recherche de métiers compatibles est momentanément indisponible.</div>';
    }
  }

  /* Fonction appelée nativement par openSkillsView() dans app.js. */
  window.renderSkills=async function(){
    const cv=read('perspectives_cv_analysis');
    const job=read('perspectives_target_job');
    const empty=document.getElementById('skillsEmpty');
    const content=document.getElementById('skillsContent');
    const intro=document.getElementById('skillsIntro');

    if(!cv){
      if(empty){empty.hidden=false;empty.textContent='Importez d’abord un CV pour analyser les compétences.'}
      if(content)content.hidden=true;
      if(intro)intro.textContent='Importez un CV pour commencer l’analyse des compétences et des métiers.';
      return;
    }

    if(!job){
      return renderCompatibleJobs(cv);
    }

    if(intro)intro.textContent='Comparez les compétences détectées dans le CV avec le référentiel ROME du métier sélectionné.';
    if(typeof legacyRenderSkills==='function') return legacyRenderSkills();
  };

  /* Le nom global openSkillsView est également remplacé afin que les appels
     provenant des autres modules utilisent toujours le même parcours. */
  const legacyOpenSkillsView=window.openSkillsView;
  window.openSkillsView=function(){
    if(typeof window.hideAllViews==='function') window.hideAllViews();
    else {
      document.querySelectorAll('.diagnostic-view').forEach(x=>x.hidden=true);
      document.querySelectorAll('main > section:not(.diagnostic-view), main > footer').forEach(x=>x.hidden=true);
    }
    const view=document.getElementById('skillsView');
    if(view)view.hidden=false;
    window.renderSkills();
    window.scrollTo({top:0,behavior:'smooth'});
    document.querySelectorAll('.sidebar a').forEach(a=>a.classList.remove('active'));
    const link=document.querySelector('.sidebar a[href="#competences"]');
    if(link)link.classList.add('active');
  };

  window.openCompatibleJobsView=function(){
    sessionStorage.removeItem('perspectives_target_job');
    window.openSkillsView();
  };

  console.info('Perspectives Emploi: Skills V2 native routing active');
})();