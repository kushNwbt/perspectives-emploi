/* Direct navigation hotfix: bypass legacy skills navigation for CV -> jobs flow. */
(function(){
  function openCompatibleJobs(){
    if(!sessionStorage.getItem('perspectives_cv_analysis')) return;
    sessionStorage.removeItem('perspectives_target_job');

    var main=document.querySelector('main');
    if(!main) return;

    /* Hide every home block and every other diagnostic view explicitly. */
    Array.prototype.forEach.call(main.children,function(el){
      if(el.id==='journeyBar'||el.id==='skillsView') return;
      el.hidden=true;
    });
    Array.prototype.forEach.call(document.querySelectorAll('.diagnostic-view'),function(el){el.hidden=true});

    var choice=document.getElementById('homeChoice');
    if(choice) choice.hidden=true;

    var bar=document.getElementById('journeyBar');
    if(bar) bar.hidden=false;

    var view=document.getElementById('skillsView');
    if(!view) return;
    view.hidden=false;

    var intro=document.getElementById('skillsIntro');
    var empty=document.getElementById('skillsEmpty');
    var content=document.getElementById('skillsContent');
    if(intro) intro.textContent='À partir des métiers, expériences et compétences détectés dans votre CV, explorez les correspondances ROME les plus solides.';
    if(content) content.hidden=true;
    if(empty){
      empty.hidden=false;
      empty.innerHTML='<div id="compatibleJobsHost"><div class="rome-loading">Analyse des expériences et compétences du CV avec le référentiel ROME…</div></div>';
      var host=document.getElementById('compatibleJobsHost');
      if(window.PerspectivesCompatibleJobs&&typeof window.PerspectivesCompatibleJobs.render==='function'){
        Promise.resolve(window.PerspectivesCompatibleJobs.render(host)).catch(function(err){
          console.error('Compatible jobs navigation hotfix:',err);
          host.innerHTML='<div class="compatible-empty">La recherche de métiers compatibles est momentanément indisponible.</div>';
        });
      }else{
        host.innerHTML='<div class="compatible-empty">Le module de recherche de métiers n’est pas chargé.</div>';
      }
    }

    Array.prototype.forEach.call(document.querySelectorAll('.sidebar a'),function(a){a.classList.remove('active')});
    var link=document.querySelector('.sidebar a[href="#competences"]');
    if(link) link.classList.add('active');
    window.scrollTo({top:0,behavior:'smooth'});
  }

  /* Capture the generated validation button before any legacy onclick can run. */
  document.addEventListener('click',function(e){
    var b=e.target.closest&&e.target.closest('#homeLaunch');
    if(!b) return;
    var mode=sessionStorage.getItem('perspectives_home_mode')||'';
    if(mode!=='discover'||b.disabled) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    openCompatibleJobs();
  },true);

  window.openCompatibleJobsDirect=openCompatibleJobs;
})();