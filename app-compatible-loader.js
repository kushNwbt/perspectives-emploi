/* Perspectives Emploi — CV -> métiers compatibles, garde-fou persistant V1.4 */
(function(){
  let rendering=false,lastSignature='';
  function read(key){try{return JSON.parse(sessionStorage.getItem(key)||'null')}catch(e){return null}}
  function eligible(){return !!read('perspectives_cv_analysis')&&!read('perspectives_target_job')&&!!window.PerspectivesCompatibleJobs}
  function signature(){const cv=read('perspectives_cv_analysis');try{return JSON.stringify(cv).slice(0,500)}catch(e){return String(Date.now())}}
  async function showCompatible(force=false){
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
      if(intro)intro.textContent='À partir des métiers, expériences et compétences détectés dans votre CV, explorez les correspondances ROME les plus solides.';
      const sig=signature();
      if(force||host.dataset.loaded!=='1'||lastSignature!==sig){
        host.dataset.loaded='1';lastSignature=sig;
        await window.PerspectivesCompatibleJobs.render(host);
      }
      return true;
    }finally{rendering=false}
  }
  function schedule(force=false){setTimeout(()=>showCompatible(force),80);setTimeout(()=>showCompatible(force),350);setTimeout(()=>showCompatible(force),900)}
  const observer=new MutationObserver(()=>{if(eligible())schedule(false)});
  function start(){
    const view=document.getElementById('skillsView'),empty=document.getElementById('skillsEmpty');
    if(view)observer.observe(view,{attributes:true,attributeFilter:['hidden']});
    if(empty)observer.observe(empty,{childList:true,subtree:true,characterData:true});
    document.addEventListener('click',e=>{
      const t=e.target.closest&&e.target.closest('.sidebar a[href="#competences"],[data-view="skills"],[data-journey="skills"]');
      if(t) schedule(true);
    },true);
    window.addEventListener('hashchange',()=>{if(location.hash==='#competences')schedule(true)});
    schedule(false);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
  window.openCompatibleJobsView=()=>showCompatible(true);
})();