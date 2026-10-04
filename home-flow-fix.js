/* Perspectives Emploi — correctif du parcours CV + métier recherché.
   Après analyse du CV, rester sur l'accueil pour laisser choisir le métier. */
(function(){
  let suppressNextAutomaticCvOpen=false;
  const status=document.getElementById('cvStatus');
  if(status){
    new MutationObserver(function(){
      const mode=sessionStorage.getItem('perspectives_home_mode')||'';
      const analysed=!!sessionStorage.getItem('perspectives_cv_analysis');
      if(mode==='compare' && analysed && /analysé avec succès/i.test(status.textContent||'')){
        suppressNextAutomaticCvOpen=true;
        status.textContent='CV analysé avec succès. Choisissez maintenant le métier recherché.';
        if(typeof window.renderSessionSummary==='function')window.renderSessionSummary();
      }
    }).observe(status,{childList:true,subtree:true,characterData:true});
  }

  const originalOpenCvView=window.openCvView;
  if(typeof originalOpenCvView==='function'){
    window.openCvView=function(){
      if(suppressNextAutomaticCvOpen && sessionStorage.getItem('perspectives_home_mode')==='compare'){
        suppressNextAutomaticCvOpen=false;
        if(typeof window.openHome==='function')window.openHome();
        return;
      }
      return originalOpenCvView.apply(this,arguments);
    };
  }
})();