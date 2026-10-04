/* Perspectives Emploi: deterministic CV -> compatible jobs transition. */
(function(){
  function hasCv(){return !!sessionStorage.getItem('perspectives_cv_analysis');}

  function renderCompatiblePage(){
    if(!hasCv()) return false;
    sessionStorage.removeItem('perspectives_target_job');

    var main=document.querySelector('main');
    var view=document.getElementById('skillsView');
    if(!main||!view) return false;

    /* Hide only the home/direct-child sections. Do NOT hide skillsView again through a broad selector. */
    Array.prototype.forEach.call(main.children,function(el){
      if(el===view){el.hidden=false;return;}
      if(el.id==='journeyBar'){el.hidden=false;return;}
      el.hidden=true;
    });
    Array.prototype.forEach.call(document.querySelectorAll('.diagnostic-view'),function(el){
      el.hidden=(el!==view);
    });
    view.hidden=false;

    var homeChoice=document.getElementById('homeChoice');
    if(homeChoice) homeChoice.hidden=true;

    var intro=document.getElementById('skillsIntro');
    var empty=document.getElementById('skillsEmpty');
    var content=document.getElementById('skillsContent');
    if(intro) intro.textContent='À partir des métiers, expériences et compétences détectés dans votre CV, explorez les correspondances ROME les plus solides.';
    if(content) content.hidden=true;
    if(!empty) return false;

    empty.hidden=false;
    empty.innerHTML='<div id="compatibleJobsHost"><div class="rome-loading"><strong>Recherche des métiers compatibles en cours…</strong><br>Analyse du CV et correspondance avec le référentiel ROME.</div></div>';
    var host=document.getElementById('compatibleJobsHost');

    Array.prototype.forEach.call(document.querySelectorAll('.sidebar a'),function(a){a.classList.remove('active');});
    var link=document.querySelector('.sidebar a[href="#competences"]');
    if(link) link.classList.add('active');

    if(window.PerspectivesCompatibleJobs&&typeof window.PerspectivesCompatibleJobs.render==='function'){
      Promise.resolve(window.PerspectivesCompatibleJobs.render(host)).catch(function(err){
        console.error('Compatible jobs render failed',err);
        host.innerHTML='<div class="compatible-empty">La recherche des métiers a rencontré une erreur. Revenez à l’accueil puis relancez la recherche.</div>';
      });
    }else{
      host.innerHTML='<div class="compatible-empty">Le moteur de métiers n’est pas chargé. Rechargez la page puis réessayez.</div>';
    }
    window.scrollTo({top:0,behavior:'smooth'});
    return true;
  }

  /* Capture phase: this is the single owner of the discover validation button. */
  document.addEventListener('click',function(e){
    var b=e.target.closest&&e.target.closest('#homeLaunch');
    if(!b) return;
    if((sessionStorage.getItem('perspectives_home_mode')||'')!=='discover'||b.disabled) return;
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    renderCompatiblePage();
  },true);

  window.openCompatibleJobsDirect=renderCompatiblePage;
})();