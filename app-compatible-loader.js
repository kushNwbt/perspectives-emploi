/* Perspectives Emploi — branchement stable du parcours Compétences V2 */
(function(){
  /* Garde d'initialisation : évite les blocs d'accueil, styles et écouteurs en double. */
  if(window.__perspectivesCompatibleLoaderLoaded)return;
  window.__perspectivesCompatibleLoaderLoaded=true;

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
    if(!window.PerspectivesCompatibleJobs){host.innerHTML='<div class="rome-loading">Le module de recherche de métiers n’est pas disponible. Rechargez la page.</div>';return;}
    try{await window.PerspectivesCompatibleJobs.render(host)}catch(e){console.error('Compatible jobs error',e);host.innerHTML='<div class="rome-loading">La recherche de métiers compatibles est momentanément indisponible.</div>'}
  }

  window.renderSkills=async function(){
    const cv=read('perspectives_cv_analysis');
    const job=read('perspectives_target_job');
    const empty=document.getElementById('skillsEmpty');
    const content=document.getElementById('skillsContent');
    const intro=document.getElementById('skillsIntro');
    if(!cv){if(empty){empty.hidden=false;empty.textContent='Importez d’abord un CV pour analyser les compétences.'}if(content)content.hidden=true;if(intro)intro.textContent='Importez un CV pour commencer l’analyse des compétences et des métiers.';return;}
    if(!job)return renderCompatibleJobs(cv);
    if(intro)intro.textContent='Comparez les compétences détectées dans le CV avec le référentiel ROME du métier sélectionné.';
    if(typeof legacyRenderSkills==='function') return legacyRenderSkills();
  };

  window.openSkillsView=function(){
    if(typeof window.hideAllViews==='function') window.hideAllViews();
    else {document.querySelectorAll('.diagnostic-view').forEach(x=>x.hidden=true);document.querySelectorAll('main > section:not(.diagnostic-view), main > footer').forEach(x=>x.hidden=true);}
    const view=document.getElementById('skillsView');if(view)view.hidden=false;
    window.renderSkills();window.scrollTo({top:0,behavior:'smooth'});
    document.querySelectorAll('.sidebar a').forEach(a=>a.classList.remove('active'));const link=document.querySelector('.sidebar a[href="#competences"]');if(link)link.classList.add('active');
  };
  window.openCompatibleJobsView=function(){sessionStorage.removeItem('perspectives_target_job');window.openSkillsView()};

  const style=document.createElement('style');
  style.textContent=`
    .home-choice{background:#fff;border:1px solid #e4e6ef;border-radius:22px;padding:28px 30px;margin-top:22px}
    .home-choice h2{margin:0 0 6px;font-size:22px;color:#22275f}.home-choice>p{margin:0 0 20px;color:#777b91;font-size:13px}
    .journey-choices{display:grid;grid-template-columns:1fr 1fr;gap:14px}.journey-choice{border:1px solid #d9ddeb;background:#fff;border-radius:17px;padding:20px;text-align:left;cursor:pointer;color:#22275f;transition:.15s}.journey-choice:hover,.journey-choice.selected{border-color:#283276;background:#f5f6ff;box-shadow:0 7px 20px rgba(40,50,118,.08)}.journey-choice strong{display:block;font-size:16px;margin-bottom:7px}.journey-choice span{display:block;color:#73788e;font-size:12px;line-height:1.45}.journey-choice b{display:inline-block;margin-top:14px;color:#283276;font-size:12px}
    .home-input-hidden{display:none!important}.modules{display:none!important}.sidebar a.nav-locked{opacity:.32;pointer-events:none;filter:grayscale(1)}
    .remove-cv{margin-left:8px!important;background:#fff!important;color:#8b2b2b!important;border:1px solid #e7caca!important}.home-action-row{display:flex;justify-content:flex-end;margin-top:14px}.home-action{border:0;background:#283276;color:#fff;border-radius:11px;padding:12px 18px;font-weight:700;cursor:pointer}.home-action:disabled{opacity:.4;cursor:not-allowed}
    .view-nav-extra{display:flex;gap:8px;margin-left:auto}.view-nav-extra button{border:1px solid #d6d9e7;background:#fff;color:#283276;border-radius:11px;padding:11px 15px;font-weight:700;cursor:pointer}
    @media(max-width:850px){.journey-choices{grid-template-columns:1fr}.view-nav-extra{width:100%;flex-wrap:wrap}}
  `;document.head.appendChild(style);

  const main=document.querySelector('main');
  const welcome=main&&main.querySelector('.welcome');
  const starts=main?[...main.querySelectorAll(':scope > section.start')]:[];
  const modules=main&&main.querySelector(':scope > section.modules');
  let mode=sessionStorage.getItem('perspectives_home_mode')||'';

  if(welcome){
    /* Nettoie aussi un éventuel doublon laissé par une ancienne version mise en cache. */
    document.querySelectorAll('#homeChoice,.home-choice').forEach(x=>x.remove());
    const choice=document.createElement('section');choice.className='home-choice';choice.id='homeChoice';
    choice.innerHTML='<h2>Comment souhaitez-vous commencer ?</h2><p>Choisissez le parcours adapté à la situation du candidat.</p><div class="journey-choices"><button type="button" class="journey-choice" data-mode="discover"><strong>Rechercher un métier à partir d’un CV</strong><span>Analyse le parcours, les expériences et les compétences pour proposer les métiers les plus cohérents.</span><b>CV → métiers compatibles</b></button><button type="button" class="journey-choice" data-mode="compare"><strong>CV + métier recherché</strong><span>Analyse le CV puis le compare à un métier ROME déjà envisagé afin d’identifier les acquis et les écarts.</span><b>CV + métier → comparaison</b></button></div>';
    welcome.insertAdjacentElement('afterend',choice);
  }

  function hasCV(){return !!sessionStorage.getItem('perspectives_cv_analysis')}
  function hasJob(){return !!sessionStorage.getItem('perspectives_target_job')}
  function updateHome(){
    mode=sessionStorage.getItem('perspectives_home_mode')||'';
    document.querySelectorAll('.journey-choice').forEach(b=>b.classList.toggle('selected',b.dataset.mode===mode));
    if(starts[0])starts[0].classList.toggle('home-input-hidden',!mode);
    if(starts[1])starts[1].classList.toggle('home-input-hidden',mode!=='compare');
    if(modules)modules.style.setProperty('display','none','important');
    const hint=starts[0]&&starts[0].querySelector('.section-title p');if(hint)hint.textContent=mode==='compare'?'Importez le CV à comparer au métier recherché.':'Importez le CV pour rechercher les métiers les plus cohérents.';
    updateRemoveCv();updateLocks();updateLaunch();
  }
  function updateRemoveCv(){
    const upload=document.getElementById('cvDropZone');if(!upload)return;let b=document.getElementById('removeCv');
    if(hasCV()&&!b){b=document.createElement('button');b.id='removeCv';b.type='button';b.className='remove-cv';b.textContent='Retirer le CV';upload.appendChild(b);b.onclick=()=>{sessionStorage.removeItem('perspectives_cv_analysis');sessionStorage.removeItem('perspectives_compare_offers');const fi=document.getElementById('cvFile');if(fi)fi.value='';const t=document.getElementById('cvFileTitle');if(t)t.textContent='Importer votre CV';const i=document.getElementById('cvFileInfo');if(i)i.textContent='PDF, DOCX ou TXT · 10 Mo maximum';const s=document.getElementById('cvStatus');if(s)s.hidden=true;updateHome()}}
    if(b)b.hidden=!hasCV();
  }
  function updateLocks(){
    const cv=hasCV(),job=hasJob();
    const rules={'#cv':cv,'#competences':cv,'#offres':cv&&job,'#comparaison':cv&&job,'#formations':cv&&job,'#marche':cv&&job,'#plan':cv&&job};
    document.querySelectorAll('.sidebar a').forEach(a=>{if(a.getAttribute('href')==='#accueil'){a.classList.remove('nav-locked');return}const ok=!!rules[a.getAttribute('href')];a.classList.toggle('nav-locked',!ok);a.setAttribute('aria-disabled',ok?'false':'true')});
  }
  function updateLaunch(){
    if(!starts[0])return;let row=document.getElementById('homeActionRow');if(!row){row=document.createElement('div');row.id='homeActionRow';row.className='home-action-row';row.innerHTML='<button id="homeLaunch" class="home-action" type="button">Continuer →</button>';starts[(mode==='compare'&&starts[1])?1:0].appendChild(row)}
    const target=(mode==='compare'&&starts[1])?starts[1]:starts[0];if(row.parentNode!==target)target.appendChild(row);
    const btn=document.getElementById('homeLaunch');if(!btn)return;btn.disabled=!hasCV()||(mode==='compare'&&!hasJob());btn.textContent=mode==='discover'?'Rechercher les métiers compatibles →':'Comparer le CV au métier →';btn.onclick=()=>{if(btn.disabled)return;if(mode==='discover'){sessionStorage.removeItem('perspectives_target_job');window.openSkillsView()}else window.openSkillsView()};
  }
  document.querySelectorAll('.journey-choice').forEach(b=>b.onclick=()=>{sessionStorage.setItem('perspectives_home_mode',b.dataset.mode);mode=b.dataset.mode;if(mode==='discover'){sessionStorage.removeItem('perspectives_target_job');const rs=document.getElementById('romeSearch');if(rs)rs.value='';const sel=document.getElementById('romeSelected');if(sel){sel.hidden=true;sel.innerHTML=''}}updateHome()});

  const observer=new MutationObserver(()=>{updateLocks();updateLaunch();updateRemoveCv()});
  const status=document.getElementById('cvStatus');if(status)observer.observe(status,{childList:true,attributes:true,subtree:true});
  const selected=document.getElementById('romeSelected');if(selected)observer.observe(selected,{childList:true,attributes:true,subtree:true});

  document.querySelectorAll('.diagnostic-view .diag-head').forEach(head=>{
    const old=head.querySelector('button[id$="BackHome"],#backHome');if(!old)return;
    const wrap=document.createElement('div');wrap.className='view-nav-extra';
    const prev=document.createElement('button');prev.type='button';prev.textContent='← Page précédente';prev.onclick=()=>history.length>1?history.back():window.openHome&&window.openHome();
    old.parentNode.insertBefore(wrap,old);wrap.appendChild(prev);wrap.appendChild(old);old.textContent='⌂ Retour à l’accueil';
  });

  document.querySelector('.sidebar')?.addEventListener('click',e=>{const a=e.target.closest('a.nav-locked');if(a){e.preventDefault();e.stopImmediatePropagation()}},true);

  /* Correctif : dans le parcours CV + métier, l'analyse du CV ne doit pas ouvrir le diagnostic automatiquement. */
  let suppressNextAutomaticCvOpen=false;
  if(status){
    new MutationObserver(()=>{
      if((sessionStorage.getItem('perspectives_home_mode')||'')==='compare' && hasCV() && /analysé avec succès/i.test(status.textContent||'')){
        suppressNextAutomaticCvOpen=true;
        status.textContent='CV analysé avec succès. Choisissez maintenant le métier recherché.';
        updateHome();
      }
    }).observe(status,{childList:true,subtree:true,characterData:true});
  }
  const originalOpenCvView=window.openCvView;
  if(typeof originalOpenCvView==='function'){
    window.openCvView=function(){
      if(suppressNextAutomaticCvOpen && (sessionStorage.getItem('perspectives_home_mode')||'')==='compare'){
        suppressNextAutomaticCvOpen=false;
        if(typeof window.openHome==='function')window.openHome();
        return;
      }
      return originalOpenCvView.apply(this,arguments);
    };
  }

  updateHome();
  console.info('Perspectives Emploi: Skills V2 + accueil guidé actifs');
})();