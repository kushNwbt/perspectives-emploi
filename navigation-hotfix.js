/* Deterministic CV -> compatible jobs route. No dependency on legacy view navigation. */
(function(){
  var ROUTE='compatible';

  function showCompatiblePage(){
    if(!sessionStorage.getItem('perspectives_cv_analysis')) return false;
    sessionStorage.removeItem('perspectives_target_job');
    var main=document.querySelector('main');
    var view=document.getElementById('skillsView');
    if(!main||!view) return false;

    Array.prototype.forEach.call(main.children,function(el){el.hidden=true});
    view.hidden=false;

    var intro=document.getElementById('skillsIntro');
    var empty=document.getElementById('skillsEmpty');
    var content=document.getElementById('skillsContent');
    if(intro) intro.textContent='À partir des métiers, expériences et compétences détectés dans votre CV, explorez les correspondances ROME les plus solides.';
    if(content) content.hidden=true;
    if(empty){
      empty.hidden=false;
      empty.innerHTML='<div id="compatibleJobsHost"><div class="rome-loading"><strong>Recherche des métiers compatibles en cours…</strong><br>Analyse du CV et correspondance avec le référentiel ROME.</div></div>';
    }

    Array.prototype.forEach.call(document.querySelectorAll('.sidebar a'),function(a){a.classList.remove('active')});
    var link=document.querySelector('.sidebar a[href="#competences"]');
    if(link) link.classList.add('active');

    var host=document.getElementById('compatibleJobsHost');
    if(host&&window.PerspectivesCompatibleJobs&&typeof window.PerspectivesCompatibleJobs.render==='function'){
      window.PerspectivesCompatibleJobs.render(host).catch(function(err){
        console.error(err);
        host.innerHTML='<div class="compatible-empty">La recherche a rencontré une erreur. Utilisez « Retour à l’accueil » puis relancez la recherche.</div>';
      });
    }else if(host){
      host.innerHTML='<div class="compatible-empty">Le module métiers n’a pas pu démarrer. Rechargez cette page.</div>';
    }
    window.scrollTo(0,0);
    return true;
  }

  function goToCompatiblePage(){
    if(!sessionStorage.getItem('perspectives_cv_analysis')) return;
    sessionStorage.removeItem('perspectives_target_job');
    /* Full same-origin reload preserves sessionStorage and eliminates all legacy click/view races. */
    location.href='/?view='+ROUTE+'&v=20261005-2';
  }

  document.addEventListener('click',function(e){
    var b=e.target.closest&&e.target.closest('#homeLaunch');
    if(!b) return;
    var mode=sessionStorage.getItem('perspectives_home_mode')||'';
    if(mode!=='discover'||b.disabled) return;
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    goToCompatiblePage();
  },true);

  var params=new URLSearchParams(location.search);
  if(params.get('view')===ROUTE){
    /* Run after all scripts/controllers have initialized, then take final ownership of the screen. */
    setTimeout(showCompatiblePage,50);
    setTimeout(function(){
      var view=document.getElementById('skillsView');
      if(view&&view.hidden) showCompatiblePage();
    },500);
  }

  window.openCompatibleJobsDirect=goToCompatiblePage;
})();