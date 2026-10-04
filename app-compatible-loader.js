document.addEventListener('DOMContentLoaded',()=>{
  const skillsLink=document.querySelector('.sidebar a[href="#competences"]');
  const skillsCard=document.querySelector('[data-view="skills"]');
  async function showCompatible(e){
    let cv=null,job=null;
    try{cv=JSON.parse(sessionStorage.getItem('perspectives_cv_analysis'))}catch(_){}
    try{job=JSON.parse(sessionStorage.getItem('perspectives_target_job'))}catch(_){}
    if(!cv||job||!window.PerspectivesCompatibleJobs)return;
    if(e){e.preventDefault();e.stopImmediatePropagation()}
    document.querySelectorAll('.diagnostic-view').forEach(x=>x.hidden=true);
    document.querySelectorAll('main > section:not(.diagnostic-view), main > footer').forEach(x=>x.hidden=true);
    const view=document.getElementById('skillsView');view.hidden=false;
    const content=document.getElementById('skillsContent');if(content)content.hidden=true;
    const empty=document.getElementById('skillsEmpty');empty.hidden=false;empty.innerHTML='<div id="compatibleJobsHost"></div>';
    const intro=document.getElementById('skillsIntro');if(intro)intro.textContent='Métiers proposés automatiquement à partir des compétences identifiées dans le CV.';
    document.querySelectorAll('.sidebar a').forEach(a=>a.classList.remove('active'));if(skillsLink)skillsLink.classList.add('active');
    await window.PerspectivesCompatibleJobs.render(document.getElementById('compatibleJobsHost'));
    window.scrollTo({top:0,behavior:'smooth'});
  }
  if(skillsLink)skillsLink.addEventListener('click',showCompatible,true);
  if(skillsCard)skillsCard.addEventListener('click',showCompatible,true);
});