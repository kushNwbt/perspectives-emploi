import os, sys, json, re, threading, queue, time, urllib.parse, urllib.request, unicodedata
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import customtkinter as ctk

try:
    import fitz
except Exception:
    fitz=None
try:
    from docx import Document
except Exception:
    Document=None

def resource_path(name):
    base=Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name

APP="Perspectives Emploi"
TAG="Votre profil, vos compétences, vos opportunités"
NAVY="#283276"; PURPLE="#008ECF"; BG="#F6F7FB"; CARD="#FFFFFF"
TEXT="#1D2142"; MUTED="#606579"; LINE="#DDE0E8"; GOOD="#18753C"; WARN="#A15C00"; BAD="#E1000F"

CFG_DIR=Path(os.getenv("APPDATA",str(Path.home()))) / "PerspectivesEmploi"
CFG=CFG_DIR/"config.json"
TOKEN_URL="https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire"
ROME_URL="https://api.francetravail.io/partenaire/rome-metiers/v1/metiers/metier/requete"
ROME_SCOPE="nomenclatureRome api_rome-metiersv1"
ROME_FICHE_SCOPE="nomenclatureRome api_rome-fiches-metiersv1"
ROME_FICHE_URL="https://api.francetravail.io/partenaire/rome-fiches-metiers/v1/fiches-rome/fiche-metier/"
ROME_FICHES_LIST_URL="https://api.francetravail.io/partenaire/rome-fiches-metiers/v1/fiches-rome/fiche-metier"
MARKET_BASE="https://api.francetravail.io/partenaire/stats-offres-demandes-emploi"
MARKET_SCOPE="offresetdemandesemploi api_stats-offres-demandes-emploiv1"

def load_cfg():
    try:return json.loads(CFG.read_text(encoding="utf-8"))
    except:return {}

def save_cfg(cid,secret):
    CFG_DIR.mkdir(parents=True,exist_ok=True)
    CFG.write_text(json.dumps({"client_id":cid,"client_secret":secret}),encoding="utf-8")

def token(cid,secret,scope):
    data=urllib.parse.urlencode({"grant_type":"client_credentials","client_id":cid,"client_secret":secret,"scope":scope}).encode()
    req=urllib.request.Request(TOKEN_URL,data=data,headers={"Content-Type":"application/x-www-form-urlencoded"},method="POST")
    with urllib.request.urlopen(req,timeout=20) as r:
        return json.loads(r.read().decode())["access_token"]

def get_json(url,tok):
    req=urllib.request.Request(url,headers={"Authorization":"Bearer "+tok,"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read().decode())

def post_json(url,tok,payload):
    raw=json.dumps(payload).encode("utf-8")
    req=urllib.request.Request(url,data=raw,headers={"Authorization":"Bearer "+tok,"Accept":"application/json","Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=25) as r:return json.loads(r.read().decode())

def read_cv(path):
    ext=Path(path).suffix.lower()
    if ext==".pdf":
        if fitz is None:raise RuntimeError("PyMuPDF n'est pas installé.")
        d=fitz.open(path); return "\n".join(p.get_text("text") for p in d)
    if ext==".docx":
        if Document is None:raise RuntimeError("python-docx n'est pas installé.")
        d=Document(path); out=[p.text for p in d.paragraphs]
        for t in d.tables:
            for row in t.rows:out.append(" | ".join(c.text for c in row.cells))
        return "\n".join(out)
    if ext==".txt":return Path(path).read_text(encoding="utf-8",errors="ignore")
    raise RuntimeError("Format non pris en charge.")

def diagnostic(text,target):
    low=text.lower()
    email=bool(re.search(r"[\w.+-]+@[\w.-]+\.\w+",text))
    phone=bool(re.search(r"(?:\+33|0)[1-9](?:[\s.-]?\d{2}){4}",text))
    years=len(re.findall(r"\b(?:19|20)\d{2}\b",text))
    sec_exp=bool(re.search(r"exp[ée]rience|parcours professionnel",low))
    sec_comp=bool(re.search(r"comp[ée]tence|savoir[- ]faire",low))
    sec_form=bool(re.search(r"formation|dipl[oô]me|certification",low))
    words=len(re.findall(r"\b[\wÀ-ÿ'-]+\b",text))
    target=(target or "").strip()
    target_hit=bool(target and target.lower() in low)
    rows=[]
    def row(name,score,maxi,why,advice,example,state_override=None):
        state=state_override or ("✓ Conforme" if score/maxi>=.8 else "! À améliorer" if score/maxi>=.5 else "✕ Prioritaire")
        rows.append((name,score,maxi,state,why,advice,example))
    row("Coordonnées",10 if email and phone else 6 if email or phone else 2,10,
        "Les coordonnées doivent être immédiatement accessibles.",
        "Afficher téléphone et e-mail en texte lisible.",
        "Avant : coordonnées partielles → Amélioré : 06… • prenom.nom@email.fr")
    n=sum([sec_exp,sec_comp,sec_form])
    row("Structure et rubriques",15 if n==3 else 10 if n==2 else 5,15,
        "Des rubriques standard facilitent la lecture et l'analyse ATS.",
        "Utiliser Expériences professionnelles, Compétences et Formation.",
        "Avant : Mon parcours → Amélioré : EXPÉRIENCES PROFESSIONNELLES")
    if target:
        row("Titre et métier ciblé",15 if target_hit else 8,15,
            "Le métier recherché doit être identifiable immédiatement.",
            f"Faire apparaître clairement le métier ciblé : {target}.",
            f"Avant : Curriculum Vitae → Amélioré : {target}")
    else:
        row("Métier ciblé",15,15,
            "Aucun métier n'a été sélectionné : ce critère n'est pas utilisé pour pénaliser le diagnostic.",
            "Passez ensuite dans « Compétences & métiers » pour explorer des métiers à partir des compétences réellement repérées dans le CV.",
            "Mode exploration : CV → compétences identifiées → métiers à explorer",
            state_override="— Non évalué")
    row("Expériences",18 if sec_exp and years>=4 else 12 if sec_exp else 6,20,
        "Les expériences doivent montrer missions, dates et résultats.",
        "Pour chaque poste : intitulé, employeur, dates, 3 à 5 missions/résultats.",
        "Avant : Accueil clients → Amélioré : Accueil et orientation de 40 usagers/jour")
    row("Compétences",15 if sec_comp else 6,15,
        "Les compétences doivent être faciles à repérer.",
        "Créer une rubrique dédiée avec uniquement les compétences réellement maîtrisées.",
        "Avant : Polyvalent → Amélioré : Conduite d'entretien • Animation d'atelier")
    row("Formation",10 if sec_form else 5,10,
        "Diplômes et certifications permettent de situer le niveau de qualification.",
        "Préciser intitulé, organisme, année et certification utile.",
        "Avant : Formation CIP → Amélioré : Titre professionnel CIP — 2024")
    row("Chronologie",10 if years>=3 else 5,10,
        "Des dates homogènes rendent le parcours compréhensible.",
        "Employer un format constant : MM/AAAA – MM/AAAA.",
        "Avant : 2025 / actuellement → Amélioré : 04/2025 – Aujourd'hui")
    row("Lisibilité / ATS",5 if 180<=words<=1100 and n>=2 else 3,5,
        "Le contenu essentiel doit rester textuel, structuré et lisible.",
        "Éviter de placer les informations essentielles uniquement dans des images.",
        "Objectif : texte sélectionnable + titres standards + contenu concis")
    return min(sum(x[1] for x in rows),100),rows

RADIUS_CARD=22
RADIUS_BUTTON=12
RADIUS_FIELD=10

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP+" — V6.24.5"); self.geometry("1260x780"); self.minsize(1050,680); self.configure(bg=BG)
        self.cv_text=""; self.cv_path=""; self.jobs=[]; self.selected_job=None; self.after_id=None
        self.target=tk.StringVar(); self.location=tk.StringVar(value="Yvelines (78)"); self.status=tk.StringVar(value="Prêt")
        self.offer_extra_jobs=[]
        self.primary_offer_job={}
        self.skills_explore_code=""
        self.nearby_action_buttons={}
        self.rome_subgroup_selection={}
        self.rome_subgroup_preferred={}
        self.rome_fiche_cache={}
        self.rome_fiche_loading=set()
        self.rome_request_queue=queue.Queue()
        self.rome_queued_codes=set()
        self.rome_last_request_at=0.0
        self.rome_min_interval=1.15
        self.rome_nearby_cache={}
        self.rome_nearby_loading=set()

        # Autocomplete ROME Métier has the same 1 request/second constraint.
        self.rome_search_cache={}
        self.rome_search_last_at=0.0
        self.rome_search_seq=0

        threading.Thread(target=self._rome_request_worker,daemon=True).start()
        self.build()

    def build(self):
        h=tk.Frame(self,bg="white",height=112,highlightbackground=LINE,highlightthickness=0); h.pack(fill="x"); h.pack_propagate(False)
        brand=tk.Frame(h,bg="white");brand.pack(side="left",fill="y",padx=(28,0))
        try:
            logo_path=resource_path("bloc_marque_rf_france_travail.jpg")
            im=Image.open(logo_path).convert("RGB")
            im.thumbnail((360,82),Image.LANCZOS)
            self.ft_logo=ImageTk.PhotoImage(im)
            tk.Label(brand,image=self.ft_logo,bg="white",bd=0).pack(side="left",padx=(0,24),pady=8)
        except Exception as ex:
            tk.Label(brand,text="RÉPUBLIQUE FRANÇAISE   |   France Travail",bg="white",fg=NAVY,
                     font=("Segoe UI",10,"bold")).pack(side="left",padx=(0,24),pady=20)
        sep=tk.Frame(brand,bg=LINE,width=1,height=54);sep.pack(side="left",padx=(0,22),pady=20)
        ident=tk.Frame(brand,bg="white");ident.pack(side="left",pady=16)
        tk.Label(ident,text=APP,bg="white",fg=NAVY,font=("Segoe UI",21,"bold")).pack(anchor="w")
        tk.Label(ident,text=TAG,bg="white",fg=MUTED,font=("Segoe UI",9)).pack(anchor="w",pady=(2,0))
        tk.Frame(self,bg="#008ECF",height=4).place(x=0,y=108,relwidth=1)
        body=tk.Frame(self,bg=BG); body.pack(fill="both",expand=True)
        nav=tk.Frame(body,bg="#EEEFFC",width=225); nav.pack(side="left",fill="y"); nav.pack_propagate(False)
        self.main=tk.Frame(body,bg=BG); self.main.pack(side="left",fill="both",expand=True)
        names=["Accueil","Mon CV","Compétences & métiers","Offres","CV ↔ Offre","Formations","Marché du travail","Plan d’action"]
        self.pages={}
        self.nav_buttons={}
        for n in names:
            self.pages[n]=tk.Frame(self.main,bg=BG)
            _btn=tk.Button(nav,text="  "+n,anchor="w",command=lambda x=n:self.show(x),bg="#EEEFFC",fg=TEXT,
                      relief="flat",activebackground="#DDDDF7",font=("Segoe UI",10,"bold"),padx=14,pady=13)
            _btn.pack(fill="x",padx=8,pady=2)
            self.nav_buttons[n]=_btn
        tk.Frame(nav,bg=LINE,height=1).pack(fill="x",padx=15,pady=10)
        tk.Button(nav,text="⚙  Connexion API",anchor="w",command=self.config_api,bg="#EEEFFC",fg=MUTED,relief="flat",
                  font=("Segoe UI",9,"bold"),padx=14,pady=10).pack(fill="x",padx=8)
        self.comparison_offers=[]
        self.home(); self.cvpage(); self.cv_offer_page(); self.skills_page(); self.offers_page(); self.formations_page(); self.market_page(); self.plan_action_page()
        self.show("Accueil")
        self.after(100,self._sync_module_access)
        tk.Label(self,textvariable=self.status,bg="#ECECF4",fg=MUTED,anchor="w",font=("Segoe UI",9)).pack(fill="x",ipady=5)

    def heading(self,p,t,s):
        tk.Label(p,text=t,bg=BG,fg=TEXT,font=("Segoe UI",22,"bold")).pack(anchor="w",padx=30,pady=(24,2))
        tk.Label(p,text=s,bg=BG,fg=MUTED,font=("Segoe UI",10)).pack(anchor="w",padx=31,pady=(0,14))
    def _round_rect(self,canvas,x1,y1,x2,y2,r,**kw):
        pts=[x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1]
        return canvas.create_polygon(pts,smooth=True,splinesteps=24,**kw)

    def rounded_frame(self,parent,bg=CARD,border=LINE,radius=RADIUS_CARD,padx=30,pady=7):
        f=ctk.CTkFrame(parent,fg_color=bg,border_color=border,border_width=1,
                       corner_radius=radius)
        f.pack(fill="x",padx=padx,pady=pady)
        return f

    def rounded_button(self,parent,text,command,bg="#008ECF",fg="white",width=180,height=44,radius=RADIUS_BUTTON):
        hover="#0079B0" if bg=="#008ECF" else "#202965"
        return ctk.CTkButton(parent,text=text,command=command,width=width,height=height,
                             corner_radius=radius,fg_color=bg,hover_color=hover,
                             text_color=fg,font=("Segoe UI",10,"bold"))

    def card(self,p):
        return self.rounded_frame(p,CARD,LINE,RADIUS_CARD,30,7)
    def show(self,n):
        for f in self.pages.values():f.pack_forget()
        self.pages[n].pack(fill="both",expand=True)
        if n=="CV ↔ Offre" and hasattr(self,"cv_offer_status"):
            self._refresh_cv_offer_status()
        if n=="Compétences & métiers" and hasattr(self,"skills_panel"):
            self.refresh_skills()
        try:self._sync_module_access()
        except Exception:pass
        if n=="Offres" and hasattr(self,"offer_job_label"):
            self._refresh_offer_tabs()
            job=self._active_offer(); code=(job.get("code") or ""); label=(job.get("libelle") or "")
            self.offer_job_label.config(text=("Recherche pour : "+label+" • "+code) if code else "Métier : aucun métier ROME sélectionné")
        if n=="Formations" and hasattr(self,"training_job_label"):
            self._refresh_training_tabs()
            job=self._active_training_job(); code=(job.get("code") or ""); label=(job.get("libelle") or "")
            self.training_job_label.config(text=("Recherche pour : "+label+" • "+code) if code else "Métier : aucun métier ROME sélectionné")
        if n=="Marché du travail" and hasattr(self,"market_tabs"):
            self._refresh_market_tabs()
            self._refresh_market_scope()
        if n=="Plan d’action" and hasattr(self,"plan_zone"):
            self.refresh_plan_action()

    def home(self):
        p=self.pages["Accueil"];self.heading(p,"Démarrer un accompagnement","1. CV  →  2. métier ROME  →  3. diagnostic  →  4. exploration métiers")
        c=self.card(p)
        tk.Label(c,text="1  Importer le CV",bg=CARD,fg=TEXT,font=("Segoe UI",13,"bold")).grid(row=0,column=0,sticky="w",padx=22,pady=(18,6))
        self.filelab=tk.Label(c,text="Aucun CV importé",bg=CARD,fg=MUTED);self.filelab.grid(row=1,column=0,sticky="w",padx=22,pady=(0,18))
        self.rounded_button(c,"Choisir un CV",self.import_cv,width=150).grid(row=0,rowspan=2,column=1,padx=22)
        c.grid_columnconfigure(0,weight=1)
        c=self.card(p)
        tk.Label(c,text="2  Métier visé — ROME 4.0",bg=CARD,fg=TEXT,font=("Segoe UI",13,"bold")).pack(anchor="w",padx=22,pady=(18,4))
        tk.Label(c,text="Si vous connaissez le métier visé, sélectionnez-le. Sinon laissez ce champ vide : l’exploration se fera ensuite à partir du CV.",bg=CARD,fg=MUTED,font=("Segoe UI",9)).pack(anchor="w",padx=22,pady=(0,8))
        self.entry=ttk.Entry(c,textvariable=self.target,font=("Segoe UI",11));self.entry.pack(fill="x",padx=22,ipady=6);self.entry.bind("<KeyRelease>",self.key)
        self.listbox=tk.Listbox(c,height=6,font=("Segoe UI",10),bd=0,highlightthickness=1,highlightbackground=LINE)
        self.listbox.bind("<<ListboxSelect>>",self.pick)
        self.selectedlab=tk.Label(c,text="Aucun métier ROME sélectionné",bg=CARD,fg=MUTED,font=("Segoe UI",9));self.selectedlab.pack(anchor="w",padx=22,pady=10)
        r=tk.Frame(c,bg=CARD);r.pack(fill="x",padx=22,pady=(0,18))
        c=self.card(p)
        tk.Label(c,text="3  Diagnostic",bg=CARD,fg=TEXT,font=("Segoe UI",13,"bold")).pack(anchor="w",padx=22,pady=(18,4))
        self.rounded_button(c,"Analyser le CV",self.analyse,bg=NAVY,width=150).pack(anchor="w",padx=22,pady=(8,18))

    def key(self,e=None):
        q=self.target.get().strip()
        if isinstance(self.selected_job,dict):
            selected_label=(self.selected_job.get("libelle") or "").strip()
            if q==selected_label:
                return
        self.selected_job=None
        # The Home field is no longer the previously selected ROME:
        # clear every primary-target mirror so other modules cannot reuse it.
        self.primary_offer_job={}
        self.current_offer_rome={}
        self.skills_explore_code=""
        self.cv_selected_jobs=[]
        self.plan_selected_job_codes=[]
        self.selectedlab.config(text="Aucun métier ROME sélectionné",fg=MUTED)
        self.refresh_skills()
        if self.after_id:self.after_cancel(self.after_id)
        if len(q)<2:
            self.listbox.pack_forget();return
        self.after_id=self.after(1150,lambda:self.search(q))

    def search(self,q):
        q=(q or "").strip()
        if len(q)<2:return

        cfg=load_cfg()
        if not cfg.get("client_id"):
            self.status.set("Configurez la connexion API avant la recherche ROME")
            return

        cache_key=q.casefold()
        if cache_key in self.rome_search_cache:
            self.display(self.rome_search_cache[cache_key])
            return

        self.rome_search_seq+=1
        seq=self.rome_search_seq
        self.status.set("Recherche ROME en cours…")

        def work():
            try:
                # ROME Métiers: max 1 request/s. Wait rather than sending bursts.
                wait=1.15-(time.monotonic()-self.rome_search_last_at)
                if wait>0:time.sleep(wait)

                # If the user typed something else while waiting, cancel this obsolete query.
                if seq!=self.rome_search_seq:return

                t=token(cfg["client_id"],cfg["client_secret"],ROME_SCOPE)
                self.rome_search_last_at=time.monotonic()
                data=get_json(ROME_URL+"?"+urllib.parse.urlencode({"q":q}),t)
                results=data.get("resultats",[]) if isinstance(data,dict) else []
                self.rome_search_cache[cache_key]=results

                def done():
                    # Do not replace newer suggestions with an old response.
                    if seq==self.rome_search_seq and self.target.get().strip().casefold()==cache_key:
                        self.display(results)
                self.after(0,done)

            except Exception as ex:
                msg=str(ex)
                def failed():
                    if seq!=self.rome_search_seq:return
                    if "429" in msg:
                        self.status.set("Recherche ROME momentanément limitée — réessayez dans un instant")
                    else:
                        self.api_error(msg)
                self.after(0,failed)

        threading.Thread(target=work,daemon=True).start()


    def display(self,results):
        self.jobs=results[:12];self.listbox.delete(0,"end")
        for x in self.jobs:
            label=x.get("libelle") or x.get("libelleMetier") or x.get("intitule") or x.get("label") or "Métier"
            code=x.get("code") or x.get("codeRome") or x.get("id") or ""
            self.listbox.insert("end",label+(f"  [{code}]" if code else ""))
        if self.jobs:
            self.listbox.pack(fill="x",padx=22,pady=(3,5),after=self.entry);self.status.set(f"{len(self.jobs)} proposition(s) ROME")
        else:self.listbox.pack_forget();self.status.set("Aucun résultat ROME")
    def api_error(self,msg):
        self.listbox.pack_forget();self.status.set("Erreur ROME");messagebox.showerror("ROME 4.0",msg)
    def pick(self,e=None):
        s=self.listbox.curselection()
        if not s:return
        x=self.jobs[s[0]];label=x.get("libelle") or x.get("libelleMetier") or x.get("intitule") or x.get("label") or "Métier"
        code=x.get("code") or x.get("codeRome") or x.get("id") or ""
        # Normalise et mémorise explicitement le métier ROME sélectionné.
        self.selected_job=dict(x) if isinstance(x,dict) else {}
        self.primary_offer_job=dict(self.selected_job)
        self.current_offer_rome=dict(self.selected_job) if isinstance(self.selected_job,dict) else {}
        self.selected_job["libelle"]=label
        self.selected_job["code"]=code
        self.rome_search_seq+=1
        self.target.set(label)
        self.listbox.pack_forget()
        self.selectedlab.config(text="✓ Métier ROME sélectionné : "+label+(f" — {code}" if code else ""),fg=GOOD)
        self.refresh_skills()

    def import_cv(self):
        p=filedialog.askopenfilename(filetypes=[("CV","*.pdf *.docx *.txt")])
        if not p:return
        try:self.cv_text=read_cv(p);self.cv_path=p;self.filelab.config(text=Path(p).name,fg=GOOD);self.status.set("CV importé")
        except Exception as ex:messagebox.showerror("Import CV",str(ex))

    def geo_get(self,url):
        req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"PerspectivesEmploi/4.4"})
        with urllib.request.urlopen(req,timeout=15) as r:
            return json.loads(r.read().decode())

    def load_regions(self):
        self.status.set("Chargement des régions…")
        def work():
            try:
                data=self.geo_get("https://geo.api.gouv.fr/regions")
                vals=sorted([(x.get("nom",""),x.get("code","")) for x in data])
                self.after(0,lambda:self.set_regions(vals))
            except Exception as ex:
                self.after(0,lambda:self.geo_error("régions",str(ex)))
        threading.Thread(target=work,daemon=True).start()

    def set_regions(self,vals):
        self.regions=dict(vals)
        self.region_cb["values"]=[x[0] for x in vals]
        if self.region_var.get() not in self.regions and vals:self.region_var.set(vals[0][0])
        self.region_changed()
        self.status.set("Territoires chargés")

    def region_changed(self,e=None):
        name=self.region_var.get()
        code=getattr(self,"regions",{}).get(name)
        if not code:return
        self.dept_var.set("");self.city_var.set("");self.city_cb["values"]=[]
        self.status.set("Chargement des départements…")
        def work():
            try:
                data=self.geo_get("https://geo.api.gouv.fr/regions/"+urllib.parse.quote(code)+"/departements")
                vals=sorted([(f"{x.get('nom','')} ({x.get('code','')})",x.get("code","")) for x in data])
                self.after(0,lambda:self.set_departments(vals))
            except Exception as ex:self.after(0,lambda:self.geo_error("départements",str(ex)))
        threading.Thread(target=work,daemon=True).start()

    def set_departments(self,vals):
        self.departments=dict(vals);self.dept_cb["values"]=[x[0] for x in vals]
        preferred="Yvelines (78)"
        if preferred in self.departments and self.region_var.get()=="Île-de-France":
            self.dept_var.set(preferred)
        elif vals:self.dept_var.set(vals[0][0])
        self.dept_changed()

    def dept_changed(self,e=None):
        code=getattr(self,"departments",{}).get(self.dept_var.get())
        if not code:return
        self.city_var.set("");self.status.set("Chargement des villes…")
        def work():
            try:
                url="https://geo.api.gouv.fr/departements/"+urllib.parse.quote(code)+"/communes?fields=nom,code,codesPostaux&format=json"
                data=self.geo_get(url)
                vals=sorted([x.get("nom","") for x in data if x.get("nom")])
                self.after(0,lambda:self.set_cities(vals))
            except Exception as ex:self.after(0,lambda:self.geo_error("villes",str(ex)))
        threading.Thread(target=work,daemon=True).start()

    def set_cities(self,vals):
        self.all_cities=vals;self.city_cb["values"]=vals
        self.status.set(f"{len(vals)} ville(s) disponibles")
        self.update_location()

    def city_typed(self,e=None):
        typed=self.city_var.get().strip().lower()
        vals=getattr(self,"all_cities",[])
        if typed:self.city_cb["values"]=[x for x in vals if typed in x.lower()][:50]
        else:self.city_cb["values"]=vals
        self.update_location()

    def update_location(self):
        parts=[self.region_var.get(),self.dept_var.get(),self.city_var.get().strip()]
        self.location.set(" — ".join(x for x in parts if x))

    def geo_error(self,kind,msg):
        self.status.set("Erreur de chargement des "+kind)
        messagebox.showerror("Territoire","Impossible de charger les "+kind+".\\n\\n"+msg)

    def cvpage(self):
        p=self.pages["Mon CV"]
        self.heading(p,"Mon CV","Comprendre rapidement ce qui fonctionne et ce qu'il faut modifier concrètement.")
        tabs=tk.Frame(p,bg=BG);tabs.pack(fill="x",padx=30,pady=(0,4))
        self.cv_mode=tk.StringVar(value="candidat")
        tk.Radiobutton(tabs,text="👤 Conseils pour le candidat",variable=self.cv_mode,value="candidat",
                       command=self.refresh_cv_view,bg=BG,fg=TEXT,selectcolor="#EEEDFF",
                       activebackground=BG,font=("Segoe UI",10,"bold")).pack(side="left",padx=(0,18))
        tk.Radiobutton(tabs,text="🧑‍💼 Analyse conseiller",variable=self.cv_mode,value="conseiller",
                       command=self.refresh_cv_view,bg=BG,fg=TEXT,selectcolor="#EEEDFF",
                       activebackground=BG,font=("Segoe UI",10,"bold")).pack(side="left")

        canvas=tk.Canvas(p,bg=BG,highlightthickness=0)
        self.cv_canvas=canvas
        sb=ttk.Scrollbar(p,orient="vertical",command=canvas.yview)
        self.diag=tk.Frame(canvas,bg=BG)
        self.diag.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
        self.cv_canvas_window=canvas.create_window((0,0),window=self.diag,anchor="nw")
        canvas.bind("<Configure>",lambda e:canvas.itemconfigure(self.cv_canvas_window,width=e.width))
        canvas.configure(yscrollcommand=sb.set)

        def _cv_wheel(event):
            # Windows/macOS wheel + Linux buttons, only while pointer is over this page.
            if getattr(event,"num",None)==4:
                canvas.yview_scroll(-4,"units")
            elif getattr(event,"num",None)==5:
                canvas.yview_scroll(4,"units")
            else:
                delta=getattr(event,"delta",0)
                if delta:
                    canvas.yview_scroll((int(-1*(delta/120)) if abs(delta)>=120 else (-1 if delta>0 else 1))*4,"units")
            return "break"

        # Ne pas utiliser bind_all/unbind_all ici :
        # CustomTkinter utilise lui-même les événements de molette pour ses
        # CTkScrollableFrame. Les supprimer bloquerait les autres pages.
        def _bind_cv_tree(widget):
            widget.bind("<MouseWheel>",_cv_wheel,add="+")
            widget.bind("<Button-4>",_cv_wheel,add="+")
            widget.bind("<Button-5>",_cv_wheel,add="+")
            for child in widget.winfo_children():
                _bind_cv_tree(child)

        canvas.bind("<MouseWheel>",_cv_wheel,add="+")
        canvas.bind("<Button-4>",_cv_wheel,add="+")
        canvas.bind("<Button-5>",_cv_wheel,add="+")
        _bind_cv_tree(self.diag)
        self.bind_cv_mousewheel=lambda: _bind_cv_tree(self.diag)
        self.diag.bind("<Enter>",lambda e:self.bind_cv_mousewheel(),add="+")
        canvas.pack(side="left",fill="both",expand=True,padx=(18,0))
        sb.pack(side="right",fill="y",padx=(0,18))
        self.last_diag=None
        tk.Label(self.diag,text="Importez un CV, choisissez un métier puis cliquez sur « Analyser le CV ».",
                 bg=BG,fg=MUTED,font=("Segoe UI",11)).pack(anchor="w",padx=14,pady=20)

    def refresh_cv_view(self):
        if not self.last_diag:return
        score,rows=self.last_diag
        self.render_cv(score,rows)

    def analyse(self):
        if not self.cv_text:
            messagebox.showwarning(APP,"Importez d'abord un CV.");return
        score,rows=diagnostic(self.cv_text,self.target.get().strip())
        self.last_diag=(score,rows)
        self.render_cv(score,rows)
        self.show("Mon CV")
        self.status.set("Diagnostic CV terminé")

    def render_cv(self,score,rows):
        for w in self.diag.winfo_children():w.destroy()
        if self.cv_mode.get()=="conseiller":
            self.render_adviser(score,rows);return

        if score>=80:
            verdict="CV solide — quelques optimisations peuvent encore le renforcer"
            vcol=GOOD
        elif score>=60:
            verdict="CV sur la bonne voie — plusieurs améliorations sont recommandées"
            vcol=WARN
        else:
            verdict="CV à retravailler en priorité avant candidature"
            vcol=BAD

        top=self.rounded_frame(self.diag,CARD,LINE,RADIUS_CARD,14,6)
        tk.Label(top,text=f"{score}/100",bg=CARD,fg=NAVY,font=("Segoe UI",28,"bold")).pack(side="left",padx=22,pady=18)
        right=tk.Frame(top,bg=CARD);right.pack(side="left",fill="x",expand=True,pady=14)
        tk.Label(right,text=verdict,bg=CARD,fg=vcol,font=("Segoe UI",13,"bold"),wraplength=690,justify="left").pack(anchor="w")
        tk.Label(right,text=("Métier ciblé : "+self.target.get().strip()) if self.target.get().strip() else "Mode exploration : aucun métier ciblé",bg=CARD,fg=MUTED,font=("Segoe UI",9)).pack(anchor="w",pady=(5,0))

        priorities=sorted([x for x in rows if not x[3].startswith("—")],key=lambda x:(x[2]-x[1]),reverse=True)[:3]
        pr=tk.Frame(self.diag,bg="#FFF9DB",highlightbackground="#FFE000",highlightthickness=1)
        pr.pack(fill="x",padx=14,pady=7)
        tk.Label(pr,text="🎯 Ce que vous devez faire maintenant",bg="#FFF9DB",fg=TEXT,font=("Segoe UI",14,"bold")).pack(anchor="w",padx=20,pady=(15,4))
        tk.Label(pr,text="Commencez par ces modifications : ce sont celles qui ont le plus d'impact sur votre diagnostic.",
                 bg="#FFF9DB",fg=MUTED,font=("Segoe UI",9),wraplength=850,justify="left").pack(anchor="w",padx=20,pady=(0,8))
        for i,x in enumerate(priorities,1):
            name,pts,maxi,state,why,advice,example=x
            gap=maxi-pts
            tk.Label(pr,text=f"{i}. {name}  •  jusqu'à +{gap} pts",
                     bg="#FFF9DB",fg=TEXT,font=("Segoe UI",10,"bold")).pack(anchor="w",padx=20,pady=(5,1))
            tk.Label(pr,text="👉 "+advice,bg="#FFF9DB",fg=TEXT,font=("Segoe UI",9),
                     wraplength=850,justify="left").pack(anchor="w",padx=34,pady=(0,3))
        tk.Label(pr,text="Les points indiquent le potentiel maximum selon les critères Perspectives Emploi, pas une garantie de sélection par un recruteur ou un ATS.",
                 bg="#FFF9DB",fg=MUTED,font=("Segoe UI",8),wraplength=850,justify="left").pack(anchor="w",padx=20,pady=(8,13))

        tk.Label(self.diag,text="Vérification complète de votre CV",bg=BG,fg=TEXT,font=("Segoe UI",16,"bold")).pack(anchor="w",padx=14,pady=(14,5))

        for name,pts,maxi,state,why,advice,example in rows:
            if state.startswith("—"):
                col=MUTED; label="Non évalué"
            else:
                col=GOOD if state.startswith("✓") else WARN if state.startswith("!") else BAD
                label="Bon" if state.startswith("✓") else "À renforcer" if state.startswith("!") else "Prioritaire"
            c=self.rounded_frame(self.diag,CARD,LINE,RADIUS_CARD,14,5)
            h=tk.Frame(c,bg=CARD);h.pack(fill="x",padx=18,pady=(13,4))
            tk.Label(h,text=name,bg=CARD,fg=TEXT,font=("Segoe UI",11,"bold")).pack(side="left")
            tk.Label(h,text=label,bg=CARD,fg=col,font=("Segoe UI",9,"bold")).pack(side="right")
            tk.Label(c,text=why,bg=CARD,fg=MUTED,font=("Segoe UI",9),wraplength=870,justify="left").pack(anchor="w",padx=18,pady=(0,4))
            if state.startswith("—"):
                action="ℹ "+advice
            elif state.startswith("✓"):
                action="✓ Rien d'urgent à modifier. Conservez cet élément clair et visible."
            else:
                action="👉 À faire : "+advice
            tk.Label(c,text=action,bg=CARD,fg=TEXT,font=("Segoe UI",9,"bold"),
                     wraplength=870,justify="left").pack(anchor="w",padx=18,pady=(4,5))
            example_col=col if not state.startswith("—") else TEXT
            tk.Label(c,text=example,bg="#F8F8FC",fg=example_col,font=("Segoe UI",9,"bold"),
                     wraplength=870,justify="left",anchor="w").pack(fill="x",padx=18,pady=(2,5),ipadx=8,ipady=7)
            if not state.startswith("✓") and not state.startswith("—"):
                tk.Label(c,text="Exemple à adapter uniquement si cela correspond réellement à votre expérience.",
                         bg=CARD,fg=MUTED,font=("Segoe UI",8,"italic")).pack(anchor="w",padx=18,pady=(0,12))
            else:
                tk.Frame(c,bg=CARD,height=8).pack()

    def render_adviser(self,score,rows):
        top=tk.Frame(self.diag,bg="#EEF7FB",highlightbackground=LINE,highlightthickness=1)
        top.pack(fill="x",padx=14,pady=6)
        tk.Label(top,text="🧑‍💼 Analyse conseiller",bg="#EEF7FB",fg=TEXT,font=("Segoe UI",16,"bold")).pack(anchor="w",padx=20,pady=(15,3))
        tk.Label(top,text=(f"Diagnostic CV : {score}/100 • Métier ciblé : {self.target.get().strip()}" if self.target.get().strip() else f"Diagnostic CV : {score}/100 • Mode exploration métiers"),
                 bg="#EEF7FB",fg=MUTED,font=("Segoe UI",9)).pack(anchor="w",padx=20,pady=(0,14))

        weak=[x for x in rows if not x[3].startswith("✓")]
        c=self.rounded_frame(self.diag,CARD,LINE,RADIUS_CARD,14,6)
        tk.Label(c,text="Points à travailler avec le candidat",bg=CARD,fg=TEXT,font=("Segoe UI",12,"bold")).pack(anchor="w",padx=18,pady=(14,6))
        if weak:
            for x in sorted(weak,key=lambda a:a[2]-a[1],reverse=True)[:5]:
                tk.Label(c,text="• "+x[0]+" : "+x[5],bg=CARD,fg=TEXT,font=("Segoe UI",9),
                         wraplength=860,justify="left").pack(anchor="w",padx=22,pady=3)
        else:
            tk.Label(c,text="• Aucun point prioritaire détecté par les critères actuels.",bg=CARD,fg=TEXT,font=("Segoe UI",9)).pack(anchor="w",padx=22,pady=3)
        tk.Frame(c,bg=CARD,height=10).pack()

        q=self.rounded_frame(self.diag,CARD,LINE,RADIUS_CARD,14,6)
        tk.Label(q,text="Questions à poser en entretien",bg=CARD,fg=TEXT,font=("Segoe UI",12,"bold")).pack(anchor="w",padx=18,pady=(14,6))
        questions=[
            "Quelles missions maîtrisez-vous le mieux dans vos expériences récentes ?",
            "Quels résultats ou réalisations pouvez-vous illustrer concrètement ?",
            "Quelles compétences souhaitez-vous mettre davantage en avant pour ce métier ?",
            "Les exemples proposés dans le CV correspondent-ils bien à des activités réellement réalisées ?"
        ]
        for x in questions:
            tk.Label(q,text="• "+x,bg=CARD,fg=TEXT,font=("Segoe UI",9),wraplength=860,justify="left").pack(anchor="w",padx=22,pady=3)
        tk.Frame(q,bg=CARD,height=10).pack()

        a=tk.Frame(self.diag,bg="#F1F8F4",highlightbackground=LINE,highlightthickness=1);a.pack(fill="x",padx=14,pady=(6,24))
        tk.Label(a,text="Action d'accompagnement recommandée",bg="#F1F8F4",fg=TEXT,font=("Segoe UI",12,"bold")).pack(anchor="w",padx=18,pady=(14,5))
        tk.Label(a,text="Faire corriger d'abord les éléments prioritaires, puis vérifier avec le candidat que chaque compétence, mission et résultat ajouté correspond bien à son expérience réelle.",
                 bg="#F1F8F4",fg=TEXT,font=("Segoe UI",9),wraplength=860,justify="left").pack(anchor="w",padx=18,pady=(0,14))

    def _skills_jobs(self):
        jobs=[]
        primary=getattr(self,"primary_offer_job",{}) or self.get_offer_rome()
        if isinstance(primary,dict) and primary.get("code"):
            jobs.append({"libelle":str(primary.get("libelle") or ""),
                         "code":str(primary.get("code") or "").upper(),
                         "primary":True})
        for j in getattr(self,"offer_extra_jobs",[]):
            code=str(j.get("code") or "").upper()
            if code and not any(x["code"]==code for x in jobs):
                jobs.append({"libelle":str(j.get("libelle") or ""),
                             "code":code,"primary":False})
        return jobs

    def _active_skills_job(self):
        jobs=self._skills_jobs()
        code=getattr(self,"skills_explore_code","")
        if code:
            found=next((j for j in jobs if j["code"]==code),None)
            if found:return found
        return jobs[0] if jobs else self.get_offer_rome()

    def _remove_explored_job(self,code):
        if not (getattr(self,"selected_job",None) or {}).get("code"):
            _match=next((j for j in self._selected_exploration_jobs()
                         if str(j.get("code") or "").upper()==str(code or "").upper()),None)
            if _match:
                self._toggle_cv_job(_match)
                return
        saved_y=None
        try:
            canvas=getattr(self.skills_panel,"_parent_canvas",None)
            if canvas is not None:saved_y=canvas.yview()[0]
        except Exception:pass
        code=str(code or "").upper()
        if not code:return
        self.offer_extra_jobs=[j for j in self.offer_extra_jobs
                               if str(j.get("code") or "").upper()!=code]
        if getattr(self,"skills_explore_code","")==code:self.skills_explore_code=""
        if hasattr(self,"active_offer_job") and self.active_offer_job.get()==code:
            primary=self._primary_offer()
            self.active_offer_job.set(primary.get("code","") if primary else "")
        if hasattr(self,"offer_tabs"):self._refresh_offer_tabs()
        btn=getattr(self,"nearby_action_buttons",{}).get(code)
        if btn and btn.winfo_exists():btn.configure(text="Ajouter")
        current=getattr(self,"active_skill_tab","overview")
        self.show_skills_tab(current)
        self.status.set("Métier exploré retiré.") 
        if saved_y is not None:
            def _restore_removed_scroll():
                try:
                    canvas=getattr(self.skills_panel,"_parent_canvas",None)
                    if canvas is not None:canvas.yview_moveto(saved_y)
                except Exception:pass
            self.after_idle(_restore_removed_scroll)


    def _select_skills_job(self,code):
        self.skills_explore_code=code
        self.refresh_skills()

    def _refresh_skills_job_selector(self):
        if not hasattr(self,"skills_job_selector"):return
        for w in self.skills_job_selector.winfo_children():w.destroy()
        jobs=self._skills_jobs()
        if len(jobs)<2:
            try:self.skills_job_selector.pack_forget()
            except Exception:pass
            return
        try:
            self.skills_job_selector.pack(fill="x",padx=20,pady=(14,4),before=self.skills_job_selector.master.winfo_children()[1])
        except Exception:
            try:self.skills_job_selector.pack(fill="x",padx=20,pady=(14,4))
            except Exception:pass
        active=self._active_skills_job()
        # Profession blocks: one single rounded background, no nested button
        # background that can protrude through the rounded corners.
        for col in range(2):
            self.skills_job_selector.grid_columnconfigure(col,weight=1,uniform="skills_jobs")

        for i,j in enumerate(jobs):
            is_active=j["code"]==active.get("code")
            row=i//2; col=i%2
            bg=NAVY if is_active else "#E9EBF8"
            fg="white" if is_active else NAVY

            holder=ctk.CTkFrame(self.skills_job_selector,fg_color=bg,corner_radius=14,
                                border_width=0,height=42)
            holder.grid(row=row,column=col,sticky="ew",padx=4,pady=4)
            holder.grid_propagate(False)
            holder.grid_columnconfigure(0,weight=1)

            prefix_text="Métier initial : " if j.get("primary") else "Métier exploré : "
            lbl=ctk.CTkLabel(holder,text=prefix_text+j.get("libelle","")+" • "+j["code"],
                             text_color=fg,font=("Segoe UI",8,"bold"),anchor="w")
            lbl.grid(row=0,column=0,sticky="nsew",padx=(14,6),pady=5)
            lbl.bind("<Button-1>",lambda e,c=j["code"]:self._select_skills_job(c))
            holder.bind("<Button-1>",lambda e,c=j["code"]:self._select_skills_job(c))

            if not j.get("primary"):
                xlbl=ctk.CTkLabel(holder,text="×",width=28,text_color=fg,
                                  font=("Segoe UI",13,"bold"),cursor="hand2")
                xlbl.grid(row=0,column=1,padx=(0,8),pady=5)
                xlbl.bind("<Button-1>",lambda e,c=j["code"]:self._remove_explored_job(c))


    # ---------------- CV ↔ OFFRE : module autonome ----------------
    def cv_offer_page(self):
        p=self.pages["CV ↔ Offre"]
        self.heading(p,"CV ↔ Offre","Analyser une offre et la comparer au CV chargé, sans modifier les autres modules.")
        self.cv_offer_data={}; self.cv_offer_source=""
        self.cv_offer_ref_var=tk.StringVar(); self.cv_offer_url_var=tk.StringVar()
        self.cv_offer_method=tk.StringVar(value="offers"); self.cv_offer_file_path=""
        self.cv_offer_selected_key=tk.StringVar(value="")

        box=self.rounded_frame(p)
        self.cv_offer_import_box=box
        ctk.CTkLabel(box,text="Choisir une méthode d’import",text_color=NAVY,font=("Segoe UI",13,"bold"),
                     anchor="w").pack(fill="x",padx=16,pady=(13,8))
        methods=ctk.CTkFrame(box,fg_color="transparent");methods.pack(fill="x",padx=12,pady=(0,8))
        for label,val in [("Depuis Offres","offers"),("Référence France Travail","reference"),
                          ("Lien de l’offre","url"),("Coller le texte","text"),
                          ("Importer un document","file")]:
            ctk.CTkRadioButton(methods,text=label,variable=self.cv_offer_method,value=val,
                command=self._cv_offer_method_changed,text_color=TEXT,fg_color=NAVY).pack(side="left",padx=6,pady=4)

        self.cv_offer_input=ctk.CTkFrame(box,fg_color="transparent")
        self.cv_offer_input.pack(fill="x",padx=16,pady=(2,8))
        row=ctk.CTkFrame(box,fg_color="transparent");row.pack(fill="x",padx=16,pady=(0,13))
        self.cv_offer_status=ctk.CTkLabel(row,text="Aucune offre chargée",text_color=MUTED,anchor="w")
        self.cv_offer_status.pack(side="left",fill="x",expand=True)
        ctk.CTkButton(row,text="Analyser et comparer avec mon CV",height=35,corner_radius=10,
                      fg_color=NAVY,command=self._cv_offer_launch_analysis).pack(side="right")
        self.cv_offer_results=ctk.CTkScrollableFrame(p,fg_color="transparent",corner_radius=0)
        self.cv_offer_results.pack(fill="both",expand=True,padx=24,pady=(0,18))
        self.after(100,self._bind_cv_offer_wheel)
        self._cv_offer_method_changed()

    def _bind_cv_offer_wheel(self):
        """Active une molette uniforme sur toute la page CV ↔ Offre."""
        try:
            frame=self.cv_offer_results
            canvas=getattr(frame,"_parent_canvas",None) or getattr(frame,"_canvas",None)
            if canvas is None:return
            def _wheel(event):
                try:
                    if getattr(event,"num",None)==4: step=-1
                    elif getattr(event,"num",None)==5: step=1
                    else:
                        delta=getattr(event,"delta",0)
                        if not delta:return None
                        step=int(-1*(delta/120)) if abs(delta)>=120 else (-1 if delta>0 else 1)
                    canvas.yview_scroll(step*12, "units")
                    return "break"
                except Exception:return None
            def _tree(w):
                try:
                    w.bind("<MouseWheel>",_wheel,add="+")
                    w.bind("<Button-4>",_wheel,add="+")
                    w.bind("<Button-5>",_wheel,add="+")
                except Exception:pass
                try:
                    for child in w.winfo_children():_tree(child)
                except Exception:pass
            _tree(frame)
        except Exception:pass

    def _cv_offer_collapse_import(self):
        """Réduit la zone d'import après analyse tout en gardant l'accès au changement d'offre."""
        box=getattr(self,"cv_offer_import_box",None)
        if not box:return
        try: box.pack_forget()
        except Exception: pass
        try:
            if hasattr(self,"cv_offer_compact_box") and self.cv_offer_compact_box.winfo_exists():
                self.cv_offer_compact_box.destroy()
        except Exception: pass
        compact=ctk.CTkFrame(self.cv_offer_results,fg_color="#FFFFFF",corner_radius=14,
                             border_width=1,border_color=LINE)
        compact.pack(fill="x",padx=6,pady=(4,8))
        self.cv_offer_compact_box=compact
        ctk.CTkLabel(compact,text="Offre analysée : "+(self.cv_offer_source or "offre sélectionnée"),
                     text_color=NAVY,font=("Segoe UI",10,"bold"),anchor="w").pack(side="left",fill="x",expand=True,padx=14,pady=9)
        ctk.CTkButton(compact,text="Changer d’offre / méthode",height=29,corner_radius=9,width=165,
                      fg_color=NAVY,command=self._cv_offer_expand_import).pack(side="right",padx=(6,10),pady=7)
        ctk.CTkButton(compact,text="Importer la comparaison",height=29,corner_radius=9,width=165,
                      fg_color=PURPLE,command=self.export_cv_offer_pdf).pack(side="right",padx=(6,0),pady=7)

    def _cv_offer_expand_import(self):
        try:
            if hasattr(self,"cv_offer_compact_box") and self.cv_offer_compact_box.winfo_exists():
                self.cv_offer_compact_box.destroy()
        except Exception: pass
        try:
            self.cv_offer_import_box.pack(fill="x",padx=24,pady=(0,12),before=self.cv_offer_results)
        except Exception: pass

    def _refresh_cv_offer_status(self):
        cvok=bool(str(getattr(self,"cv_text","") or getattr(self,"extracted_text","") or "").strip())
        txt=("CV chargé" if cvok else "Chargez d’abord un CV dans « Mon CV »")
        if self.cv_offer_source:txt+=" • Offre : "+self.cv_offer_source
        self.cv_offer_status.configure(text=txt)

    def _cv_offer_method_changed(self):
        for w in self.cv_offer_input.winfo_children():w.destroy()
        m=self.cv_offer_method.get()
        if m=="offers":
            offers=list(getattr(self,"comparison_offers",[]) or [])
            if not offers:
                ctk.CTkLabel(self.cv_offer_input,text="Aucune offre sélectionnée dans l’onglet Offres.",
                             text_color=MUTED,anchor="w").pack(fill="x",pady=6)
            else:
                keys=[self._comparison_offer_key(x) for x in offers]
                if self.cv_offer_selected_key.get() not in keys:
                    self.cv_offer_selected_key.set(keys[0])
                ctk.CTkLabel(self.cv_offer_input,text="Choisissez l’offre à comparer avec le CV",
                             text_color=NAVY,font=("Segoe UI",10,"bold"),anchor="w").pack(fill="x",pady=(3,5))
                for o in offers:
                    key=self._comparison_offer_key(o)
                    title=str(o.get("intitule") or "Offre France Travail")
                    company=str((o.get("entreprise") or {}).get("nom") or "Entreprise non précisée")
                    location=str((o.get("lieuTravail") or {}).get("libelle") or "Lieu non précisé")
                    card=ctk.CTkFrame(self.cv_offer_input,fg_color="#FFFFFF",corner_radius=11,
                                      border_width=1,border_color=LINE)
                    card.pack(fill="x",pady=3)
                    rb=ctk.CTkRadioButton(card,text="",width=24,variable=self.cv_offer_selected_key,value=key,
                                          fg_color=NAVY)
                    rb.pack(side="left",padx=(10,3),pady=10)
                    info=ctk.CTkFrame(card,fg_color="transparent");info.pack(side="left",fill="x",expand=True,pady=7)
                    ctk.CTkLabel(info,text=title,text_color=NAVY,font=("Segoe UI",10,"bold"),
                                 anchor="w").pack(side="left")
                    ctk.CTkLabel(info,text="  •  "+company+" · "+location,text_color=TEXT,font=("Segoe UI",9),
                                 anchor="w").pack(side="left",padx=(2,0))
        elif m=="reference":
            ctk.CTkLabel(self.cv_offer_input,text="Numéro / référence France Travail",text_color=TEXT,anchor="w").pack(fill="x")
            ctk.CTkEntry(self.cv_offer_input,textvariable=self.cv_offer_ref_var,height=34,corner_radius=9,fg_color="#FFFFFF",text_color=TEXT,border_color=LINE,
                         placeholder_text="Saisir la référence de l’offre").pack(fill="x",pady=4)
        elif m=="url":
            ctk.CTkLabel(self.cv_offer_input,text="Lien de l’offre",text_color=TEXT,anchor="w").pack(fill="x")
            ctk.CTkEntry(self.cv_offer_input,textvariable=self.cv_offer_url_var,height=34,corner_radius=9,fg_color="#FFFFFF",text_color=TEXT,border_color=LINE,
                         placeholder_text="https://…").pack(fill="x",pady=4)
        elif m=="text":
            ctk.CTkLabel(self.cv_offer_input,text="Collez le texte complet de l’annonce",text_color=TEXT,anchor="w").pack(fill="x")
            self.cv_offer_text=ctk.CTkTextbox(self.cv_offer_input,height=125,corner_radius=10,border_width=1,border_color=LINE,fg_color="#FFFFFF",text_color=TEXT)
            self.cv_offer_text.pack(fill="x",pady=4)
        else:
            rr=ctk.CTkFrame(self.cv_offer_input,fg_color="transparent");rr.pack(fill="x",pady=5)
            self.cv_offer_file_label=ctk.CTkLabel(rr,text=(Path(self.cv_offer_file_path).name if self.cv_offer_file_path else "Aucun document sélectionné"),
                                                  text_color=TEXT,anchor="w")
            self.cv_offer_file_label.pack(side="left",fill="x",expand=True)
            ctk.CTkButton(rr,text="Choisir un document",width=145,height=32,corner_radius=9,fg_color=NAVY,
                          command=self._cv_offer_choose_file).pack(side="right")

    def _cv_offer_choose_file(self):
        path=filedialog.askopenfilename(title="Importer une offre",
             filetypes=[("Documents","*.pdf *.docx *.txt"),("PDF","*.pdf"),("Word","*.docx"),("Texte","*.txt")])
        if path:self.cv_offer_file_path=path;self._cv_offer_method_changed()

    def _cv_offer_launch_analysis(self):
        m=self.cv_offer_method.get()
        if m=="offers":
            offers=list(getattr(self,"comparison_offers",[]) or [])
            key=self.cv_offer_selected_key.get()
            o=next((x for x in offers if self._comparison_offer_key(x)==key),None)
            if not isinstance(o,dict) or not o:
                messagebox.showinfo("CV ↔ Offre","Sélectionnez d’abord une offre parmi celles ajoutées depuis l’onglet Offres.");return
            self._cv_offer_loaded("Offre sélectionnée",o);return
        if m=="reference":self._cv_offer_fetch_reference();return
        if m=="text":
            text=self.cv_offer_text.get("1.0","end").strip()
            if not text:messagebox.showinfo("CV ↔ Offre","Collez d’abord le texte de l’offre.");return
            self.cv_offer_data={};self.cv_offer_source="Texte collé";self._refresh_cv_offer_status()
            self._cv_offer_render(self._cv_offer_parse(text,{}));return
        if m=="file":
            if not self.cv_offer_file_path:messagebox.showinfo("CV ↔ Offre","Choisissez d’abord un document.");return
            try:text=read_cv(self.cv_offer_file_path)
            except Exception as e:messagebox.showerror("Import de l’offre",str(e));return
            self.cv_offer_data={};self.cv_offer_source=Path(self.cv_offer_file_path).name;self._refresh_cv_offer_status()
            self._cv_offer_render(self._cv_offer_parse(text,{}));return
        url=self.cv_offer_url_var.get().strip()
        if not url:messagebox.showinfo("CV ↔ Offre","Saisissez d’abord le lien de l’offre.");return
        try:
            r=requests.get(url,timeout=15,headers={"User-Agent":"Mozilla/5.0"});r.raise_for_status()
            raw=re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>"," ",r.text,flags=re.I)
            text=re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",raw)).strip()
            if len(text)<100:raise RuntimeError("Contenu insuffisant.")
            self.cv_offer_data={};self.cv_offer_source="Lien de l’offre";self._refresh_cv_offer_status()
            self._cv_offer_render(self._cv_offer_parse(text,{}))
        except Exception as e:messagebox.showerror("Lien de l’offre","Impossible de récupérer cette annonce. Utilisez « Coller le texte ».\n\n"+str(e))

    def _cv_offer_fetch_reference(self):
        ref=self.cv_offer_ref_var.get().strip()
        if not ref:return
        self.cv_offer_status.configure(text="Recherche de l’offre "+ref+"…")
        def work():
            try:
                cfg=load_cfg();cid=(cfg.get("client_id") or "").strip();secret=(cfg.get("client_secret") or "").strip()
                if not cid or not secret:raise RuntimeError("Configurez d’abord la connexion API France Travail.")
                tok=token(cid,secret,"o2dsoffre api_offresdemploiv2")
                data=get_json("https://api.francetravail.io/partenaire/offresdemploi/v2/offres/"+urllib.parse.quote(ref),tok)
                self.after(0,lambda:self._cv_offer_loaded("France Travail • "+ref,data))
            except Exception as e:
                msg=str(e);self.after(0,lambda:messagebox.showerror("Recherche de l’offre",msg));self.after(0,self._refresh_cv_offer_status)
        threading.Thread(target=work,daemon=True).start()

    def _cv_offer_loaded(self,source,offer):
        self.cv_offer_data=dict(offer or {});self.cv_offer_source=source
        text=self._cv_offer_offer_text(self.cv_offer_data);self._refresh_cv_offer_status()
        self._cv_offer_render(self._cv_offer_parse(text,self.cv_offer_data))

    def _cv_offer_offer_text(self,o):
        def g(*keys):
            x=o
            for k in keys:
                if not isinstance(x,dict):return ""
                x=x.get(k,"")
            return str(x or "")
        vals=[g("intitule"),g("description"),g("entreprise","nom"),g("lieuTravail","libelle"),
              g("typeContratLibelle"),g("dureeTravailLibelle"),g("salaire","libelle"),g("experienceLibelle")]
        for key in ("competences","qualitesProfessionnelles"):
            for x in o.get(key,[]) or []:
                if isinstance(x,dict):
                    lab=x.get("libelle") or x.get("libelleCompetence") or ""
                    if lab:vals.append(str(lab))
        return "\n".join(x for x in vals if x)

    def _cv_offer_parse(self,text,o=None):
        o=o or {}
        def og(*keys):
            x=o
            for k in keys:
                if not isinstance(x,dict):return ""
                x=x.get(k,"")
            return str(x or "").strip()
        def grab(patterns):
            for pat in patterns:
                m=re.search(pat,text,re.I|re.M)
                if m:return (m.group(1) if m.lastindex else m.group(0)).strip(" :-\t")
            return ""
        info={
          "Poste":og("intitule") or grab([r"(?:poste|intitul[ée])\s*[:\-]\s*([^\n]+)"]),
          "Entreprise":og("entreprise","nom") or grab([r"(?:entreprise|employeur)\s*[:\-]\s*([^\n]+)"]),
          "Type de contrat":og("typeContratLibelle") or grab([r"\b(CDI|CDD|intérim|interim|alternance|apprentissage|stage)\b[^\n]*"]),
          "Salaire":og("salaire","libelle") or grab([r"(?:salaire|rémunération|remuneration)\s*[:\-]\s*([^\n]+)"]),
          "Horaires / temps de travail":og("dureeTravailLibelle") or grab([r"(?:horaires?|temps de travail|durée de travail)\s*[:\-]\s*([^\n]+)"]),
          "Lieu":og("lieuTravail","libelle") or grab([r"(?:lieu|localisation)\s*[:\-]\s*([^\n]+)"]),
          "Expérience demandée":og("experienceLibelle") or grab([r"(?:expérience|experience)\s*[:\-]\s*([^\n]+)"])
        }
        req=[]
        for key in ("competences","qualitesProfessionnelles"):
            for x in o.get(key,[]) or []:
                if isinstance(x,dict):
                    lab=str(x.get("libelle") or x.get("libelleCompetence") or "").strip()
                    if lab and lab not in req:req.append(lab)
        for line in text.splitlines():
            q=line.strip(" •-\t")
            if 5<len(q)<160 and any(k in q.lower() for k in
              ("maîtrise","maitrise","connaissance","expérience","experience","permis","compétence","competence",
               "autonomie","rigueur","organisation","communication","excel","anglais","diplôme","diplome")):
                if q not in req:req.append(q)
        return {"info":info,"requirements":req[:20],"text":text}

    def _cv_offer_analyse_text(self):
        text=self.cv_offer_text.get("1.0","end").strip()
        if not text:
            messagebox.showinfo("CV ↔ Offre","Collez ou importez d’abord une offre.");return
        self.cv_offer_source=self.cv_offer_source or "Texte collé"
        self._refresh_cv_offer_status()
        self._cv_offer_render(self._cv_offer_parse(text,self.cv_offer_data))

    def _cv_offer_render(self,a):
        self.cv_offer_last_analysis=a
        for w in self.cv_offer_results.winfo_children():w.destroy()
        self._cv_offer_collapse_import()
        self.after(100,self._bind_cv_offer_wheel)
        cv=str(getattr(self,"cv_text","") or getattr(self,"extracted_text","") or "")
        if not cv.strip():
            ctk.CTkLabel(self.cv_offer_results,text="Chargez d’abord un CV dans « Mon CV ».",
                         text_color=BAD,font=("Segoe UI",11,"bold")).pack(anchor="w",padx=12,pady=12);return
        cvlow=cv.lower()
        state=self.rounded_frame(self.cv_offer_results)
        ctk.CTkLabel(state,text="État des lieux de l’offre",text_color=NAVY,font=("Segoe UI",14,"bold"),anchor="w").pack(fill="x",padx=16,pady=(12,6))
        for lab,val in a["info"].items():
            row=ctk.CTkFrame(state,fg_color="transparent");row.pack(fill="x",padx=16,pady=2)
            ctk.CTkLabel(row,text=lab,width=185,anchor="w",text_color=MUTED,font=("Segoe UI",9,"bold")).pack(side="left")
            ctk.CTkLabel(row,text=val or "Non précisé dans l’offre",anchor="w",justify="left",
                         text_color=TEXT,font=("Segoe UI",9)).pack(side="left",fill="x",expand=True)

        matched=[];verify=[]
        stop={"avec","pour","dans","vous","votre","cette","poste","avoir","être","etre","expérience","experience","compétence","competence"}
        for r in a["requirements"]:
            words=[w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ0-9+#]{4,}",r) if w.lower() not in stop]
            score=sum(1 for w in set(words) if w in cvlow)
            (matched if words and score>=max(1,min(2,len(set(words))//2)) else verify).append(r)

        comp=self.rounded_frame(self.cv_offer_results)
        ctk.CTkLabel(comp,text="Correspondance CV ↔ Offre",text_color=NAVY,font=("Segoe UI",14,"bold"),anchor="w").pack(fill="x",padx=16,pady=(12,5))
        if matched:
            ctk.CTkLabel(comp,text="✓ Identifié dans le CV",text_color=GOOD,font=("Segoe UI",10,"bold"),anchor="w").pack(fill="x",padx=16,pady=(4,2))
            for x in matched[:10]:ctk.CTkLabel(comp,text="• "+x,text_color=TEXT,anchor="w",justify="left",wraplength=800).pack(fill="x",padx=24,pady=1)
        if verify:
            ctk.CTkLabel(comp,text="? À vérifier avec le candidat",text_color=WARN,font=("Segoe UI",10,"bold"),anchor="w").pack(fill="x",padx=16,pady=(8,2))
            for x in verify[:10]:ctk.CTkLabel(comp,text="• "+x,text_color=TEXT,anchor="w",justify="left",wraplength=800).pack(fill="x",padx=24,pady=1)

        # Indicateur descriptif de compatibilité basé uniquement sur les exigences détectées.
        total=len(matched)+len(verify)
        pct=round((len(matched)/total)*100) if total else 0
        gauge=self.rounded_frame(self.cv_offer_results)
        ctk.CTkLabel(gauge,text="Compatibilité CV ↔ Offre",text_color=NAVY,font=("Segoe UI",14,"bold"),anchor="w").pack(fill="x",padx=16,pady=(12,3))
        ctk.CTkLabel(gauge,text=(str(pct)+" % des exigences détectées sont retrouvées dans le CV" if total else "Compatibilité non calculable : aucune exigence exploitable détectée."),
                     text_color=TEXT,font=("Segoe UI",10),anchor="w").pack(fill="x",padx=16,pady=(0,7))
        bar=ctk.CTkProgressBar(gauge,height=13,corner_radius=7,progress_color=("#16803A" if pct>=70 else "#D97706" if pct>=40 else "#E1000F"))
        bar.pack(fill="x",padx=16,pady=(0,5));bar.set(pct/100 if total else 0)
        ctk.CTkLabel(gauge,text="Indicateur d’aide à la lecture : il mesure les éléments détectés dans les textes, pas l’aptitude réelle du candidat.",
                     text_color=MUTED,font=("Segoe UI",8),anchor="w").pack(fill="x",padx=16,pady=(0,12))

        sug=self.rounded_frame(self.cv_offer_results)
        ctk.CTkLabel(sug,text="Suggestions concrètes pour mieux adapter le CV",text_color=NAVY,font=("Segoe UI",14,"bold"),anchor="w").pack(fill="x",padx=16,pady=(12,4))
        suggestions=[]
        poste=a["info"].get("Poste","")
        if poste:
            suggestions.append(("Titre du CV","Si le projet correspond bien à ce poste, utiliser un titre directement identifiable.","Exemple : « "+poste+" »"))
        if matched:
            for x in matched[:3]:
                suggestions.append(("Compétence déjà présente","Mieux faire ressortir cet élément déjà repéré dans le CV : "+x,
                                    "Suggestion : le reprendre dans la rubrique Compétences ou dans l’expérience où il a réellement été exercé."))
        if verify:
            for x in verify[:3]:
                suggestions.append(("À vérifier avant modification","L’offre demande : "+x,
                                    "Suggestion : demander au candidat s’il possède réellement cet élément. Si oui, préciser dans quelle expérience ou formation il l’a acquis avant de l’ajouter."))
        if not suggestions:
            suggestions.append(("Analyse à compléter","Les textes disponibles ne permettent pas encore de proposer une modification précise.",
                                "Suggestion : utiliser une annonce plus détaillée ou vérifier les missions et compétences avec le candidat."))
        for title,why,proposal in suggestions:
            c=ctk.CTkFrame(sug,fg_color="#F7F8FC",corner_radius=12)
            c.pack(fill="x",padx=16,pady=5)
            ctk.CTkLabel(c,text=title,text_color=NAVY,font=("Segoe UI",10,"bold"),anchor="w").pack(fill="x",padx=12,pady=(8,2))
            ctk.CTkLabel(c,text=why,text_color=TEXT,font=("Segoe UI",9),anchor="w",justify="left",wraplength=790).pack(fill="x",padx=12,pady=1)
            ctk.CTkLabel(c,text="✏ "+proposal,text_color=PURPLE,font=("Segoe UI",9,"bold"),anchor="w",justify="left",wraplength=790).pack(fill="x",padx=12,pady=(2,8))

        tips=self.rounded_frame(self.cv_offer_results)
        ctk.CTkLabel(tips,text="Adapter le CV à cette offre",text_color=NAVY,font=("Segoe UI",14,"bold"),anchor="w").pack(fill="x",padx=16,pady=(12,5))
        poste=a["info"].get("Poste","")
        advice=[]
        if poste:advice.append("Adapter le titre du CV au poste « "+poste+" » uniquement si cela correspond réellement au projet du candidat.")
        if matched:advice.append("Faire ressortir plus clairement les compétences déjà présentes dans le CV et également demandées par l’offre.")
        if verify:advice.append("Vérifier les exigences non identifiées dans le CV avant de les ajouter ou de les reformuler.")
        advice.append("Reprendre les mots professionnels de l’offre uniquement lorsqu’ils décrivent réellement une expérience ou une compétence acquise.")
        for x in advice:ctk.CTkLabel(tips,text="• "+x,text_color=TEXT,anchor="w",justify="left",wraplength=800).pack(fill="x",padx=20,pady=2)
        ctk.CTkFrame(tips,fg_color="transparent",height=8).pack()


    def export_cv_offer_pdf(self):
        """Exporte un bilan CV ↔ Offre avec la même identité visuelle que les bilans de l'application."""
        a=getattr(self,"cv_offer_last_analysis",None)
        if not isinstance(a,dict):
            messagebox.showinfo("Export PDF","Lancez d’abord une analyse CV ↔ Offre.")
            return
        path=filedialog.asksaveasfilename(title="Enregistrer la comparaison",defaultextension=".pdf",
                                         filetypes=[("Document PDF","*.pdf")],
                                         initialfile="Comparaison_CV_Offre.pdf")
        if not path:return
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_LEFT
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether,Image as RLImage
            from reportlab.lib.utils import ImageReader
            from xml.sax.saxutils import escape

            navy=colors.HexColor("#283276"); purple=colors.HexColor("#6D3FC0")
            light=colors.HexColor("#F5F6FA"); green=colors.HexColor("#16803A")
            orange=colors.HexColor("#D97706"); grey=colors.HexColor("#62677A")
            doc=SimpleDocTemplate(path,pagesize=A4,rightMargin=15*mm,leftMargin=15*mm,
                                  topMargin=15*mm,bottomMargin=15*mm)
            styles=getSampleStyleSheet()
            title=ParagraphStyle("cvot",parent=styles["Title"],fontName="Helvetica-Bold",
                                 fontSize=18,leading=21,textColor=navy,spaceAfter=5)
            sub=ParagraphStyle("cvos",parent=styles["BodyText"],fontName="Helvetica",
                               fontSize=8.5,leading=11,textColor=grey,spaceAfter=8)
            h=ParagraphStyle("cvoh",parent=styles["Heading2"],fontName="Helvetica-Bold",
                             fontSize=11,leading=14,textColor=navy,spaceAfter=6)
            body=ParagraphStyle("cvob",parent=styles["BodyText"],fontName="Helvetica",
                                fontSize=8.5,leading=11,textColor=colors.HexColor("#161A2B"))
            small=ParagraphStyle("cvosm",parent=body,fontSize=7.5,leading=10,textColor=grey)

            story=[]
            lp=Path(__file__).with_name("bloc_marque_rf_france_travail.jpg")
            if lp.exists():
                iw,ih=ImageReader(str(lp)).getSize(); scale=min(145/float(iw),40/float(ih))
                logo=RLImage(str(lp),width=iw*scale,height=ih*scale)
                story.append(Table([[Paragraph("CV ↔ Offre",title),logo]],colWidths=[125*mm,45*mm],
                                   style=[("VALIGN",(0,0),(-1,-1),"TOP"),("ALIGN",(1,0),(1,0),"RIGHT")]))
            else:story.append(Paragraph("CV ↔ Offre",title))
            story.append(Paragraph("Bilan de comparaison entre le CV chargé et l’offre analysée.",sub))

            info=a.get("info",{}) or {}
            rows=[]
            for lab in ("Poste","Entreprise","Type de contrat","Salaire","Horaires / temps de travail","Lieu","Expérience demandée"):
                rows.append([Paragraph("<b>"+escape(lab)+"</b>",small),
                             Paragraph(escape(str(info.get(lab) or "Non précisé dans l’offre")),body)])
            t=Table(rows,colWidths=[50*mm,120*mm],hAlign="LEFT")
            t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.white),("BOX",(0,0),(-1,-1),0.5,colors.HexColor("#DDE0EA")),
                                   ("INNERGRID",(0,0),(-1,-1),0.25,colors.HexColor("#E8EAF1")),
                                   ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),7),
                                   ("RIGHTPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
            story += [Paragraph("État des lieux de l’offre",h),t,Spacer(1,9)]

            cv=str(getattr(self,"cv_text","") or getattr(self,"extracted_text","") or "")
            cvlow=cv.lower()
            reqs=a.get("requirements",[]) or []
            stop={"avec","pour","dans","vous","votre","cette","poste","avoir","être","etre","expérience","experience","compétence","competence"}
            matched=[];verify=[]
            for r in reqs:
                words=[w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ0-9+#]{4,}",str(r)) if w.lower() not in stop]
                score=sum(1 for w in set(words) if w in cvlow)
                (matched if words and score>=max(1,min(2,len(set(words))//2)) else verify).append(str(r))
            total=len(matched)+len(verify); pct=round(100*len(matched)/total) if total else 0

            story.append(Paragraph("Compatibilité CV ↔ Offre",h))
            story.append(Paragraph((f"<b>{pct} %</b> des exigences détectées sont retrouvées dans le CV." if total else
                                    "Compatibilité non calculable : aucune exigence exploitable détectée."),body))
            gauge=Table([["", ""]],colWidths=[170*mm*(pct/100 if total else 0),170*mm*(1-(pct/100 if total else 0))],rowHeights=[5])
            gauge.setStyle(TableStyle([("BACKGROUND",(0,0),(0,0),green if pct>=70 else orange if pct>=40 else colors.HexColor("#E1000F")),
                                       ("BACKGROUND",(1,0),(1,0),colors.HexColor("#E8EAF1")),("BOX",(0,0),(-1,-1),0,colors.white)]))
            story += [gauge,Paragraph("Indicateur d’aide à la lecture basé sur les éléments détectés dans les textes.",small),Spacer(1,9)]

            if matched:
                story.append(Paragraph("Éléments identifiés dans le CV",h))
                story.append(KeepTogether([Paragraph("• "+escape(x),body) for x in matched[:12]]))
                story.append(Spacer(1,7))
            if verify:
                story.append(Paragraph("Éléments à vérifier avec le candidat",h))
                story.append(KeepTogether([Paragraph("• "+escape(x),body) for x in verify[:12]]))
                story.append(Spacer(1,7))

            suggestions=[]
            poste=str(info.get("Poste") or "")
            if poste:suggestions.append(("Titre du CV","Si le projet correspond bien au poste, utiliser un titre directement identifiable : « "+poste+" »."))
            for x in matched[:3]:
                suggestions.append(("À mieux valoriser","Faire ressortir dans la rubrique Compétences ou dans l’expérience concernée : "+x))
            for x in verify[:3]:
                suggestions.append(("À vérifier avant ajout","L’offre demande : "+x+". Vérifier avec le candidat s’il possède réellement cet élément et où il l’a acquis."))
            if suggestions:
                story.append(Paragraph("Suggestions concrètes pour adapter le CV",h))
                for lab,txt in suggestions:
                    card=Table([[Paragraph("<b>"+escape(lab)+"</b><br/>"+escape(txt),body)]],colWidths=[170*mm])
                    card.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),light),("BOX",(0,0),(-1,-1),0.5,colors.HexColor("#DDE0EA")),
                                              ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
                                              ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]))
                    story += [KeepTogether(card),Spacer(1,4)]

            story += [Spacer(1,10),Paragraph("Services utiles pour aller plus loin",h)]
            services=[
              ("MétierScope","Explorer les métiers, compétences et environnements professionnels.","https://candidat.francetravail.fr/metierscope/"),
              ("France Travail - Formations","Rechercher des formations correspondant au projet.","https://candidat.francetravail.fr/formations/recherche"),
              ("France Travail - Offres","Poursuivre la recherche d’offres d’emploi.","https://candidat.francetravail.fr/offres/recherche"),
              ("La Bonne Boîte","Identifier des entreprises susceptibles de recruter.","https://labonneboite.francetravail.fr/"),
              ("Mes événements emploi","Trouver des événements et rencontres emploi.","https://mesevenementsemploi.francetravail.fr/mes"),
              ("CVDesignR","Créer et mettre en forme un CV.","https://cvdesignr.com/fr")]
            for name,desc,url in services:
                story.append(Paragraph(f'<b>{escape(name)}</b> - {escape(desc)} <link href="{url}" color="#283276">Accéder au service</link>',body))

            def footer(canvas,doc):
                canvas.saveState();canvas.setFont("Helvetica",7);canvas.setFillColor(grey)
                canvas.drawString(15*mm,8*mm,"Perspectives Emploi - Comparaison CV ↔ Offre")
                canvas.drawRightString(195*mm,8*mm,"Page "+str(doc.page));canvas.restoreState()
            doc.build(story,onFirstPage=footer,onLaterPages=footer)
            messagebox.showinfo("Export PDF","La comparaison a été exportée.")
        except Exception as e:
            messagebox.showerror("Export PDF","Impossible de générer le PDF : "+str(e))

    def _bind_slow_wheel(self, root_widget, canvas, key):
        """Molette locale ralentie : 1 unité tous les 2 événements, sans bind_all."""
        if not hasattr(self, "_slow_wheel_ticks"):
            self._slow_wheel_ticks={}
        def _wheel(event):
            try:
                delta=int(getattr(event,"delta",0) or 0)
                if not delta:
                    return None
                self._slow_wheel_ticks[key]=self._slow_wheel_ticks.get(key,0)+1
                if self._slow_wheel_ticks[key] % 2:
                    return "break"
                canvas.yview_scroll(-1 if delta>0 else 1, "units")
                return "break"
            except Exception:
                return None
        def _bind_tree(w):
            try:w.bind("<MouseWheel>",_wheel,add="+")
            except Exception:pass
            try:
                for child in w.winfo_children():_bind_tree(child)
            except Exception:pass
        _bind_tree(root_widget)
        try:root_widget.bind("<Enter>",lambda e:_bind_tree(root_widget),add="+")
        except Exception:pass

    def skills_page(self):
        p=self.pages["Compétences & métiers"]
        self.heading(p,"Compétences & métiers","Comparer le CV au métier ciblé ou explorer des pistes à partir des compétences repérées.")

        top=self.card(p)
        tk.Label(top,text="Analyse compétences & métiers",bg=CARD,fg=TEXT,
                 font=("Segoe UI",13,"bold")).pack(anchor="w",padx=22,pady=(16,3))
        self.skills_mode_label=tk.Label(top,text="",bg=CARD,fg=MUTED,font=("Segoe UI",9),
                                        wraplength=850,justify="left")
        self.skills_mode_label.pack(anchor="w",padx=22,pady=(0,14))

        # Navigation : un seul panneau visible à la fois.
        nav=ctk.CTkFrame(p,fg_color="transparent")
        nav.pack(fill="x",padx=30,pady=(4,8))
        self.skills_tabs={}
        tabs=[
            ("overview","Vue d’ensemble"),
            ("knowhow","Savoir-faire"),
            ("knowledge","Savoirs"),
            ("soft","Savoir-être"),
            ("transfer","Compétences transférables"),
            ("jobs","Métiers proches"),
        ]
        for key,label in tabs:
            b=ctk.CTkButton(nav,text=label,corner_radius=12,height=38,
                            fg_color="#E8EAF7",hover_color="#DDE1F3",text_color=NAVY,
                            font=("Segoe UI",9,"bold"),
                            command=lambda k=key:self.show_skills_tab(k))
            b.pack(side="left",padx=(0,7))
            self.skills_tabs[key]=b

        # Zone unique : le contenu est remplacé à chaque clic.
        self.skills_panel=ctk.CTkScrollableFrame(p,fg_color=CARD,border_color=LINE,border_width=1,
                                                 corner_radius=22,scrollbar_button_color="#D9DCEF",
                                                 scrollbar_button_hover_color="#C8CCE6")
        self.skills_panel.pack(fill="both",expand=True,padx=30,pady=(0,18))
        self.active_skills_tab="overview"
        self.refresh_skills()
        self.show_skills_tab("overview")

    def _skills_evidence(self):
        text=(self.cv_text or "")
        low=text.lower()
        families=[
            ("Relation, conseil & accompagnement",["accompagnement","accompagner","conseil","conseiller","accueil","entretien","orientation","suivi"]),
            ("Organisation & gestion",["organisation","planification","administratif","dossier","reporting","gestion","coordination"]),
            ("Communication & animation",["communication","présentation","animation","atelier","rédaction","rédiger"]),
            ("Outils numériques",["excel","word","powerpoint","office","logiciel","crm","informatique","numérique"]),
            ("Commerce & relation client",["vente","commercial","prospection","client","fidélisation","négociation"]),
            ("Logistique & production",["logistique","stock","préparation de commandes","caces","production","manutention"]),
            ("Management & encadrement",["management","manager","équipe","encadrement","pilotage"]),
        ]
        found=[]
        for label,keys in families:
            hits=[k for k in keys if k in low]
            if hits: found.append((label,hits[:5]))
        return found

    def get_selected_rome(self):
        if isinstance(self.selected_job,dict):
            label=(self.selected_job.get("libelle") or self.selected_job.get("libelleMetier") or
                   self.selected_job.get("intitule") or self.selected_job.get("label") or "").strip()
            code=(self.selected_job.get("code") or self.selected_job.get("codeRome") or
                  self.selected_job.get("codeROME") or self.selected_job.get("id") or "")
            if label:
                return label,str(code)
        return self.target.get().strip(),""

    def _norm(self,text):
        text=unicodedata.normalize("NFKD",str(text or ""))
        text="".join(c for c in text if not unicodedata.combining(c)).lower()
        return re.sub(r"[^a-z0-9]+"," ",text).strip()

    def _cv_match(self,label):
        """Heuristique locale transparente : ne valide jamais une compétence absente."""
        cv=self._norm(self.cv_text)
        lab=self._norm(label)
        words=[w for w in lab.split() if len(w)>=4 and w not in
               {"avec","dans","pour","afin","selon","entre","mettre","faire","etre","avoir","tout","toute"}]
        hits=[w for w in words if re.search(r"\b"+re.escape(w)+r"\w*\b",cv)]
        if words and len(hits)>=max(2,(len(words)+1)//2):
            return "✓ Identifiée dans le CV","Mots/éléments concordants : "+", ".join(hits[:6]),GOOD
        if hits:
            return "△ À préciser dans le CV","Indice partiel à préciser dans le CV : "+", ".join(hits[:6]),WARN
        return "? À vérifier avec le candidat","Non identifiée explicitement dans le CV. Cela ne signifie pas que la compétence n’est pas maîtrisée.",MUTED

    def load_rome_fiche(self,code):
        code=str(code or "").strip().upper()
        if not code:return

        # Never call the API again for a fiche already loaded (success or error).
        if code in self.rome_fiche_cache:return
        if code in self.rome_fiche_loading:return
        if code in self.rome_queued_codes:return

        self.rome_queued_codes.add(code)
        self.rome_request_queue.put(code)

    def _rome_request_worker(self):
        while True:
            code=self.rome_request_queue.get()
            self.rome_queued_codes.discard(code)

            if code in self.rome_fiche_cache:
                self.rome_request_queue.task_done()
                continue

            self.rome_fiche_loading.add(code)
            try:
                # Enforce >1 second between every ROME fiche request.
                wait=self.rome_min_interval-(time.monotonic()-self.rome_last_request_at)
                if wait>0:time.sleep(wait)

                cfg=load_cfg()
                token_value=token(cfg.get("client_id",""),cfg.get("client_secret",""),ROME_FICHE_SCOPE)

                req=urllib.request.Request(
                    ROME_FICHE_URL+urllib.parse.quote(code),
                    headers={"Authorization":"Bearer "+token_value,"Accept":"application/json"}
                )

                try:
                    self.rome_last_request_at=time.monotonic()
                    with urllib.request.urlopen(req,timeout=20) as r:
                        data=json.loads(r.read().decode("utf-8"))
                    self.rome_fiche_cache[code]=data

                except urllib.error.HTTPError as e:
                    # A 429 is temporary: wait, then retry once through the queue.
                    if e.code==429:
                        self.rome_last_request_at=time.monotonic()
                        time.sleep(2.25)
                        self.rome_fiche_loading.discard(code)
                        if code not in self.rome_fiche_cache and code not in self.rome_queued_codes:
                            self.rome_queued_codes.add(code)
                            self.rome_request_queue.put(code)
                        continue
                    body=""
                    try:body=e.read().decode("utf-8","ignore")
                    except Exception:pass
                    self.rome_fiche_cache[code]={"_error":"HTTP Error "+str(e.code)+(": "+body[:180] if body else "")}

                except Exception as e:
                    self.rome_fiche_cache[code]={"_error":str(e)}

            except Exception as e:
                self.rome_fiche_cache[code]={"_error":str(e)}
            finally:
                self.rome_fiche_loading.discard(code)
                self.rome_request_queue.task_done()

            # Refresh only if the user is currently looking at this ROME code.
            try:
                self.after(0,lambda c=code:self._refresh_rome_if_visible(c))
            except Exception:pass

    def _refresh_rome_if_visible(self,code):
        try:
            job=self._active_skills_job()
            active_code=str((job or {}).get("code") or "").upper()
            if active_code!=str(code).upper():return
            current=getattr(self,"active_skill_tab","overview")
            # Nearby professions do not depend on rendering the fiche content here.
            if current!="nearby":self.show_skills_tab(current)
        except Exception:
            pass


    def _rome_sections(self,code):
        data=self.rome_fiche_cache.get((code or "").upper())
        out={"knowhow":[],"soft":[],"knowledge":[]}
        if not isinstance(data,dict) or data.get("_error"):return out

        for group in data.get("groupesCompetencesMobilisees",[]) or []:
            enjeu=(group.get("enjeu") or {}).get("libelle","Compétences")
            for c in group.get("competences",[]) or []:
                typ=str(c.get("type") or "").upper().replace("_","-")
                item={"libelle":c.get("libelle",""),"code":c.get("code",""),
                      "type":typ,"groupe":enjeu}
                # Official ROME discriminator:
                # MACRO-SAVOIR-ETRE-PROFESSIONNEL => Savoir-être.
                # MACRO-SAVOIR-FAIRE and COMPETENCE-DETAILLEE => Savoir-faire.
                if typ=="MACRO-SAVOIR-ETRE-PROFESSIONNEL":
                    out["soft"].append(item)
                elif typ in ("MACRO-SAVOIR-FAIRE","COMPETENCE-DETAILLEE"):
                    out["knowhow"].append(item)
                elif typ=="SAVOIR":
                    out["knowledge"].append(item)
                else:
                    # Unknown/missing ROME type: do not display it in a wrong tab.
                    # The item is deliberately ignored until its official type is known.
                    continue

        # Savoirs have their own official ROME groups.
        for group in data.get("groupesSavoirs",[]) or []:
            cat=(group.get("categorieSavoirs") or {}).get("libelle","Savoirs")
            for c in group.get("savoirs",[]) or []:
                item={"libelle":c.get("libelle",""),"code":c.get("code",""),
                      "type":"SAVOIR","groupe":cat}
                # Avoid duplicates if a SAVOIR was also present above.
                if not any(x.get("code")==item["code"] and x.get("libelle")==item["libelle"]
                           for x in out["knowledge"]):
                    out["knowledge"].append(item)
        return out

    def _select_rome_subgroup(self,section,code,group):
        self.rome_subgroup_selection[(str(code).upper(),section)]=group
        if section!="transfer":
            self.rome_subgroup_preferred[section]=group

        if section=="transfer":
            # Refresh only the transferable content zone. This prevents
            # successive tab clicks from accumulating widgets/results.
            zone=getattr(self,"transfer_results_zone",None)
            if zone is not None and zone.winfo_exists():
                for w in zone.winfo_children():
                    w.destroy()
                self._render_transfer_results(str(code).upper(),group)
                self._refresh_transfer_tab_styles(group)
                return

        parent=getattr(self,"skills_content",None)
        if parent is None:return
        for w in parent.winfo_children():w.destroy()
        self._render_rome_items(section,code)

    def _rome_group_tabs(self,section,code,items):
        groups=[]
        for item in items:
            g=str(item.get("groupe") or "Autres").strip()
            if g not in groups:groups.append(g)
        if len(groups)<=1:
            return groups[0] if groups else None

        key=(str(code).upper(),section)
        selected=self.rome_subgroup_selection.get(key)
        preferred=self.rome_subgroup_preferred.get(section)
        if selected not in groups:
            # On profession change, reuse the user's last category whenever
            # the new profession contains it.
            selected=preferred if preferred in groups else groups[0]
            self.rome_subgroup_selection[key]=selected

        parent=getattr(self,"skills_content",self.skills_panel)

        # Compact selector: avoids a large wall of category buttons.
        row=ctk.CTkFrame(parent,fg_color="transparent")
        row.pack(fill="x",padx=20,pady=(8,8))

        var=tk.StringVar(value=selected)
        combo=ttk.Combobox(
            row,
            textvariable=var,
            values=groups,
            state="readonly",
            font=("Segoe UI",9),
            height=min(18,max(6,len(groups)))
        )
        combo.pack(fill="x",expand=True)
        combo.bind("<<ComboboxSelected>>",
                   lambda e:self._select_rome_subgroup(section,code,var.get()))

        return selected


    def _open_metierscope(self,code="",label=""):
        code=str(code or "").strip().upper()
        if code:
            url="https://candidat.francetravail.fr/metierscope/fiche-metier/"+urllib.parse.quote(code)
        else:
            url="https://candidat.francetravail.fr/metierscope/"
        webbrowser.open(url)

    def _render_rome_items(self,section,code):
        parent=getattr(self,"skills_content",self.skills_panel)
        code=(code or "").upper()
        if code in self.rome_fiche_loading or code in self.rome_queued_codes:
            self._info_row("Chargement des données ROME…","Les données du métier sont en cours de récupération.")
            return
        data=self.rome_fiche_cache.get(code)
        if not data:
            self._info_row("Chargement des données ROME…","La fiche métier va être récupérée automatiquement.")
            self.after(20,lambda:self.load_rome_fiche(code))
            return
        if data.get("_error"):
            self._info_row("Impossible de récupérer la fiche ROME",data["_error"])
            return

        items=self._rome_sections(code).get(section,[])
        if not items:
            self._info_row("Aucune donnée dans cette rubrique","La fiche ROME reçue ne contient pas d’élément de ce type.")
            return

        # The page header/title/MetierScope button are rendered by show_skills_tab().
        # Here we render only the actual ROME items, so no duplicate heading appears.
        for item in items[:10]:
            status,detail,color=self._cv_match(item["libelle"])
            self._skill_row(item["libelle"],status,detail,status_color=color,
                            meta=("ROME "+item["code"]) if item["code"] else "")
        if len(items)>10:
            tk.Label(parent,text="10 éléments maximum affichés.",bg=CARD,fg=MUTED,
                     font=("Segoe UI",8)).pack(anchor="w",padx=24,pady=(8,12))

    def refresh_skills(self):
        self._refresh_skills_job_selector()
        if not hasattr(self,"skills_panel"): return
        job=self._active_skills_job()
        target=(job.get("libelle") or "") if isinstance(job,dict) else ""
        code=(job.get("code") or "") if isinstance(job,dict) else ""
        if target:
            txt="Métier ciblé : "+target+((" • Code ROME : "+code) if code else "")+"."
        else:
            txt="Mode exploration : aucun métier ciblé. L’analyse part uniquement des éléments visibles dans le CV."
        self.skills_mode_label.config(text=txt)
        if code:
            self.load_rome_fiche(code)
        self.show_skills_tab(getattr(self,"active_skills_tab","overview"))

    def _rome_identified_items(self,code):
        secs=self._rome_sections(code)
        identified=[]
        for section in ("knowhow","knowledge","soft"):
            for item in secs.get(section,[]):
                status,detail,color=self._cv_match(item.get("libelle",""))
                if status.startswith("✓"):
                    identified.append((section,item,detail))
        return identified

    def _transfer_lists(self,code):
        rome=self._rome_sections(code)
        result={"knowhow":[],"knowledge":[],"soft":[]}
        for sec in ("knowhow","knowledge","soft"):
            for item in list(rome.get(sec,[])):
                status,detail,color=self._cv_match(item.get("libelle",""))
                if status.startswith("✓"):
                    result[sec].append((item,detail))
        return result

    def _refresh_transfer_tab_styles(self,selected):
        buttons=getattr(self,"transfer_tab_buttons",{})
        for sec,b in buttons.items():
            active=(sec==selected)
            try:
                b.configure(
                    fg_color=NAVY if active else "#E9EBF8",
                    hover_color="#202965" if active else "#DDE0F3",
                    text_color="white" if active else NAVY
                )
            except Exception:
                pass

    def _render_transfer_results(self,code,selected):
        zone=getattr(self,"transfer_results_zone",None)
        if zone is None:return
        lists=self._transfer_lists(code)
        labels={"knowhow":"Savoir-faire","knowledge":"Savoirs","soft":"Savoir-être"}
        current=lists.get(selected,[])

        tk.Label(zone,text=labels.get(selected,"Compétences"),bg=CARD,fg=NAVY,
                 font=("Segoe UI",12,"bold")).pack(anchor="w",padx=4,pady=(5,8))

        if not current:
            row=ctk.CTkFrame(zone,fg_color="#F7F8FC",corner_radius=12)
            row.pack(fill="x",padx=0,pady=5)
            tk.Label(row,text="Aucun "+labels.get(selected,"élément").lower()+" transférable identifié",
                     bg="#F7F8FC",fg=NAVY,font=("Segoe UI",10,"bold")).pack(anchor="w",padx=14,pady=(10,3))
            tk.Label(row,text="Aucun élément de cette catégorie ROME n’est suffisamment explicite dans le CV.",
                     bg="#F7F8FC",fg=MUTED,font=("Segoe UI",9),wraplength=820,
                     justify="left").pack(anchor="w",padx=14,pady=(0,10))
            return

        # No 10-item limit here: transferable competencies display in full.
        for item,detail in current:
            row=ctk.CTkFrame(zone,fg_color="#F7F8FC",corner_radius=12)
            row.pack(fill="x",padx=0,pady=5)
            head=tk.Frame(row,bg="#F7F8FC"); head.pack(fill="x",padx=14,pady=(10,2))
            tk.Label(head,text=item["libelle"],bg="#F7F8FC",fg=NAVY,
                     font=("Segoe UI",10,"bold"),wraplength=650,justify="left").pack(side="left",anchor="w")
            meta=labels.get(selected,"Compétence")+((" • ROME "+item["code"]) if item.get("code") else "")
            tk.Label(head,text=meta,bg="#F7F8FC",fg=MUTED,font=("Segoe UI",8)).pack(side="right")
            tk.Label(row,text="✓ Point d’appui identifié",bg="#F7F8FC",fg=GOOD,
                     font=("Segoe UI",9,"bold")).pack(anchor="w",padx=14)
            tk.Label(row,text=detail,bg="#F7F8FC",fg=MUTED,font=("Segoe UI",9),
                     wraplength=820,justify="left").pack(anchor="w",padx=14,pady=(2,10))

    def _clear_target_rome_state(self):
        """Forget the previous target profession when the ROME field is cleared on Home."""
        # Primary target values used by the different screens.
        for attr in ("target_rome","selected_rome","rome_target","rome_code","selected_rome_code",
                     "selected_job","target_job","rome_metier","home_rome_selected"):
            if hasattr(self,attr):
                val=getattr(self,attr)
                if isinstance(val,dict): setattr(self,attr,{})
                elif isinstance(val,list): setattr(self,attr,[])
                else: setattr(self,attr,"")
        # Text/selection variables can otherwise repopulate the old target.
        for attr in ("rome_var","target_rome_var","job_var","metier_var","home_rome_var"):
            v=getattr(self,attr,None)
            try:
                if v is not None and hasattr(v,"set"): v.set("")
            except Exception: pass
        # Force screens to rebuild from the CV-only path.
        self.selected_job=None
        self.primary_offer_job={}
        self.current_offer_rome={}
        self.skills_explore_code=""
        try:
            self.selectedlab.config(text="Aucun métier ROME sélectionné",fg=MUTED)
        except Exception:pass
        try:self.rome_nearby_cache={}
        except Exception:pass
        try:self.refresh_skills()
        except Exception:pass

    def _selected_exploration_jobs(self):
        """Jobs explicitly added by the user while exploring a CV without a primary ROME."""
        vals=getattr(self,"cv_selected_jobs",None)
        if vals is None:
            self.cv_selected_jobs=[]
            vals=self.cv_selected_jobs
        return vals

    def _job_is_selected(self,code):
        return any(str(j.get("code") or "")==str(code or "") for j in self._selected_exploration_jobs())

    def _toggle_cv_job(self,job):
        """Add/remove a CV-exploration job without leaving the current Skills page."""
        code=str(job.get("code") or "")
        vals=list(self._selected_exploration_jobs())
        removing=self._job_is_selected(code)

        if removing:
            self.cv_selected_jobs=[j for j in vals if str(j.get("code") or "")!=code]
        else:
            self.cv_selected_jobs=vals+[{"code":code,"libelle":str(job.get("libelle") or "")}]

        allowed={str(j.get("code") or "") for j in self.cv_selected_jobs}
        cur=[c for c in (getattr(self,"plan_selected_job_codes",[]) or []) if c in allowed]
        if not removing and code not in cur:cur.append(code)
        self.plan_selected_job_codes=cur

        active=str((getattr(self,"current_offer_rome",None) or {}).get("code") or "")
        if active not in allowed:
            self.current_offer_rome=(dict(self.cv_selected_jobs[0]) if self.cv_selected_jobs else {})
        self.primary_offer_job={}

        # Navigation is synchronized, but no page change is triggered.
        self._sync_module_access()

        # Invalidate/rebuild downstream profession selectors when those pages are opened.
        for attr in ("offer_profession_code","formation_profession_code","market_profession_code"):
            if hasattr(self,attr) and str(getattr(self,attr) or "") not in allowed:
                setattr(self,attr,(self.cv_selected_jobs[0]["code"] if self.cv_selected_jobs else ""))

        # Stay on Compétences & métiers > Métiers proches.
        try:self.show_skills_tab("jobs")
        except Exception:pass


    def _sync_module_access(self):
        """Offres/Formations/Marché/Plan are unavailable until at least one profession is selected."""
        has_primary=bool((getattr(self,"selected_job",None) or {}).get("code"))
        enabled=has_primary or bool(self._selected_exploration_jobs())
        for key in ("Offres","Formations","Marché du travail","Plan d’action"):
            b=(getattr(self,"nav_buttons",{}) or {}).get(key)
            if not b:continue
            try:
                b.configure(state=("normal" if enabled else "disabled"),
                            bg=("#EEEFFC" if enabled else "#E4E5EC"),
                            fg=(TEXT if enabled else "#A1A5B2"),
                            activebackground=("#DDDDF7" if enabled else "#E4E5EC"),
                            disabledforeground="#A1A5B2")
            except Exception:pass


    def _jobs_for_downstream_modules(self):
        primary=getattr(self,"selected_job",None) or {}
        vals=[]
        if primary.get("code"):
            vals.append(primary)
            vals.extend(list(getattr(self,"explored_jobs",[]) or []))
            vals.extend(list(getattr(self,"offer_extra_jobs",[]) or []))
            # Jobs added from nearby-profession cards in primary-ROME mode may be
            # stored in either exploration collection depending on the source card.
            vals.extend(list(getattr(self,"cv_selected_jobs",[]) or []))
        else:
            vals.extend(list(self._selected_exploration_jobs()))
        seen=set();out=[]
        for j in vals:
            c=str(j.get("code") or "")
            if c and c not in seen:
                seen.add(c);out.append({"code":c,"libelle":str(j.get("libelle") or "")})
        return out


    def _plan_selected_jobs(self):
        jobs=self._jobs_for_downstream_modules()
        chosen=set(getattr(self,"plan_selected_job_codes",[]) or [])
        return [j for j in jobs if j.get("code") in chosen]

    def _plan_cv_mode_nearby(self):
        if (getattr(self,"selected_job",None) or {}).get("code"):return None
        evidence={j["code"]:j for j in self._cv_exploration_jobs()}
        out=[]
        for j in self._plan_selected_jobs():
            src=evidence.get(j["code"],{})
            out.append({"code":j["code"],"libelle":j["libelle"],
                        "common":src.get("common",[])})
        return out

    def _plan_cv_mode_transferables(self):
        if (getattr(self,"selected_job",None) or {}).get("code"):return None
        return self._cv_transferables()

    def _plan_job_choices(self):
        try:
            _offer_pool=self._offer_jobs()
        except Exception:
            _offer_pool=[]
        if _offer_pool:
            seen=set(); jobs=[]
            for j in list(_offer_pool)+list(self._jobs_for_downstream_modules()):
                c=str(j.get("code") or "")
                if c and c not in seen:
                    seen.add(c); jobs.append({"code":c,"libelle":str(j.get("libelle") or "")})
        else:
            jobs=self._jobs_for_downstream_modules()
        codes={j["code"] for j in jobs}
        cur=[c for c in (getattr(self,"plan_selected_job_codes",[]) or []) if c in codes]
        if not cur and jobs:
            cur=[j["code"] for j in jobs]
        self.plan_selected_job_codes=cur
        return jobs

    def _toggle_plan_job(self,code):
        cur=list(getattr(self,"plan_selected_job_codes",[]) or [])
        if code in cur:
            cur=[c for c in cur if c!=code]
        else:
            cur.append(code)
        self.plan_selected_job_codes=cur
        try:self.refresh_plan_action()
        except Exception:pass

    def _cv_profile_competences(self):
        """CV-only exploration: classify only elements actually identifiable in the CV."""
        txt=str(getattr(self,"cv_text","") or getattr(self,"extracted_text","") or "").lower()
        if not txt:return {"Savoir-faire":[],"Savoirs":[],"Savoir-être":[]}
        # Conservative dictionary: labels are returned only when one of their evidence terms is present.
        refs={
            "Savoir-faire":[
                ("Conduite d’entretien",["entretien individuel","conduite d'entretien","conduite d’entretien","entretiens individuels"]),
                ("Animation d’ateliers",["animation d'atelier","animation d’atelier","animer des ateliers","ateliers cv","atelier collectif"]),
                ("Accompagnement individuel",["accompagnement individuel","accompagner les","accompagnement des"]),
                ("Prospection",["prospection","prospecter"]),
                ("Relation entreprises",["relation entreprise","relations entreprises","partenariat entreprise","entreprises partenaires"]),
                ("Accueil et information du public",["accueil du public","accueillir","information du public"]),
                ("Suivi administratif",["suivi administratif","gestion administrative","dossiers administratifs"]),
                ("Organisation d’événements",["organisation d'événement","organisation d’événement","forum","job dating","évènement emploi","événement emploi"]),
                ("Conseil",["conseiller","conseil aux","conseil des"]),
                ("Analyse des besoins",["analyse des besoins","diagnostic de situation","diagnostic"]),
            ],
            "Savoirs":[
                ("Techniques de recherche d’emploi",["techniques de recherche d'emploi","tre","cv","lettre de motivation","entretien d'embauche"]),
                ("Insertion professionnelle",["insertion professionnelle","conseiller en insertion","cip"]),
                ("Recrutement",["recrutement","sourcing"]),
                ("Formation professionnelle",["formation professionnelle","centre de formation","organisme de formation"]),
                ("Dispositifs d’emploi",["france travail","pôle emploi","pole emploi","mission locale","emploi"]),
                ("Outils bureautiques",["word","excel","powerpoint","pack office","bureautique"]),
            ],
            "Savoir-être":[
                ("Écoute",["écoute","ecoute","écouter"]),
                ("Autonomie",["autonomie","autonome"]),
                ("Organisation",["organisé","organisee","organisée","organisation","rigoureux","rigoureuse"]),
                ("Travail en équipe",["travail en équipe","travail en equipe","esprit d'équipe","esprit d’équipe"]),
                ("Adaptabilité",["adaptabilité","adaptable","polyvalent","polyvalente"]),
                ("Communication",["communication","aisance relationnelle","relationnel"]),
                ("Empathie",["empathie"]),
                ("Réactivité",["réactif","réactive","réactivité"]),
            ]
        }
        out={}
        for typ,items in refs.items():
            found=[]
            for label,terms in items:
                if any(term in txt for term in terms):
                    found.append({"libelle":label,"source":"CV"})
            out[typ]=found
        return out

    def _cv_transferables(self):
        prof=self._cv_profile_competences()
        # In exploration mode, the most reusable know-how and soft skills are shown as transferable.
        vals=[]
        for typ in ("Savoir-faire","Savoir-être"):
            for x in prof.get(typ,[]):
                vals.append({"libelle":x["libelle"],"type":typ,"source":"CV"})
        return vals

    def _cv_exploration_jobs(self):
        """Suggest ROME jobs from CV evidence only. No target ROME is required."""
        prof=self._cv_profile_competences()
        labels={x["libelle"].lower() for arr in prof.values() for x in arr}
        txt=str(getattr(self,"cv_text","") or getattr(self,"extracted_text","") or "").lower()
        # Broad, transparent mapping used only to seed exploration. It never asserts suitability.
        candidates=[
            ("K1801","Conseiller / Conseillère en insertion professionnelle",
             ["accompagnement individuel","conduite d’entretien","animation d’ateliers","insertion professionnelle","relation entreprises"]),
            ("M1502","Développement des ressources humaines",
             ["conduite d’entretien","recrutement","relation entreprises","communication"]),
            ("K2111","Formation professionnelle",
             ["animation d’ateliers","accompagnement individuel","formation professionnelle","communication"]),
            ("M1704","Management relation clientèle",
             ["relation entreprises","conseil","communication","organisation"]),
            ("M1604","Assistanat de direction",
             ["suivi administratif","organisation","outils bureautiques","communication"]),
            ("K1205","Information et médiation sociale",
             ["accueil et information du public","accompagnement individuel","écoute","communication"]),
            ("D1402","Relation commerciale grands comptes et entreprises",
             ["prospection","relation entreprises","conseil","communication"]),
        ]
        scored=[]
        for code,label,need in candidates:
            common=[n for n in need if n.lower() in labels]
            # small text signal only helps ranking; displayed evidence remains the recognized competencies.
            if common:
                scored.append({"code":code,"libelle":label,"common":[{"libelle":x} for x in common],
                               "score":len(common)})
        scored.sort(key=lambda x:x["score"],reverse=True)
        return scored[:5]

    def _render_transferable(self,code):
        parent=getattr(self,"skills_content",self.skills_panel)
        code=(code or "").upper()
        if not code:
            self._info_row("Sélectionnez un métier ROME","Les compétences transférables seront recherchées après sélection d’un métier.")
            return
        if code in self.rome_fiche_loading or code in self.rome_queued_codes:
            self._info_row("Chargement des données ROME…","Analyse des compétences du métier "+code+".")
            return
        data=self.rome_fiche_cache.get(code)
        if not data:
            self._info_row("Chargement des données ROME…","La fiche métier va être récupérée automatiquement.")
            self.after(20,lambda:self.load_rome_fiche(code))
            return
        if data.get("_error"):
            self._info_row("Données ROME indisponibles",data["_error"])
            return

        lists=self._transfer_lists(code)
        labels={"knowhow":"Savoir-faire","knowledge":"Savoirs","soft":"Savoir-être"}
        key=(code,"transfer")
        selected=self.rome_subgroup_selection.get(key,"knowhow")
        if selected not in lists:selected="knowhow"
        self.rome_subgroup_selection[key]=selected

        tk.Label(parent,text="Compétences transférables identifiées dans le CV, classées par type ROME.",
                 bg=CARD,fg=MUTED,font=("Segoe UI",10),wraplength=850,
                 justify="left").pack(anchor="w",padx=24,pady=(0,10))

        tabs=ctk.CTkFrame(parent,fg_color="transparent")
        tabs.pack(fill="x",padx=20,pady=(0,10))
        for col in range(3):tabs.grid_columnconfigure(col,weight=1,uniform="transfer")

        self.transfer_tab_buttons={}
        for i,sec in enumerate(("knowhow","knowledge","soft")):
            active=sec==selected
            btn=ctk.CTkButton(
                tabs,text=f"{labels[sec]} ({len(lists[sec])})",
                corner_radius=11,height=36,
                fg_color=NAVY if active else "#E9EBF8",
                hover_color="#202965" if active else "#DDE0F3",
                text_color="white" if active else NAVY,font=("Segoe UI",8,"bold"),
                command=lambda x=sec:self._select_rome_subgroup("transfer",code,x)
            )
            btn.grid(row=0,column=i,sticky="ew",padx=4)
            self.transfer_tab_buttons[sec]=btn

        # Only this zone changes when clicking Savoir-faire / Savoirs / Savoir-être.
        self.transfer_results_zone=tk.Frame(parent,bg=CARD)
        self.transfer_results_zone.pack(fill="both",expand=True,padx=24,pady=(0,12))
        self._render_transfer_results(code,selected)

    def _fetch_nearby_jobs(self,code):
        """Compare les compétences ROME identifiées dans le CV avec toutes les fiches ROME."""
        code=(code or "").upper()
        if not code or code in self.rome_nearby_loading:
            return
        # Une réponse (ou une erreur temporaire) déjà obtenue pour ce code reste en cache :
        # changer d'onglet ne doit pas déclencher une nouvelle lecture complète du référentiel.
        if code in self.rome_nearby_cache:
            return
        identified=self._rome_identified_items(code)
        source_codes={str(x[1].get("code","")).strip() for x in identified if x[1].get("code")}
        if not source_codes:
            self.rome_nearby_cache[code]=[]
            self.refresh_skills()
            return

        self.rome_nearby_loading.add(code)

        def worker():
            try:
                cfg=load_cfg()
                cid=(cfg.get("client_id") or "").strip()
                secret=(cfg.get("client_secret") or "").strip()
                if not cid or not secret:
                    raise RuntimeError("Identifiants API France Travail manquants dans Connexion API.")

                tok=token(cid,secret,ROME_FICHE_SCOPE)

                champs=("code,metier(libelle,code),"
                        "groupescompetencesmobilisees(competences(libelle,code),enjeu(libelle,code))")
                query=urllib.parse.urlencode({"champs":champs})
                rows=get_json(ROME_FICHES_LIST_URL+"?"+query,tok)
                if not isinstance(rows,list):
                    raise RuntimeError("Format inattendu reçu pour la liste des fiches ROME.")

                scored=[]
                for row in rows:
                    if not isinstance(row,dict): continue
                    met=row.get("metier") or {}
                    rcode=str(met.get("code") or row.get("code") or "").upper().strip()
                    label=str(met.get("libelle") or "").strip()
                    if not rcode or not label or rcode==code: continue

                    comps=[]
                    for grp in row.get("groupesCompetencesMobilisees") or []:
                        for c in (grp.get("competences") or []):
                            cc=str(c.get("code") or "").strip()
                            if cc: comps.append(c)
                    common=[c for c in comps if str(c.get("code") or "").strip() in source_codes]
                    if not common: continue

                    # Score descriptif et transparent : part des compétences du CV identifiées
                    # qui sont aussi mobilisées par l'autre métier. Ce n'est pas une probabilité.
                    coverage=len({str(c.get("code")) for c in common})/max(1,len(source_codes))
                    scored.append({
                        "code":rcode,"libelle":label,
                        "common":common,
                        "target_competences":comps,
                        "common_count":len({str(c.get("code")) for c in common}),
                        "source_count":len(source_codes),
                        "coverage":coverage
                    })

                scored.sort(key=lambda x:(x["common_count"],x["coverage"]),reverse=True)
                self.rome_nearby_cache[code]=scored[:12]
            except Exception as e:
                self.rome_nearby_cache[code]={"_error":(
                    "Le service ROME est momentanément très sollicité. "
                    "La recherche des métiers proches pourra être relancée dans quelques instants."
                    if ("429" in str(e) or "Too Many Requests" in str(e))
                    else str(e))}
            finally:
                self.rome_nearby_loading.discard(code)
                self.after(0,self.refresh_skills)
                if hasattr(self,"plan_zone"):
                    self.after(80,self.refresh_plan_action)

        threading.Thread(target=worker,daemon=True).start()

    def _nearby_from_rome_fiche(self,code):
        data=self.rome_nearby_cache.get((code or "").upper())
        return data if isinstance(data,list) else []

    def _toggle_nearby_job(self,job):
        code=str(job.get("code") or "").strip().upper()
        if not code:return
        exists=any(str(j.get("code") or "").upper()==code for j in self.offer_extra_jobs)

        if exists:
            self.offer_extra_jobs=[j for j in self.offer_extra_jobs
                                   if str(j.get("code") or "").upper()!=code]
            if getattr(self,"skills_explore_code","")==code:self.skills_explore_code=""
            if hasattr(self,"active_offer_job") and self.active_offer_job.get()==code:
                primary=self._primary_offer()
                self.active_offer_job.set(primary.get("code","") if primary else "")
            btn=getattr(self,"nearby_action_buttons",{}).get(code)
            if btn and btn.winfo_exists():btn.configure(text="Ajouter")
            self.status.set("Métier retiré : "+str(job.get("libelle") or code))
        else:
            label=str(job.get("libelle") or "").strip()
            self.offer_extra_jobs.append({"libelle":label,"code":code})
            btn=getattr(self,"nearby_action_buttons",{}).get(code)
            if btn and btn.winfo_exists():btn.configure(text="Retirer")
            self.status.set("Métier ajouté : "+label+" — "+code)

        # Important: no show_skills_tab(), no selector rebuild and no scroll
        # manipulation here. The visible Métiers proches page stays pixel-stable.

    def _choose_nearby_job(self,job):
        label=str(job.get("libelle") or "").strip()
        code=str(job.get("code") or "").strip().upper()
        if not label or not code:return
        if not any(str(j.get("code") or "").upper()==code for j in self.offer_extra_jobs):
            self.offer_extra_jobs.append({"libelle":label,"code":code})
        if hasattr(self,"offer_tabs"):self._refresh_offer_tabs()
        if hasattr(self,"skills_job_selector"):self._refresh_skills_job_selector()
        self.status.set("Métier ajouté : "+label+" — "+code)


    def _refresh_nearby_button_states(self):
        # Re-render only if the user is already on Métiers proches.
        # This avoids changing tabs or showing an empty panel after Add/Remove.
        if getattr(self,"active_skill_tab","")=="nearby":
            self.show_skills_tab("nearby")

    def _nearby_job_card(self,job):
        box=ctk.CTkFrame(self.skills_panel,fg_color="#F6F7FC",corner_radius=14)
        box.pack(fill="x",padx=22,pady=7)

        top=ctk.CTkFrame(box,fg_color="transparent")
        top.pack(fill="x",padx=16,pady=(13,4))
        tk.Label(top,text=job["libelle"],bg="#F6F7FC",fg=NAVY,
                 font=("Segoe UI",10,"bold"),wraplength=620,justify="left").pack(side="left",anchor="w")
        tk.Label(top,text=job["code"],bg="#F6F7FC",fg=MUTED,
                 font=("Segoe UI",9)).pack(side="right",anchor="e")

        n=job.get("common_count",0)
        total=job.get("source_count",0)
        tk.Label(box,
                 text=f"Pourquoi ce métier ?  {n} compétence(s) de votre profil sont également mobilisées dans ce métier.",
                 bg="#F6F7FC",fg=TEXT,font=("Segoe UI",9,"bold"),
                 wraplength=790,justify="left").pack(anchor="w",padx=16,pady=(4,6))

        labels=[str(c.get("libelle") or "") for c in job.get("common",[]) if c.get("libelle")]
        if labels:
            tk.Label(box,text="Compétences communes",
                     bg="#F6F7FC",fg=NAVY,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=16,pady=(2,2))
            tk.Label(box,text=" • ".join(labels[:8]),
                     bg="#F6F7FC",fg=MUTED,font=("Segoe UI",8),
                     wraplength=790,justify="left").pack(anchor="w",padx=16,pady=(0,8))

        # We do not infer possession of the other job's missing competencies.
        tk.Label(box,text="À vérifier avec le candidat",
                 bg="#F6F7FC",fg=NAVY,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=16,pady=(2,2))
        tk.Label(box,
                 text="Les autres compétences attendues pour ce métier doivent être vérifiées avec le candidat. "
                      "Une compétence non identifiée dans le CV ne signifie pas qu’elle est absente.",
                 bg="#F6F7FC",fg=MUTED,font=("Segoe UI",8),
                 wraplength=790,justify="left").pack(anchor="w",padx=16,pady=(0,8))

        tk.Label(box,
                 text=f"Méthode : {n} compétence(s) ROME commune(s) parmi {total} point(s) d’appui identifiés. "
                      "Cet indicateur décrit une proximité de compétences, pas une probabilité d’accès au métier.",
                 bg="#F6F7FC",fg=MUTED,font=("Segoe UI",8),
                 wraplength=790,justify="left").pack(anchor="w",padx=16,pady=(0,10))

        actions=ctk.CTkFrame(box,fg_color="transparent")
        actions.pack(fill="x",padx=16,pady=(0,14))
        already_added=any(str(j.get("code") or "").upper()==str(job.get("code") or "").upper()
                          for j in self.offer_extra_jobs)
        action_btn=ctk.CTkButton(actions,text="Retirer" if already_added else "Ajouter",
                      corner_radius=12,height=34,width=145,
                      fg_color=NAVY,hover_color="#202965",text_color="white",
                      font=("Segoe UI",9,"bold"),
                      command=lambda j=dict(job):self._toggle_nearby_job(j))
        action_btn.pack(side="left")
        self.nearby_action_buttons[str(job.get("code") or "").upper()]=action_btn

    def _retry_nearby_jobs(self,code):
        code=str(code or "").upper()
        cached=self.rome_nearby_cache.get(code)
        if isinstance(cached,dict) and cached.get("_error"):
            self.rome_nearby_cache.pop(code,None)
        self._fetch_nearby_jobs(code)
        self.refresh_skills()

    def _render_nearby_jobs(self,code,target):
        identified=self._rome_identified_items(code) if code else []
        if not target or not code:
            self._info_row("Mode exploration","Sélectionnez un métier ROME pour rechercher des métiers partageant ses compétences.")
            return
        code=code.upper()
        if code in self.rome_fiche_loading:
            self._info_row("Chargement…","Lecture de la fiche ROME "+code+".")
            return
        data=self.rome_fiche_cache.get(code)
        if not data:
            self._info_row("Chargement…","La fiche ROME va être récupérée automatiquement.")
            self.after(20,lambda:self.load_rome_fiche(code))
            return
        if data.get("_error"):
            self._info_row("Données ROME indisponibles",data["_error"])
            return

        self._info_row("Métier de départ",target+" • "+code)
        if identified:
            labels=[x[1]["libelle"] for x in identified[:6]]
            self._info_row("Points d’appui repérés dans le CV"," • ".join(labels))
        else:
            self._info_row("Pas assez d’éléments pour comparer",
                           "Aucune compétence ROME n’est suffisamment explicite dans le CV pour calculer des métiers proches.")
            return

        if code not in self.rome_nearby_cache:
            self._info_row("Recherche des métiers proches…",
                           "Comparaison des compétences identifiées dans le CV avec les fiches métiers du référentiel ROME.")
            self.after(30,lambda:self._fetch_nearby_jobs(code))
            return
        if code in self.rome_nearby_loading:
            self._info_row("Recherche en cours…","Comparaison avec le référentiel ROME.")
            return

        result=self.rome_nearby_cache.get(code)
        if isinstance(result,dict) and result.get("_error"):
            self._info_row("Recherche temporairement indisponible",result["_error"])
            if "momentanément très sollicité" in str(result.get("_error","")):
                ctk.CTkButton(self.skills_panel,text="Réessayer",width=105,height=30,corner_radius=9,
                              fg_color=NAVY,command=lambda c=code:self._retry_nearby_jobs(c)).pack(anchor="w",padx=24,pady=(8,4))
            return
        jobs=result if isinstance(result,list) else []
        if not jobs:
            self._info_row("Aucun métier proche trouvé",
                           "Aucune autre fiche ROME ne partage suffisamment les compétences actuellement identifiées dans le CV.")
            return

        tk.Label(self.skills_panel,text=f"{len(jobs)} métier(s) à explorer — proposés à partir des compétences ROME communes avec le CV.",
                 bg=CARD,fg=MUTED,font=("Segoe UI",10),wraplength=850,justify="left").pack(anchor="w",padx=24,pady=(12,8))
        for job in jobs:
            self._nearby_job_card(job)

    def show_skills_tab(self,key):
        self.active_skill_tab=key
        if not hasattr(self,"skills_panel"): return
        previous_key=getattr(self,"active_skills_tab",None)
        self.active_skills_tab=key
        if previous_key != key:
            try:
                self.skills_panel._parent_canvas.yview_moveto(0.0)
            except Exception:
                try:
                    self.skills_panel._parent_canvas.yview("moveto",0.0)
                except Exception:
                    pass
        for k,b in self.skills_tabs.items():
            if k==key:
                b.configure(fg_color=NAVY,text_color="white",hover_color="#202965")
            else:
                b.configure(fg_color="#E8EAF7",text_color=NAVY,hover_color="#DDE1F3")
        for w in self.skills_panel.winfo_children(): w.destroy()

        # Rétablit la molette sur toute la zone scrollable, y compris les widgets enfants.
        def _skills_wheel(event):
            try:
                canvas=self.skills_panel._parent_canvas
                step=-1 if event.delta>0 else 1
                canvas.yview_scroll(step*12, "units")
                return "break"
            except Exception:
                return None
        def _bind_wheel_tree(widget):
            try: widget.bind("<MouseWheel>",_skills_wheel,add="+")
            except Exception: pass
            try:
                for child in widget.winfo_children(): _bind_wheel_tree(child)
            except Exception: pass
        self.after(80,lambda:_bind_wheel_tree(self.skills_panel))

        # Selector lives inside the white content card on every tab.
        self.skills_job_selector=ctk.CTkFrame(self.skills_panel,fg_color="transparent",height=1)
        self._refresh_skills_job_selector()

        _has_primary=bool((getattr(self,"selected_job",None) or {}).get("code"))
        job=(self._active_skills_job() if _has_primary else {})
        target=(job.get("libelle") or "") if isinstance(job,dict) else ""
        code=(job.get("code") or "") if isinstance(job,dict) else ""
        found=self._skills_evidence()

        titles={
            "overview":"Vue d’ensemble",
            "knowhow":"Savoir-faire professionnels",
            "knowledge":"Savoirs",
            "soft":"Savoir-être professionnels",
            "transfer":"Compétences transférables",
            "jobs":"Métiers proches à explorer",
        }
        if key in ("knowhow","knowledge","soft"):
            title_row=ctk.CTkFrame(self.skills_panel,fg_color="transparent")
            title_row.pack(fill="x",padx=24,pady=(14,5))
            ctk.CTkLabel(title_row,text=titles[key],text_color=TEXT,
                         font=("Segoe UI",15,"bold"),anchor="w").pack(side="left")
            if code:
                ctk.CTkButton(
                    title_row,text="En savoir plus",width=108,height=30,corner_radius=9,
                    fg_color="#E9EBF8",hover_color="#DDE0F3",text_color=NAVY,
                    font=("Segoe UI",8,"bold"),
                    command=lambda c=code:self._open_metierscope(c)
                ).pack(side="left",padx=(12,0))
        else:
            tk.Label(self.skills_panel,text=titles[key],bg=CARD,fg=TEXT,
                     font=("Segoe UI",15,"bold")).pack(anchor="w",padx=24,pady=(14,5))
        self.skills_content=tk.Frame(self.skills_panel,bg=CARD)
        self.skills_content.pack(fill="both",expand=True)

        if not (self.cv_text or "").strip():
            tk.Label(self.skills_content,text="Importez d’abord un CV pour afficher cette analyse.",
                     bg=CARD,fg=MUTED,font=("Segoe UI",10)).pack(anchor="w",padx=24,pady=(4,22))
            return

        if key=="overview":
            subtitle=(f"{target}"+(f" — {code}" if code else "")) if target else "Exploration à partir du CV"
            tk.Label(self.skills_content,text=subtitle,bg=CARD,fg=NAVY,
                     font=("Segoe UI",10,"bold")).pack(anchor="w",padx=24,pady=(0,12))
            tk.Label(self.skills_content,text=f"{len(found)} famille(s) de compétences comportent des indices explicites dans le CV.",
                     bg=CARD,fg=MUTED,font=("Segoe UI",10)).pack(anchor="w",padx=24,pady=(0,12))
            if code and code.upper() in self.rome_fiche_cache and not self.rome_fiche_cache[code.upper()].get("_error"):
                secs=self._rome_sections(code)
                tk.Label(self.skills_content,text=f"Référentiel ROME chargé : {len(secs['knowhow'])} savoir-faire/compétences • {len(secs['knowledge'])} savoirs • {len(secs['soft'])} savoir-être.",
                         bg=CARD,fg=NAVY,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=24,pady=(0,12))

        elif key=="knowhow":
            if not code:
                vals=self._cv_profile_competences().get("Savoir-faire",[])
                tk.Label(self.skills_content,text="Savoir-faire identifiés directement dans le CV.",bg=CARD,fg=MUTED,
                         font=("Segoe UI",10),wraplength=850,justify="left").pack(anchor="w",padx=24,pady=(0,8))
                if vals:
                    for x in vals:self._skill_row(x["libelle"],"✓ Identifiée dans le CV","Élément explicitement repéré dans le CV.","#16803A")
                else:self._info_row("Aucun savoir-faire suffisamment explicite","Le CV ne contient pas assez d’éléments explicites pour cette catégorie.")
            else:
                tk.Label(self.skills_content,text="Savoir-faire officiels de la fiche ROME, comparés aux éléments réellement visibles dans le CV.",
                         bg=CARD,fg=MUTED,font=("Segoe UI",10),wraplength=850,justify="left").pack(anchor="w",padx=24,pady=(0,8))
                self._render_rome_items("knowhow",code)

        elif key=="knowledge":
            if not code:
                vals=self._cv_profile_competences().get("Savoirs",[])
                tk.Label(self.skills_content,text="Savoirs identifiés directement dans le CV.",bg=CARD,fg=MUTED,
                         font=("Segoe UI",10),wraplength=850,justify="left").pack(anchor="w",padx=24,pady=(0,8))
                if vals:
                    for x in vals:self._skill_row(x["libelle"],"✓ Identifiée dans le CV","Élément explicitement repéré dans le CV.","#16803A")
                else:self._info_row("Aucun savoir suffisamment explicite","Le CV ne contient pas assez d’éléments explicites pour cette catégorie.")
            else:
                tk.Label(self.skills_content,text="Savoirs officiels associés au métier. Un savoir non repéré dans le CV reste « à vérifier ».",
                         bg=CARD,fg=MUTED,font=("Segoe UI",10),wraplength=850,justify="left").pack(anchor="w",padx=24,pady=(0,8))
                self._render_rome_items("knowledge",code)

        elif key=="soft":
            if not code:
                vals=self._cv_profile_competences().get("Savoir-être",[])
                tk.Label(self.skills_content,text="Savoir-être explicitement identifiés dans le CV.",bg=CARD,fg=MUTED,
                         font=("Segoe UI",10),wraplength=850,justify="left").pack(anchor="w",padx=24,pady=(0,8))
                if vals:
                    for x in vals:self._skill_row(x["libelle"],"✓ Identifiée dans le CV","Élément explicitement repéré dans le CV.","#16803A")
                else:self._info_row("Aucun savoir-être suffisamment explicite","Le CV ne contient pas assez d’éléments explicites pour cette catégorie.")
            else:
                tk.Label(self.skills_content,text="Savoir-être professionnels de la fiche ROME. Ils ne sont jamais déduits automatiquement d’un intitulé de poste.",
                         bg=CARD,fg=MUTED,font=("Segoe UI",10),wraplength=850,justify="left").pack(anchor="w",padx=24,pady=(0,8))
                self._render_rome_items("soft",code)

        elif key=="transfer":
            if not code:
                vals=self._cv_transferables()
                tk.Label(self.skills_content,text="Compétences reconnues dans le CV pouvant être mobilisées dans plusieurs contextes professionnels.",
                         bg=CARD,fg=MUTED,font=("Segoe UI",10),wraplength=850,justify="left").pack(anchor="w",padx=24,pady=(0,8))
                if vals:
                    for x in vals:self._skill_row(x["libelle"],"✓ Identifiée dans le CV",x["type"]+" • Compétence transférable","#16803A")
                else:self._info_row("Aucune compétence transférable suffisamment explicite","L’analyse ne dispose pas encore d’assez d’éléments explicites.")
            else:
                self._render_transferable(code)

        elif key=="jobs":
            if not code:
                vals=self._cv_exploration_jobs()
                tk.Label(self.skills_content,text="Pistes proposées à partir des compétences reconnues dans le CV. Elles servent à explorer des possibilités.",
                         bg=CARD,fg=MUTED,font=("Segoe UI",10),wraplength=850,justify="left").pack(anchor="w",padx=24,pady=(0,8))
                if vals:
                    for j in vals:
                        common=" • ".join(x["libelle"] for x in j.get("common",[]))
                        row=ctk.CTkFrame(self.skills_content,fg_color="#F7F8FC",corner_radius=12)
                        row.pack(fill="x",padx=24,pady=5)
                        tk.Label(row,text=j["libelle"]+" • ROME "+j["code"],bg="#F7F8FC",fg=NAVY,font=("Segoe UI",10,"bold")).pack(anchor="w",padx=14,pady=(10,3))
                        tk.Label(row,text="Compétences communes : "+common,bg="#F7F8FC",fg="#16803A",font=("Segoe UI",9),
                                 wraplength=790,justify="left").pack(anchor="w",padx=14,pady=(0,8))
                        actions=ctk.CTkFrame(row,fg_color="transparent")
                        actions.pack(fill="x",padx=14,pady=(0,10))
                        ctk.CTkButton(actions,text="Voir MétierScope",width=125,height=30,corner_radius=9,fg_color=NAVY,
                                      command=lambda c=j["code"],l=j["libelle"]:self._open_metierscope(c,l)).pack(side="left",padx=(0,8))
                        _added=self._job_is_selected(j["code"])
                        ctk.CTkButton(actions,text=("Retirer" if _added else "Ajouter"),width=92,height=30,corner_radius=9,
                                      fg_color=("#FFFFFF" if not _added else "#FDECEC"),text_color=(NAVY if not _added else "#B42318"),
                                      border_width=1,border_color=("#2F6FED" if not _added else "#E6A09A"),
                                      command=lambda jj=j:self._toggle_cv_job(jj)).pack(side="left")
                else:self._info_row("Pas encore assez d’éléments","Le CV ne contient pas assez de compétences explicites pour proposer des métiers proches.")
            else:
                self._render_nearby_jobs(code,target)

    def _skill_row(self,title,status,detail,status_color="#3656A3",meta=""):
        row=ctk.CTkFrame(self.skills_panel,fg_color="#F7F8FC",corner_radius=12)
        row.pack(fill="x",padx=24,pady=5)
        head=tk.Frame(row,bg="#F7F8FC");head.pack(fill="x",padx=14,pady=(10,2))
        tk.Label(head,text=title,bg="#F7F8FC",fg=NAVY,font=("Segoe UI",10,"bold"),
                 wraplength=690,justify="left").pack(side="left",anchor="w")
        if meta:
            tk.Label(head,text=meta,bg="#F7F8FC",fg=MUTED,font=("Segoe UI",8)).pack(side="right")
        tk.Label(row,text=status,bg="#F7F8FC",fg=status_color,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=14)
        tk.Label(row,text=detail,bg="#F7F8FC",fg=MUTED,font=("Segoe UI",9),
                 wraplength=790,justify="left").pack(anchor="w",padx=14,pady=(2,10))

    def _info_row(self,title,detail):
        row=ctk.CTkFrame(self.skills_panel,fg_color="#F7F8FC",corner_radius=12)
        row.pack(fill="x",padx=24,pady=5)
        tk.Label(row,text=title,bg="#F7F8FC",fg=NAVY,font=("Segoe UI",10,"bold")).pack(anchor="w",padx=14,pady=(10,3))
        tk.Label(row,text=detail,bg="#F7F8FC",fg=MUTED,font=("Segoe UI",9),
                 wraplength=790,justify="left").pack(anchor="w",padx=14,pady=(0,10))

    def get_offer_rome(self):
        if not (getattr(self,"selected_job",None) or {}).get("code"):
            _cvjobs=self._selected_exploration_jobs()
            if _cvjobs:
                _active=str((getattr(self,"current_offer_rome",None) or {}).get("code") or "")
                for _j in _cvjobs:
                    if str(_j.get("code") or "")==_active:return dict(_j)
                return dict(_cvjobs[0])
        """Retourne sans récursion le métier ROME courant pour la page Offres."""
        try:
            job=self.get_selected_rome()
        except Exception:
            job={}
        if isinstance(job,dict) and job.get("code"):
            return {"libelle":str(job.get("libelle") or self.target.get()).strip(),
                    "code":str(job.get("code")).strip().upper()}
        for attr in ("current_offer_rome","selected_job"):
            sel=getattr(self,attr,None)
            if isinstance(sel,dict) and sel.get("code"):
                return {"libelle":str(sel.get("libelle") or self.target.get()).strip(),
                        "code":str(sel.get("code")).strip().upper()}
        # Last fallback: extract a displayed ROME code from the selection label.
        try:
            txt=str(self.selectedlab.cget("text"))
            m=re.search(r"\b([A-Z]\d{4})\b",txt)
            if m:
                return {"libelle":self.target.get().strip(),"code":m.group(1)}
        except Exception:
            pass
        return {"libelle":self.target.get().strip(),"code":""}

    def offers_page(self):
        p=self.pages["Offres"]
        self.heading(p,"Offres d’emploi","Rechercher des offres France Travail à partir du métier ROME sélectionné.")
        c=self.card(p)
        tk.Label(c,text="Recherche France Travail",bg=CARD,fg=TEXT,font=("Segoe UI",14,"bold")).pack(anchor="w",padx=22,pady=(18,4))
        self.offer_job_label=tk.Label(c,text="Métier : aucun métier ROME sélectionné",bg=CARD,fg=MUTED,font=("Segoe UI",9))
        self.offer_job_label.pack(anchor="w",padx=22,pady=(0,8))
        self.offer_tabs=ctk.CTkFrame(c,fg_color="transparent")
        self.offer_tabs.pack(fill="x",padx=18,pady=(0,10))
        self.active_offer_job=tk.StringVar(value="")
        self._refresh_offer_tabs()
        # Geographic filters. Each field can be used on its own; selecting a more
        # precise territory automatically completes the broader levels.
        geo=tk.Frame(c,bg=CARD);geo.pack(fill="x",padx=22,pady=(0,8))
        self.offer_region_var=tk.StringVar(value="")
        self.offer_dept_var=tk.StringVar(value="")
        self.offer_city_var=tk.StringVar(value="")
        self.offer_regions_by_name={}
        self.offer_regions_by_code={}
        self.offer_depts_by_name={}
        self.offer_depts_by_code={}
        self.offer_cities_by_name={}
        self.offer_geo_sync=False
        self.offer_city_after=None

        for col in range(3):geo.grid_columnconfigure(col,weight=1)
        tk.Label(geo,text="Région",bg=CARD,fg=MUTED,font=("Segoe UI",9,"bold")).grid(row=0,column=0,sticky="w",padx=(0,8))
        tk.Label(geo,text="Département",bg=CARD,fg=MUTED,font=("Segoe UI",9,"bold")).grid(row=0,column=1,sticky="w",padx=8)
        tk.Label(geo,text="Ville",bg=CARD,fg=MUTED,font=("Segoe UI",9,"bold")).grid(row=0,column=2,sticky="w",padx=(8,0))

        self.offer_region_cb=ttk.Combobox(geo,textvariable=self.offer_region_var,state="normal")
        self.offer_dept_cb=ttk.Combobox(geo,textvariable=self.offer_dept_var,state="normal")
        self.offer_city_cb=ttk.Combobox(geo,textvariable=self.offer_city_var,state="normal")
        self.offer_region_cb.grid(row=1,column=0,sticky="ew",padx=(0,8),pady=(4,0))
        self.offer_dept_cb.grid(row=1,column=1,sticky="ew",padx=8,pady=(4,0))
        self.offer_city_cb.grid(row=1,column=2,sticky="ew",padx=(8,0),pady=(4,0))
        self.offer_region_cb.bind("<<ComboboxSelected>>",self._offer_region_selected)
        self.offer_dept_cb.bind("<<ComboboxSelected>>",self._offer_dept_selected)
        self.offer_city_cb.bind("<<ComboboxSelected>>",self._offer_city_selected)
        self.offer_city_cb.bind("<KeyRelease>",self._offer_city_typed)

        row=tk.Frame(c,bg=CARD);row.pack(fill="x",padx=22,pady=(4,14))
        tk.Label(row,text="Contrat",bg=CARD,fg=MUTED,font=("Segoe UI",9,"bold")).pack(side="left")
        self.offer_contract=tk.StringVar(value="Tous")
        ttk.Combobox(row,textvariable=self.offer_contract,state="readonly",
                     values=["Tous","CDI","CDD","Intérim","Alternance","Saisonnier","Autre"],width=18).pack(side="left",padx=(8,18))
        self.rounded_button(row,"Rechercher",self.search_offers,bg=NAVY,width=135,height=38).pack(side="left")
        tk.Label(row,text="Les 3 filtres géographiques peuvent être utilisés séparément.",
                 bg=CARD,fg=MUTED,font=("Segoe UI",8)).pack(side="left",padx=(14,0))
        self.after(100,self._load_offer_geo)
        self.offer_status=tk.Label(c,text="Prêt à rechercher.",bg=CARD,fg=MUTED,font=("Segoe UI",9))
        self.offer_status.pack(anchor="w",padx=22,pady=(0,14))

        offer_wrap=tk.Frame(p,bg=BG)
        offer_wrap.pack(fill="both",expand=True,padx=22,pady=(0,18))
        self.offer_canvas=tk.Canvas(offer_wrap,bg=BG,highlightthickness=0)
        offer_scroll=ttk.Scrollbar(offer_wrap,orient="vertical",command=self.offer_canvas.yview)
        self.offer_results=tk.Frame(self.offer_canvas,bg=BG)
        self.offer_results.bind("<Configure>",lambda e:self.offer_canvas.configure(scrollregion=self.offer_canvas.bbox("all")))
        self.offer_canvas_window=self.offer_canvas.create_window((0,0),window=self.offer_results,anchor="nw")
        self.offer_canvas.bind("<Configure>",lambda e:self.offer_canvas.itemconfigure(self.offer_canvas_window,width=e.width))
        self.offer_canvas.configure(yscrollcommand=offer_scroll.set)
        self.offer_canvas.pack(side="left",fill="both",expand=True)
        offer_scroll.pack(side="right",fill="y")

        def _offer_wheel(event):
            if getattr(event,"num",None)==4:
                self.offer_canvas.yview_scroll(-1,"units")
            elif getattr(event,"num",None)==5:
                self.offer_canvas.yview_scroll(1,"units")
            else:
                delta=getattr(event,"delta",0)
                if delta:
                    steps=int(-1*(delta/120)) if abs(delta)>=120 else (-1 if delta>0 else 1)
                    self.offer_canvas.yview_scroll(steps*1,"units")
            return "break"

        self._offer_wheel=_offer_wheel
        self.offer_canvas.bind("<MouseWheel>",_offer_wheel,add="+")
        self.offer_canvas.bind("<Button-4>",_offer_wheel,add="+")
        self.offer_canvas.bind("<Button-5>",_offer_wheel,add="+")
        self.offer_results.bind("<MouseWheel>",_offer_wheel,add="+")

    def _primary_offer(self):
        p=getattr(self,"primary_offer_job",{})
        if isinstance(p,dict) and p.get("code"):return p
        j=self.get_offer_rome()
        if isinstance(j,dict) and j.get("code"):
            self.primary_offer_job=dict(j);return self.primary_offer_job
        return {}

    def _offer_jobs(self):
        # Without a primary ROME, every job explicitly added from CV exploration
        # becomes a selectable profession in Offers, Training and Labour market.
        if not (getattr(self,"selected_job",None) or {}).get("code"):
            return [dict(j) for j in self._selected_exploration_jobs()]
        jobs=[]; p=self._primary_offer()
        if p.get("code"):jobs.append(p)
        for j in self.offer_extra_jobs:
            if j.get("code") and not any(x.get("code")==j.get("code") for x in jobs):jobs.append(j)
        return jobs


    def _refresh_offer_tabs(self):
        if not hasattr(self,"offer_tabs"):return
        for w in self.offer_tabs.winfo_children():w.destroy()
        jobs=self._offer_jobs()
        if not jobs:return
        active=self.active_offer_job.get()
        if not any(j.get("code")==active for j in jobs):
            active=jobs[0]["code"];self.active_offer_job.set(active)

        # Same visual treatment as Compétences & métiers:
        # one rounded profession block, with the × integrated inside it.
        for col in range(2):
            self.offer_tabs.grid_columnconfigure(col,weight=1,uniform="offer_jobs")

        for i,j in enumerate(jobs):
            code=j["code"]
            is_active=(code==active)
            bg=NAVY if is_active else "#E9EBF8"
            fg="white" if is_active else NAVY
            holder=ctk.CTkFrame(self.offer_tabs,fg_color=bg,corner_radius=14,
                                border_width=0,height=42)
            holder.grid(row=i//2,column=i%2,sticky="ew",padx=4,pady=4)
            holder.grid_propagate(False)
            holder.grid_columnconfigure(0,weight=1)

            prefix="Principal : " if i==0 else ""
            lbl=ctk.CTkLabel(holder,text=prefix+j.get("libelle",code)+" • "+code,
                             text_color=fg,font=("Segoe UI",8,"bold"),anchor="w")
            lbl.grid(row=0,column=0,sticky="nsew",padx=(14,6),pady=5)
            lbl.bind("<Button-1>",lambda e,c=code:self._select_offer_tab(c))
            holder.bind("<Button-1>",lambda e,c=code:self._select_offer_tab(c))

            if i>0:
                xlbl=ctk.CTkLabel(holder,text="×",width=28,text_color=fg,
                                  font=("Segoe UI",13,"bold"),cursor="hand2")
                xlbl.grid(row=0,column=1,padx=(0,8),pady=5)
                xlbl.bind("<Button-1>",lambda e,c=code:self._remove_explored_job(c))


    def _select_offer_tab(self,code):
        self.active_offer_job.set(code);self._refresh_offer_tabs()
        j=self._active_offer()
        self.offer_job_label.config(text="Recherche pour : "+j.get("libelle","")+" • "+j.get("code",""))
        for w in self.offer_results.winfo_children():w.destroy()
        self.offer_status.config(text="Cliquez sur « Rechercher » pour ce métier.",fg=MUTED)

    def _active_offer(self):
        jobs=self._offer_jobs(); code=self.active_offer_job.get() if hasattr(self,"active_offer_job") else ""
        return next((j for j in jobs if j.get("code")==code),jobs[0] if jobs else {})

    def _load_offer_geo(self):
        def work():
            try:
                regions=self.geo_get("https://geo.api.gouv.fr/regions")
                depts=self.geo_get("https://geo.api.gouv.fr/departements")
                self.after(0,lambda:self._set_offer_geo_lists(regions,depts))
            except Exception as ex:
                self.after(0,lambda:self.offer_status.config(text="Territoires indisponibles : "+str(ex),fg="#B45309"))
        threading.Thread(target=work,daemon=True).start()

    def _set_offer_geo_lists(self,regions,depts):
        self.offer_regions_by_name={x.get("nom",""):x.get("code","") for x in regions if x.get("nom")}
        self.offer_regions_by_code={x.get("code",""):x.get("nom","") for x in regions if x.get("code")}
        self.offer_depts_by_name={f"{x.get('nom','')} ({x.get('code','')})":{"code":x.get("code",""),"region":x.get("codeRegion","")} for x in depts if x.get("nom")}
        self.offer_depts_by_code={v["code"]:{"label":k,"region":v["region"]} for k,v in self.offer_depts_by_name.items()}
        self.offer_region_cb["values"]=sorted(self.offer_regions_by_name)
        self.offer_dept_cb["values"]=sorted(self.offer_depts_by_name)

    def _offer_region_selected(self,e=None):
        if self.offer_geo_sync:return
        name=self.offer_region_var.get().strip()
        rcode=self.offer_regions_by_name.get(name,"")
        if not rcode:return
        # Region is valid independently. Filter the department suggestions,
        # but do not force a department selection.
        vals=[k for k,v in self.offer_depts_by_name.items() if v.get("region")==rcode]
        self.offer_dept_cb["values"]=sorted(vals)
        current=self.offer_depts_by_name.get(self.offer_dept_var.get(),{})
        if current and current.get("region")!=rcode:
            self.offer_dept_var.set("")
            self.offer_city_var.set("")
            self.offer_cities_by_name={}

    def _offer_dept_selected(self,e=None):
        if self.offer_geo_sync:return
        info=self.offer_depts_by_name.get(self.offer_dept_var.get().strip())
        if not info:return
        # Department completes Region automatically.
        self.offer_geo_sync=True
        rname=self.offer_regions_by_code.get(info.get("region",""),"")
        if rname:self.offer_region_var.set(rname)
        self.offer_geo_sync=False
        self.offer_city_var.set("")
        self.offer_cities_by_name={}
        self._load_offer_cities_for_department(info.get("code",""))

    def _load_offer_cities_for_department(self,dcode):
        if not dcode:return
        def work():
            try:
                url="https://geo.api.gouv.fr/departements/"+urllib.parse.quote(dcode)+"/communes?fields=nom,code,codeDepartement,codeRegion,codesPostaux&format=json"
                rows=self.geo_get(url)
                self.after(0,lambda:self._set_offer_cities(rows))
            except Exception:pass
        threading.Thread(target=work,daemon=True).start()

    def _set_offer_cities(self,rows):
        self.offer_cities_by_name={}
        labels=[]
        for x in rows:
            name=x.get("nom",""); code=x.get("code","")
            if not name or not code:continue
            # Keep postal code in duplicate city names when available.
            pcs=x.get("codesPostaux") or []
            label=name+((" ("+pcs[0]+")") if pcs else "")
            self.offer_cities_by_name[label]={"code":code,"dept":x.get("codeDepartement",""),"region":x.get("codeRegion",""),"name":name}
            labels.append(label)
        self.offer_city_cb["values"]=sorted(labels)

    def _offer_city_typed(self,e=None):
        if self.offer_geo_sync:return
        q=self.offer_city_var.get().strip()
        if self.offer_city_after:
            try:self.after_cancel(self.offer_city_after)
            except Exception:pass
        if len(q)<2:return
        self.offer_city_after=self.after(500,lambda:self._search_offer_city(q))

    def _search_offer_city(self,q):
        # If a department is selected, local cached cities are enough.
        if self.offer_dept_var.get() and self.offer_cities_by_name:
            nq=self._norm(q)
            vals=[x for x in self.offer_cities_by_name if nq in self._norm(x)][:40]
            self.offer_city_cb["values"]=vals
            return
        def work():
            try:
                url="https://geo.api.gouv.fr/communes?"+urllib.parse.urlencode({
                    "nom":q,"fields":"nom,code,codeDepartement,codeRegion,codesPostaux","boost":"population","limit":30
                })
                rows=self.geo_get(url)
                self.after(0,lambda:self._set_offer_cities(rows))
            except Exception:pass
        threading.Thread(target=work,daemon=True).start()

    def _offer_city_selected(self,e=None):
        if self.offer_geo_sync:return
        info=self.offer_cities_by_name.get(self.offer_city_var.get().strip())
        if not info:return
        # City completes both Department and Region automatically.
        self.offer_geo_sync=True
        d=self.offer_depts_by_code.get(info.get("dept",""),{})
        if d:self.offer_dept_var.set(d.get("label",""))
        rname=self.offer_regions_by_code.get(info.get("region",""),"")
        if rname:self.offer_region_var.set(rname)
        self.offer_geo_sync=False

    def _offer_geo_params(self):
        # Most precise selected level wins for the API request while all three
        # controls remain independent in the interface.
        city=self.offer_cities_by_name.get(self.offer_city_var.get().strip())
        if city and city.get("code"):
            return {"commune":city["code"]}
        dept=self.offer_depts_by_name.get(self.offer_dept_var.get().strip())
        if dept and dept.get("code"):
            return {"departement":dept["code"]}
        region=self.offer_regions_by_name.get(self.offer_region_var.get().strip())
        if region:
            return {"region":region}
        return {}

    def search_offers(self):
        job=self._active_offer()
        code=(job.get("code") or "").strip() if isinstance(job,dict) else ""
        label=(job.get("libelle") or "").strip() if isinstance(job,dict) else ""
        self.offer_job_label.config(text=("Métier : "+label+" • "+code) if code else "Métier : aucun métier ROME sélectionné")
        if not code:
            self.offer_status.config(text="Sélectionnez d’abord un métier ROME dans l’accueil.",fg="#B45309")
            return
        for w in self.offer_results.winfo_children():w.destroy()
        self.offer_status.config(text="Recherche France Travail en cours…",fg=MUTED)

        contract=self.offer_contract.get()
        def worker():
            try:
                cfg=load_cfg()
                cid=(cfg.get("client_id") or "").strip()
                secret=(cfg.get("client_secret") or "").strip()
                if not cid or not secret: raise RuntimeError("Identifiants API manquants dans Connexion API.")
                tok=token(cid,secret,"o2dsoffre api_offresdemploiv2")
                params={"codeROME":code,"range":"0-19"}
                params.update(self._offer_geo_params())
                if contract=="CDI": params["typeContrat"]="CDI"
                elif contract=="CDD": params["typeContrat"]="CDD"
                data=get_json("https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search?"+urllib.parse.urlencode(params),tok)
                rows=data.get("resultats",[]) if isinstance(data,dict) else []
                if contract=="Intérim":
                    rows=[o for o in rows if "interim" in self._norm(str(o.get("natureContrat") or "")+" "+str(o.get("typeContratLibelle") or "")+" "+str(o.get("description") or ""))]
                elif contract=="Alternance":
                    keys=("alternance","apprentissage","professionnalisation")
                    rows=[o for o in rows if any(k in self._norm(str(o.get("natureContrat") or "")+" "+str(o.get("typeContratLibelle") or "")+" "+str(o.get("description") or "")) for k in keys)]
                elif contract=="Saisonnier":
                    rows=[o for o in rows if "saisonn" in self._norm(str(o.get("natureContrat") or "")+" "+str(o.get("typeContratLibelle") or "")+" "+str(o.get("description") or ""))]
                elif contract=="Autre":
                    rows=[o for o in rows if str(o.get("typeContrat") or "") not in ("CDI","CDD")]
                self.after(0,lambda:self.render_offers(rows))
            except Exception as e:
                self.after(0,lambda err=str(e):self.offer_status.config(text="Recherche impossible : "+err,fg="#B91C1C"))
        threading.Thread(target=worker,daemon=True).start()

    def _bind_offer_wheel_tree(self,widget):
        try:
            widget.bind("<MouseWheel>",self._offer_wheel,add="+")
            widget.bind("<Button-4>",self._offer_wheel,add="+")
            widget.bind("<Button-5>",self._offer_wheel,add="+")
            for child in widget.winfo_children():
                self._bind_offer_wheel_tree(child)
        except Exception:
            pass

    def _open_ft_offer(self,offer):
        # France Travail API commonly exposes origineOffre.urlOrigine.
        # Use only a URL actually returned by the API; never construct one.
        origin=offer.get("origineOffre") or {}
        url=str(origin.get("urlOrigine") or "").strip()
        if not url:
            # Some responses may expose a direct URL at top level.
            for key in ("urlOrigine","url","lien"):
                val=str(offer.get(key) or "").strip()
                if val.startswith("http"):
                    url=val;break
        if url.startswith("http"):
            webbrowser.open(url)
        else:
            self.offer_status.config(text="Le lien de cette offre n’est pas fourni dans la réponse France Travail.",fg="#B45309")

    def _comparison_offer_key(self,offer):
        if not isinstance(offer,dict): return ""
        return str(offer.get("id") or offer.get("reference") or (str(offer.get("intitule") or "")+"|"+str((offer.get("entreprise") or {}).get("nom") or "")+"|"+str((offer.get("lieuTravail") or {}).get("libelle") or "")))

    def _toggle_comparison_offer(self,offer):
        """Plusieurs offres peuvent être préparées; CV ↔ Offre en compare une seule à la fois."""
        key=self._comparison_offer_key(offer)
        rows=list(getattr(self,"comparison_offers",[]) or [])
        found=next((i for i,x in enumerate(rows) if self._comparison_offer_key(x)==key),None)
        if found is None: rows.append(dict(offer or {}))
        else: rows.pop(found)
        self.comparison_offers=rows
        try:self.render_offers(getattr(self,"last_offer_rows",[]) or [])
        except Exception:pass
        if hasattr(self,"cv_offer_method") and self.cv_offer_method.get()=="offers":
            try:self._cv_offer_method_changed()
            except Exception:pass

    def render_offers(self,rows):
        self.last_offer_rows=list(rows or [])
        for w in self.offer_results.winfo_children():w.destroy()
        self.offer_status.config(text=f"{len(rows)} offre(s) affichée(s).",fg=GOOD)
        if not rows:
            box=ctk.CTkFrame(self.offer_results,fg_color="#F6F7FC",corner_radius=14);box.pack(fill="x",pady=6)
            tk.Label(box,text="Aucune offre trouvée",bg="#F6F7FC",fg=NAVY,font=("Segoe UI",10,"bold")).pack(anchor="w",padx=16,pady=14)
            self._bind_offer_wheel_tree(box)
            return
        for o in rows:
            title=str(o.get("intitule") or "Offre d’emploi")
            ent=o.get("entreprise") or {}; company=str(ent.get("nom") or "Entreprise non renseignée")
            lieu=o.get("lieuTravail") or {}; place=str(lieu.get("libelle") or "Lieu non renseigné")
            contract=str(o.get("typeContratLibelle") or o.get("typeContrat") or "Contrat non renseigné")
            salary=o.get("salaire") or {}; sal=str(salary.get("libelle") or "Salaire non renseigné")
            date=str(o.get("dateCreation") or "")
            desc=str(o.get("description") or "").replace("\n"," ").strip()
            box=ctk.CTkFrame(self.offer_results,fg_color="#F6F7FC",corner_radius=14);box.pack(fill="x",pady=7)
            top=tk.Frame(box,bg="#F6F7FC");top.pack(fill="x",padx=16,pady=(12,3))
            tk.Label(top,text=title,bg="#F6F7FC",fg=NAVY,font=("Segoe UI",10,"bold"),
                     wraplength=650,justify="left").pack(side="left")
            tk.Label(top,text=contract,bg="#F6F7FC",fg=MUTED,font=("Segoe UI",8)).pack(side="right")
            tk.Label(box,text=company+" • "+place,bg="#F6F7FC",fg=TEXT,font=("Segoe UI",9)).pack(anchor="w",padx=16,pady=2)
            tk.Label(box,text=sal+((" • Publiée le "+date[:10]) if date else ""),
                     bg="#F6F7FC",fg=MUTED,font=("Segoe UI",8)).pack(anchor="w",padx=16,pady=(0,5))
            if desc:
                tk.Label(box,text=desc[:420]+("…" if len(desc)>420 else ""),bg="#F6F7FC",fg=MUTED,
                         font=("Segoe UI",8),wraplength=800,justify="left").pack(anchor="w",padx=16,pady=(0,8))
            actions=ctk.CTkFrame(box,fg_color="transparent");actions.pack(fill="x",padx=16,pady=(0,14))
            ctk.CTkButton(actions,text="Voir l’offre sur France Travail",corner_radius=12,height=34,width=205,
                          fg_color=NAVY,hover_color="#202965",text_color="white",font=("Segoe UI",9,"bold"),
                          command=lambda offer=dict(o):self._open_ft_offer(offer)).pack(side="left")
            oid=self._comparison_offer_key(o)
            selected=any(self._comparison_offer_key(x)==oid for x in (getattr(self,"comparison_offers",[]) or []))
            ctk.CTkButton(actions,text=("Retirer de la comparaison" if selected else "Ajouter à la comparaison"),
                          corner_radius=12,height=34,width=190,fg_color=(MUTED if selected else PURPLE),
                          text_color="white",font=("Segoe UI",9,"bold"),
                          command=lambda offer=dict(o):self._toggle_comparison_offer(offer)).pack(side="left",padx=(8,0))
            self._bind_offer_wheel_tree(box)


    def formations_page(self):
        p=self.pages["Formations"]
        self.heading(p,"Formations","Rechercher des formations en lien avec le métier ROME et le territoire.")
        c=self.card(p)
        tk.Label(c,text="Recherche de formations",bg=CARD,fg=TEXT,font=("Segoe UI",14,"bold")).pack(anchor="w",padx=22,pady=(18,4))
        self.training_job_label=tk.Label(c,text="Métier : aucun métier ROME sélectionné",bg=CARD,fg=MUTED,font=("Segoe UI",9))
        self.training_job_label.pack(anchor="w",padx=22,pady=(0,8))
        self.training_tabs=ctk.CTkFrame(c,fg_color="transparent")
        self.training_tabs.pack(fill="x",padx=18,pady=(0,10))
        self.active_training_job=tk.StringVar(value="")
        self._refresh_training_tabs()

        geo=tk.Frame(c,bg=CARD); geo.pack(fill="x",padx=22,pady=(0,8))
        for col in range(3): geo.grid_columnconfigure(col,weight=1)
        tk.Label(geo,text="Région",bg=CARD,fg=MUTED,font=("Segoe UI",9,"bold")).grid(row=0,column=0,sticky="w",padx=(0,8))
        tk.Label(geo,text="Département",bg=CARD,fg=MUTED,font=("Segoe UI",9,"bold")).grid(row=0,column=1,sticky="w",padx=8)
        tk.Label(geo,text="Ville",bg=CARD,fg=MUTED,font=("Segoe UI",9,"bold")).grid(row=0,column=2,sticky="w",padx=(8,0))
        self.training_region_var=tk.StringVar(value="")
        self.training_dept_var=tk.StringVar(value="")
        self.training_city_var=tk.StringVar(value="")
        self.training_region_cb=ttk.Combobox(geo,textvariable=self.training_region_var,state="normal")
        self.training_dept_cb=ttk.Combobox(geo,textvariable=self.training_dept_var,state="normal")
        self.training_city_cb=ttk.Combobox(geo,textvariable=self.training_city_var,state="normal")
        self.training_region_cb.grid(row=1,column=0,sticky="ew",padx=(0,8),pady=(4,0))
        self.training_dept_cb.grid(row=1,column=1,sticky="ew",padx=8,pady=(4,0))
        self.training_city_cb.grid(row=1,column=2,sticky="ew",padx=(8,0),pady=(4,0))

        # Reuse the already loaded geographic reference data from the Offers module.
        def sync_geo():
            try:
                self.training_region_cb["values"]=list(self.offer_regions_by_name.keys())
                self.training_dept_cb["values"]=list(self.offer_depts_by_name.keys())
                self.training_city_cb["values"]=list(self.offer_cities_by_name.keys())
                # Start with the territory chosen on the home page when available.
                rv=self.region_var.get().strip(); dv=self.dept_var.get().strip(); cv=self.city_var.get().strip()
                if rv:self.training_region_var.set(rv)
                if dv:self.training_dept_var.set(dv)
                if cv:self.training_city_var.set(cv)
            except Exception: pass
        self.after(350,sync_geo)

        def region_pick(e=None):
            name=self.training_region_var.get().strip()
            code=self.offer_regions_by_name.get(name)
            if not code:return
            vals=[d.get("label","") for d in self.offer_depts_by_code.values() if d.get("region")==code]
            self.training_dept_cb["values"]=sorted(set(x for x in vals if x))
        def dept_pick(e=None):
            name=self.training_dept_var.get().strip()
            d=self.offer_depts_by_name.get(name,{})
            if d.get("region"):
                rn=self.offer_regions_by_code.get(d["region"],"")
                if rn:self.training_region_var.set(rn)
            code=d.get("code")
            if code:
                self._load_training_cities(code)
        def city_pick(e=None):
            info=self.offer_cities_by_name.get(self.training_city_var.get().strip(),{})
            if not info:return
            d=self.offer_depts_by_code.get(info.get("dept",""),{})
            if d:self.training_dept_var.set(d.get("label",""))
            rn=self.offer_regions_by_code.get(info.get("region",""),"")
            if rn:self.training_region_var.set(rn)
        self.training_region_cb.bind("<<ComboboxSelected>>",region_pick)
        self.training_dept_cb.bind("<<ComboboxSelected>>",dept_pick)
        self.training_city_cb.bind("<<ComboboxSelected>>",city_pick)

        row=tk.Frame(c,bg=CARD); row.pack(fill="x",padx=22,pady=(5,12))
        self.rounded_button(row,"Rechercher les formations",self.search_formations,bg=NAVY,width=205,height=38).pack(side="left")
        self.training_status=tk.Label(c,text="Prêt à rechercher.",bg=CARD,fg=MUTED,font=("Segoe UI",9))
        self.training_status.pack(anchor="w",padx=22,pady=(0,14))

        wrap=tk.Frame(p,bg=BG); wrap.pack(fill="both",expand=True,padx=22,pady=(0,18))
        self.training_canvas=tk.Canvas(wrap,bg=BG,highlightthickness=0)
        sb=ttk.Scrollbar(wrap,orient="vertical",command=self.training_canvas.yview)
        self.training_results=tk.Frame(self.training_canvas,bg=BG)
        self.training_results.bind("<Configure>",lambda e:self.training_canvas.configure(scrollregion=self.training_canvas.bbox("all")))
        win=self.training_canvas.create_window((0,0),window=self.training_results,anchor="nw")
        self.training_canvas.bind("<Configure>",lambda e:self.training_canvas.itemconfigure(win,width=e.width))
        self.training_canvas.configure(yscrollcommand=sb.set)
        self.training_canvas.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
        def wheel(e):
            d=getattr(e,"delta",0)
            if d:self.training_canvas.yview_scroll((int(-1*(d/120)) if abs(d)>=120 else (-1 if d>0 else 1))*4,"units")
            elif getattr(e,"num",0)==4:self.training_canvas.yview_scroll(-4,"units")
            elif getattr(e,"num",0)==5:self.training_canvas.yview_scroll(4,"units")
            return "break"
        self._training_wheel=wheel
        self.training_canvas.bind("<MouseWheel>",wheel,add="+")
        self.training_canvas.bind("<Button-4>",wheel,add="+")
        self.training_canvas.bind("<Button-5>",wheel,add="+")

    def _training_jobs(self):
        return self._offer_jobs()

    def _active_training_job(self):
        jobs=self._training_jobs()
        code=self.active_training_job.get() if hasattr(self,"active_training_job") else ""
        return next((j for j in jobs if j.get("code")==code),jobs[0] if jobs else {})

    def _refresh_training_tabs(self):
        if not hasattr(self,"training_tabs"):return
        for w in self.training_tabs.winfo_children():w.destroy()
        jobs=self._training_jobs()
        if not jobs:return
        active=self.active_training_job.get()
        if not any(j.get("code")==active for j in jobs):
            active=jobs[0].get("code","")
            self.active_training_job.set(active)

        for col in range(2):
            self.training_tabs.grid_columnconfigure(col,weight=1,uniform="training_jobs")

        for i,j in enumerate(jobs):
            code=j.get("code","")
            is_active=(code==active)
            bg=NAVY if is_active else "#E9EBF8"
            fg="white" if is_active else NAVY
            holder=ctk.CTkFrame(self.training_tabs,fg_color=bg,corner_radius=14,
                                border_width=0,height=42)
            holder.grid(row=i//2,column=i%2,sticky="ew",padx=4,pady=4)
            holder.grid_propagate(False)
            holder.grid_columnconfigure(0,weight=1)

            prefix="Principal : " if i==0 else ""
            lbl=ctk.CTkLabel(holder,text=prefix+j.get("libelle",code)+" • "+code,
                             text_color=fg,font=("Segoe UI",8,"bold"),anchor="w")
            lbl.grid(row=0,column=0,sticky="nsew",padx=(14,6),pady=5)
            lbl.bind("<Button-1>",lambda e,c=code:self._select_training_tab(c))
            holder.bind("<Button-1>",lambda e,c=code:self._select_training_tab(c))

            if i>0:
                xlbl=ctk.CTkLabel(holder,text="×",width=28,text_color=fg,
                                  font=("Segoe UI",13,"bold"),cursor="hand2")
                xlbl.grid(row=0,column=1,padx=(0,8),pady=5)
                xlbl.bind("<Button-1>",lambda e,c=code:self._remove_training_job(c))

    def _select_training_tab(self,code):
        self.active_training_job.set(str(code or "").upper())
        self._refresh_training_tabs()
        job=self._active_training_job()
        self.training_job_label.config(
            text="Recherche pour : "+job.get("libelle","")+" • "+job.get("code",""))
        for w in self.training_results.winfo_children():w.destroy()
        self.training_status.config(text="Cliquez sur « Rechercher les formations » pour ce métier.",fg=MUTED)

    def _remove_training_job(self,code):
        if not (getattr(self,"selected_job",None) or {}).get("code"):
            _match=next((j for j in self._selected_exploration_jobs()
                         if str(j.get("code") or "").upper()==str(code or "").upper()),None)
            if _match:
                self._toggle_cv_job(_match)
                return
        code=str(code or "").upper()
        if not code:return
        self.offer_extra_jobs=[j for j in self.offer_extra_jobs
                               if str(j.get("code") or "").upper()!=code]
        if hasattr(self,"active_training_job") and self.active_training_job.get()==code:
            jobs=self._training_jobs()
            self.active_training_job.set(jobs[0].get("code","") if jobs else "")
        if hasattr(self,"active_offer_job") and self.active_offer_job.get()==code:
            jobs=self._offer_jobs()
            self.active_offer_job.set(jobs[0].get("code","") if jobs else "")
        if getattr(self,"skills_explore_code","")==code:
            self.skills_explore_code=""
        if hasattr(self,"training_tabs"):self._refresh_training_tabs()
        if hasattr(self,"offer_tabs"):self._refresh_offer_tabs()
        btn=getattr(self,"nearby_action_buttons",{}).get(code)
        if btn and btn.winfo_exists():btn.configure(text="Ajouter")
        job=self._active_training_job()
        if hasattr(self,"training_job_label"):
            self.training_job_label.config(
                text=("Recherche pour : "+job.get("libelle","")+" • "+job.get("code",""))
                if job.get("code") else "Métier : aucun métier ROME sélectionné")
        if hasattr(self,"training_results"):
            for w in self.training_results.winfo_children():w.destroy()
        if hasattr(self,"training_status"):
            self.training_status.config(text="Métier exploré retiré.",fg=MUTED)

    def _load_training_cities(self,dept):
        def worker():
            try:
                data=get_json("https://geo.api.gouv.fr/communes?"+urllib.parse.urlencode(
                    {"codeDepartement":dept,"fields":"nom,code,codeDepartement,codeRegion","format":"json"}),"")
            except Exception:
                try:
                    with urllib.request.urlopen("https://geo.api.gouv.fr/communes?"+urllib.parse.urlencode(
                        {"codeDepartement":dept,"fields":"nom,code,codeDepartement,codeRegion","format":"json"}),timeout=15) as r:
                        data=json.loads(r.read().decode())
                except Exception:return
            vals=[]
            for x in data if isinstance(data,list) else []:
                name=x.get("nom","")
                if name:
                    vals.append(name)
                    self.offer_cities_by_name[name]={"code":x.get("code",""),"dept":x.get("codeDepartement",""),"region":x.get("codeRegion","")}
            self.after(0,lambda:self.training_city_cb.configure(values=sorted(vals)))
        threading.Thread(target=worker,daemon=True).start()

    def _training_geo_params(self):
        city=self.offer_cities_by_name.get(self.training_city_var.get().strip(),{})
        if city.get("code"):return {"codeCommune":city["code"]}
        dept=self.offer_depts_by_name.get(self.training_dept_var.get().strip(),{})
        if dept.get("code"):return {"codeDepartement":dept["code"]}
        return {}

    def _training_public_url(self):
        job=self._active_training_job()
        code=(job.get("code") or "").strip().upper()
        params={"quoi":code}
        city=self.offer_cities_by_name.get(self.training_city_var.get().strip(),{})
        dept=self.offer_depts_by_name.get(self.training_dept_var.get().strip(),{})
        region_name=self.training_region_var.get().strip()
        region_code=self.offer_regions_by_name.get(region_name,"")

        # France Travail's public catalogue accepts ROME in "quoi" and
        # REGION-/DEPARTEMENT- locations. Commune is used when an INSEE code is known.
        if city.get("code"):
            params["ou"]="COMMUNE-"+str(city["code"])
        elif dept.get("code"):
            params["ou"]="DEPARTEMENT-"+str(dept["code"])
        elif region_code:
            params["ou"]="REGION-"+str(region_code)
        return "https://candidat.francetravail.fr/formations/recherche?"+urllib.parse.urlencode(params)

    def search_formations(self):
        job=self._active_training_job()
        code=(job.get("code") or "").strip().upper()
        label=(job.get("libelle") or "").strip()
        self.training_job_label.config(
            text=("Recherche pour : "+label+" • "+code) if code else "Métier : aucun métier ROME sélectionné")
        if not code:
            self.training_status.config(text="Sélectionnez d’abord un métier ROME.",fg=WARN)
            return
        for w in self.training_results.winfo_children():w.destroy()

        # Open Formation is not a catalogue-search endpoint. The previous guessed
        # /openformation/v1/formations route returned HTTP 404. We therefore use
        # the official France Travail training catalogue with the selected ROME
        # and territory instead of displaying a false API error.
        url=self._training_public_url()
        self.training_status.config(
            text="Ouverture du catalogue France Travail avec le métier et le territoire sélectionnés.",fg=GOOD)
        webbrowser.open(url)


    def _training_value(self,o,*keys):
        for key in keys:
            cur=o
            try:
                for part in key.split("."):
                    cur=cur.get(part) if isinstance(cur,dict) else None
                if cur not in (None,"",[]):return cur
            except Exception:pass
        return ""

    def render_formations(self,rows):
        for w in self.training_results.winfo_children():w.destroy()
        rows=list(rows or [])[:30]
        self.training_status.config(text=f"{len(rows)} formation(s) affichée(s).",fg=GOOD)
        if not rows:
            b=ctk.CTkFrame(self.training_results,fg_color="#F6F7FC",corner_radius=14);b.pack(fill="x",pady=6)
            tk.Label(b,text="Aucune formation trouvée pour ces critères.",bg="#F6F7FC",fg=NAVY,font=("Segoe UI",10,"bold")).pack(anchor="w",padx=16,pady=14)
            return
        for o in rows:
            title=str(self._training_value(o,"intitule","intituleFormation","formation.intitule","libelle") or "Formation")
            org=str(self._training_value(o,"organisme.nom","organismeFormation.nom","nomOrganisme","organisme") or "")
            city=str(self._training_value(o,"lieuFormation.ville","lieu.ville","ville","commune.libelle") or "")
            modality=str(self._training_value(o,"modaliteEnseignement","modalite","modalites") or "")
            cert=str(self._training_value(o,"certification.libelle","certification","niveauSortie") or "")
            start=str(self._training_value(o,"dateDebut","sessions.0.dateDebut") or "")
            end=str(self._training_value(o,"dateFin","sessions.0.dateFin") or "")
            box=ctk.CTkFrame(self.training_results,fg_color="#F6F7FC",corner_radius=14);box.pack(fill="x",pady=6)
            tk.Label(box,text=title,bg="#F6F7FC",fg=NAVY,font=("Segoe UI",11,"bold"),
                     wraplength=790,justify="left").pack(anchor="w",padx=16,pady=(13,4))
            details=[x for x in [org,city,modality,cert] if x]
            if details:tk.Label(box,text=" • ".join(details),bg="#F6F7FC",fg=TEXT,font=("Segoe UI",9),
                                wraplength=800,justify="left").pack(anchor="w",padx=16,pady=(0,4))
            if start or end:
                tk.Label(box,text=("Dates : "+start+(" → "+end if end else "")),bg="#F6F7FC",fg=MUTED,
                         font=("Segoe UI",8)).pack(anchor="w",padx=16,pady=(0,6))
            tk.Label(box,text="Les informations de financement dépendent de la situation du candidat et doivent être vérifiées avant engagement.",
                     bg="#F6F7FC",fg=MUTED,font=("Segoe UI",8),wraplength=800,justify="left").pack(anchor="w",padx=16,pady=(0,12))
            self._bind_training_wheel(box)

    def _bind_training_wheel(self,w):
        try:
            w.bind("<MouseWheel>",self._training_wheel,add="+");w.bind("<Button-4>",self._training_wheel,add="+");w.bind("<Button-5>",self._training_wheel,add="+")
            for c in w.winfo_children():self._bind_training_wheel(c)
        except Exception:pass

    def _open_training_search(self):
        webbrowser.open(self._training_public_url())

    def market_page(self):
        page=self.pages["Marché du travail"]
        self.heading(page,"Marché du travail","Consultez MétierScope pour le métier principal ou les métiers explorés.")

        card=self.card(page)
        tk.Label(card,text="Choisir le métier à consulter",bg=CARD,fg=TEXT,
                 font=("Segoe UI",13,"bold")).pack(anchor="w",padx=22,pady=(16,3))
        tk.Label(card,text="Le métier principal reste inchangé. Les métiers proches ajoutés dans Compétences & métiers apparaissent ici automatiquement.",
                 bg=CARD,fg=MUTED,font=("Segoe UI",9),wraplength=850,justify="left").pack(anchor="w",padx=22,pady=(0,10))

        self.market_tabs=ctk.CTkFrame(card,fg_color="transparent")
        self.market_tabs.pack(fill="x",padx=18,pady=(0,14))
        self.active_market_job=tk.StringVar(value="")
        self._refresh_market_tabs()

        self.market_scope_card=ctk.CTkFrame(page,fg_color=CARD,border_color=LINE,border_width=1,corner_radius=22)
        self.market_scope_card.pack(fill="x",padx=30,pady=(0,18))
        self._refresh_market_scope()

    def _refresh_market_scope(self):
        if not hasattr(self,"market_scope_card"):return
        for w in self.market_scope_card.winfo_children():w.destroy()
        j=self._active_market_job()
        code=str(j.get("code") or "").strip().upper()
        label=str(j.get("libelle") or "Métier sélectionné").strip()
        tk.Label(self.market_scope_card,text=label,bg=CARD,fg=NAVY,
                 font=("Segoe UI",15,"bold")).pack(anchor="w",padx=22,pady=(20,2))
        if code:
            tk.Label(self.market_scope_card,text="ROME "+code,bg=CARD,fg=MUTED,
                     font=("Segoe UI",9)).pack(anchor="w",padx=22,pady=(0,6))
            tk.Label(self.market_scope_card,text="Ouvrez la fiche MétierScope officielle de ce métier pour consulter les informations métier et territoriales proposées par France Travail.",
                     bg=CARD,fg=TEXT,font=("Segoe UI",9),wraplength=820,justify="left").pack(anchor="w",padx=22,pady=(0,14))
            ctk.CTkButton(self.market_scope_card,text="Ouvrir MétierScope",height=42,corner_radius=12,
                          fg_color=NAVY,hover_color="#202965",
                          command=lambda c=code,l=label:self._open_metierscope(c,l)).pack(anchor="w",padx=22,pady=(0,20))
        else:
            tk.Label(self.market_scope_card,text="Sélectionnez d’abord un métier ROME.",
                     bg=CARD,fg=MUTED,font=("Segoe UI",9)).pack(anchor="w",padx=22,pady=(0,20))

    def _market_jobs(self):
        return self._offer_jobs()

    def _active_market_job(self):
        jobs=self._market_jobs()
        code=self.active_market_job.get() if hasattr(self,"active_market_job") else ""
        return next((j for j in jobs if j.get("code")==code),jobs[0] if jobs else {})

    def _refresh_market_tabs(self):
        if not hasattr(self,"market_tabs"):return
        for w in self.market_tabs.winfo_children():w.destroy()
        jobs=self._market_jobs()
        if not jobs:return
        active=self.active_market_job.get()
        if not any(j.get("code")==active for j in jobs):
            active=jobs[0].get("code","");self.active_market_job.set(active)
        for col in range(2):self.market_tabs.grid_columnconfigure(col,weight=1,uniform="market_jobs")
        for i,j in enumerate(jobs):
            code=j.get("code","");sel=code==active
            bg=NAVY if sel else "#E9EBF8";fg="white" if sel else NAVY
            h=ctk.CTkFrame(self.market_tabs,fg_color=bg,corner_radius=14,height=42)
            h.grid(row=i//2,column=i%2,sticky="ew",padx=4,pady=4);h.grid_propagate(False);h.grid_columnconfigure(0,weight=1)
            txt=("Principal : " if i==0 else "")+j.get("libelle",code)+" • "+code
            lab=ctk.CTkLabel(h,text=txt,text_color=fg,font=("Segoe UI",8,"bold"),anchor="w")
            lab.grid(row=0,column=0,sticky="nsew",padx=(14,6),pady=5)
            lab.bind("<Button-1>",lambda e,c=code:self._select_market_tab(c));h.bind("<Button-1>",lambda e,c=code:self._select_market_tab(c))
            if i>0:
                x=ctk.CTkLabel(h,text="×",width=28,text_color=fg,font=("Segoe UI",13,"bold"),cursor="hand2")
                x.grid(row=0,column=1,padx=(0,8));x.bind("<Button-1>",lambda e,c=code:self._remove_market_job(c))

    def _select_market_tab(self,code):
        self.active_market_job.set(str(code or "").upper())
        self._refresh_market_tabs()
        self._refresh_market_scope()

    def _remove_market_job(self,code):
        if not (getattr(self,"selected_job",None) or {}).get("code"):
            _match=next((j for j in self._selected_exploration_jobs()
                         if str(j.get("code") or "").upper()==str(code or "").upper()),None)
            if _match:
                self._toggle_cv_job(_match)
                return
        code=str(code or "").upper()
        self.offer_extra_jobs=[j for j in self.offer_extra_jobs if str(j.get("code") or "").upper()!=code]
        if self.active_market_job.get()==code:
            jobs=self._market_jobs();self.active_market_job.set(jobs[0].get("code","") if jobs else "")
        if hasattr(self,"active_training_job") and self.active_training_job.get()==code:
            jobs=self._training_jobs();self.active_training_job.set(jobs[0].get("code","") if jobs else "")
        if hasattr(self,"active_offer_job") and self.active_offer_job.get()==code:
            jobs=self._offer_jobs();self.active_offer_job.set(jobs[0].get("code","") if jobs else "")
        if getattr(self,"skills_explore_code","")==code:self.skills_explore_code=""
        self._refresh_market_tabs()
        if hasattr(self,"training_tabs"):self._refresh_training_tabs()
        if hasattr(self,"offer_tabs"):self._refresh_offer_tabs()
        btn=getattr(self,"nearby_action_buttons",{}).get(code)
        if btn and btn.winfo_exists():btn.configure(text="Ajouter")
        self._refresh_market_scope()

    def _load_market_cities(self,dept):
        # Reuse the same official geo.api.gouv.fr city loader as Formations.
        self._load_training_cities(dept)
        def sync():
            try:self.market_city_cb["values"]=sorted(self.offer_cities_by_name.keys())
            except Exception:pass
        self.after(700,sync)

    def _market_intro(self):
        if not hasattr(self,"market_results"):return
        for w in self.market_results.winfo_children():w.destroy()
        b=ctk.CTkFrame(self.market_results,fg_color="#F6F7FC",corner_radius=16);b.pack(fill="x",pady=6)
        tk.Label(b,text="Tableau de bord France Travail",bg="#F6F7FC",fg=NAVY,font=("Segoe UI",12,"bold")).pack(anchor="w",padx=18,pady=(15,6))
        tk.Label(b,text="L’analyse utilise le métier ROME et le territoire sélectionnés. Les données ne sont jamais simulées.",
                 bg="#F6F7FC",fg=TEXT,font=("Segoe UI",9),wraplength=820,justify="left").pack(anchor="w",padx=18,pady=(0,5))
        tk.Label(b,text="Cliquez sur « Analyser le marché » pour interroger les indicateurs disponibles.",
                 bg="#F6F7FC",fg=MUTED,font=("Segoe UI",8)).pack(anchor="w",padx=18,pady=(0,15))

    def _market_geo(self):
        city=self.offer_cities_by_name.get(self.market_city_var.get().strip(),{})
        if city.get("code"):
            return "COM",str(city["code"]),self.market_city_var.get().strip()
        dept=self.offer_depts_by_name.get(self.market_dept_var.get().strip(),{})
        if dept.get("code"):
            return "DEP",str(dept["code"]),self.market_dept_var.get().strip()
        reg=self.offer_regions_by_name.get(self.market_region_var.get().strip())
        if reg:
            return "REG",str(reg),self.market_region_var.get().strip()
        return "","", ""

    def _market_extract(self,data):
        if not isinstance(data,dict):return {"rows":[],"period":"","territory":"","label":""}
        raw=data.get("listeValeursParPeriode") or []
        rows=[]
        for row in raw if isinstance(raw,list) else []:
            if not isinstance(row,dict):continue
            value=None
            value_type=""
            for key,kind in (("valeurPrincipaleNombre","nombre"),("valeurPrincipaleMontant","montant"),
                             ("valeurPrincipaleTaux","taux"),("valeurPrincipaleRang","rang")):
                if row.get(key) not in (None,""):
                    value=row.get(key);value_type=kind;break
            rows.append({
                "value":value,"value_type":value_type,
                "value_name":str(row.get("valeurPrincipaleNom") or ""),
                "secondary":row.get("valeurSecondaireNombre"),
                "secondary_pct":row.get("valeurSecondairePourcentage"),
                "nomenclature":str(row.get("libNomenclature") or row.get("codeNomenclature") or ""),
                "code_nomenclature":str(row.get("codeNomenclature") or ""),
                "period":str(row.get("libPeriode") or row.get("codePeriode") or ""),
                "code_period":str(row.get("codePeriode") or ""),
                "territory":str(row.get("libTerritoire") or data.get("libTerritoire") or ""),
                "activity":str(row.get("libActivite") or "")
            })
        return {"rows":rows,"period":rows[0]["period"] if rows else "",
                "territory":rows[0]["territory"] if rows else str(data.get("libTerritoire") or ""),
                "label":str(data.get("libIndicateur") or "")}

    def _market_card(self,title,result,note=""):
        box=ctk.CTkFrame(self.market_results,fg_color="#FFFFFF",corner_radius=16,border_width=1,border_color=LINE)
        box.pack(fill="x",pady=6)
        tk.Label(box,text=title,bg="#FFFFFF",fg=NAVY,font=("Segoe UI",11,"bold")).pack(anchor="w",padx=18,pady=(13,5))
        if isinstance(result,Exception):
            tk.Label(box,text="Donnée indisponible",bg="#FFFFFF",fg=WARN,font=("Segoe UI",13,"bold")).pack(anchor="w",padx=18)
            detail=str(result)
        else:
            rows=result.get("rows") or []
            if rows:
                # Keep the most recent period returned first by the API and show every nomenclature for it.
                codep=rows[0].get("code_period","")
                current=[r for r in rows if not codep or r.get("code_period")==codep]
                for r in current:
                    val=r.get("value")
                    shown=f"{val:,.0f}".replace(","," ") if isinstance(val,(int,float)) else "—"
                    line=tk.Frame(box,bg="#FFFFFF");line.pack(fill="x",padx=18,pady=2)
                    tk.Label(line,text=shown,bg="#FFFFFF",fg=TEXT,font=("Segoe UI",14,"bold"),width=10,anchor="w").pack(side="left")
                    label=r.get("nomenclature") or r.get("value_name") or "Valeur"
                    tk.Label(line,text=label,bg="#FFFFFF",fg=TEXT,font=("Segoe UI",8),anchor="w",wraplength=650,justify="left").pack(side="left",fill="x",expand=True)
                meta=[x for x in [current[0].get("period",""),current[0].get("territory","")] if x]
                detail=" • ".join(meta)
            else:
                tk.Label(box,text="Aucune valeur retournée",bg="#FFFFFF",fg=MUTED,font=("Segoe UI",10,"bold")).pack(anchor="w",padx=18)
                detail=""
        if detail:
            tk.Label(box,text=detail,bg="#FFFFFF",fg=MUTED,font=("Segoe UI",8),wraplength=820,justify="left").pack(anchor="w",padx=18,pady=(5,2))
        if note:
            tk.Label(box,text=note,bg="#FFFFFF",fg=MUTED,font=("Segoe UI",8),wraplength=820,justify="left").pack(anchor="w",padx=18,pady=(2,2))
        tk.Label(box,text="Source : France Travail — API Marché du travail",bg="#FFFFFF",fg=MUTED,font=("Segoe UI",8)).pack(anchor="w",padx=18,pady=(3,12))

    def search_market(self):
        j=self._active_market_job();code=(j.get("code") or "").strip().upper()
        if not code:
            self.market_status.config(text="Sélectionnez d’abord un métier ROME.",fg=WARN);return
        typ,territory,territory_label=self._market_geo()
        if not territory:
            self.market_status.config(text="Sélectionnez une région, un département ou une ville.",fg=WARN);return
        for w in self.market_results.winfo_children():w.destroy()
        self.market_status.config(text="Interrogation des statistiques France Travail…",fg=MUTED)

        def worker():
            try:
                cfg=load_cfg();cid=(cfg.get("client_id") or "").strip();secret=(cfg.get("client_secret") or "").strip()
                if not cid or not secret:raise RuntimeError("Identifiants API manquants dans Connexion API.")
                tok=token(cid,secret,MARKET_SCOPE)
                base={"codeTypeTerritoire":typ,"codeTerritoire":territory,
                      "codeTypeActivite":"ROME","codeActivite":code,"codeTypePeriode":"TRIMESTRE"}
                endpoints=[
                    ("Demandeurs d’emploi",MARKET_BASE+"/v1/indicateur/stat-demandeurs","CATCAND"),
                    ("Offres d’emploi",MARKET_BASE+"/v1/indicateur/stat-offres","ORIGINEOFF"),
                    ("Embauches",MARKET_BASE+"/v1/indicateur/stat-embauches","CATCANDxDUREEEMP")]
                results=[]
                for title,url,nom in endpoints:
                    payload=dict(base);payload["codeTypeNomenclature"]=nom
                    try:results.append((title,self._market_extract(post_json(url,tok,payload))))
                    except Exception as ex:results.append((title,ex))

                # Official ROME -> FAP reference.
                fap=""
                try:
                    ref=get_json(MARKET_BASE+"/v1/referentiel/rechercherActivitesRomeFap?"+urllib.parse.urlencode({"codeRome":code}),tok)
                    pairs=ref.get("romeFapList") or []
                    if pairs:fap=str(pairs[0].get("codeFap") or "").strip()
                except Exception:pass

                tension=RuntimeError("Aucune correspondance FAP retournée pour ce ROME.")
                if fap:
                    # PERSP_2 works with FAP and TYPE_TENSION. The same territory is retained.
                    pp={"codeTypeTerritoire":typ,"codeTerritoire":territory,
                        "codeTypeActivite":"FAP","codeActivite":fap,
                        "codeTypePeriode":"ANNEE","codeTypeNomenclature":"TYPE_TENSION"}
                    try:tension=self._market_extract(post_json(MARKET_BASE+"/v1/indicateur/stat-perspective-employeur",tok,pp))
                    except Exception as ex:tension=ex

                # SAL_3: territory is in the path, ROME in query string.
                salary=None
                try:
                    su=MARKET_BASE+"/v1/indicateur/salaire-rome-fap/"+urllib.parse.quote(typ)+"/"+urllib.parse.quote(territory)
                    su+="?"+urllib.parse.urlencode({"codeRome":code})
                    salary=self._market_extract(get_json(su,tok))
                except Exception as ex:salary=ex

                self.after(0,lambda:self._render_market_live(results,territory_label,tension,salary,fap))
            except Exception as ex:
                self.after(0,lambda err=str(ex):self.market_status.config(text="Analyse impossible : "+err,fg=BAD))
        threading.Thread(target=worker,daemon=True).start()

    def _render_market_live(self,results,territory_label,tension=None,salary=None,fap=""):
        for w in self.market_results.winfo_children():w.destroy()
        for title,result in results:self._market_card(title,result)
        note=("Correspondance officielle ROME → FAP : "+fap) if fap else "Correspondance ROME → FAP non disponible."
        self._market_card("Difficulté de recrutement",tension,note)
        self._market_card("Salaires",salary,"Montants et typologies affichés tels que retournés par France Travail.")
        ok=sum(1 for _,r in results if not isinstance(r,Exception))
        if tension is not None and not isinstance(tension,Exception):ok+=1
        if salary is not None and not isinstance(salary,Exception):ok+=1
        self.market_status.config(text=f"{ok}/5 indicateur(s) reçu(s) — {territory_label}.",fg=GOOD if ok else WARN)
        if hasattr(self,"market_bind_wheel"):self.after(50,self.market_bind_wheel)

    def plan_action_page(self):
        p=self.pages["Plan d’action"]
        self.heading(p,"Plan d’action","Synthèse personnalisée du CV, des compétences et des métiers explorés.")

        self.plan_canvas=tk.Canvas(p,bg=BG,highlightthickness=0)
        sb=ttk.Scrollbar(p,orient="vertical",command=self.plan_canvas.yview)
        self.plan_zone=tk.Frame(self.plan_canvas,bg=BG)
        self.plan_zone.bind("<Configure>",lambda e:self.plan_canvas.configure(scrollregion=self.plan_canvas.bbox("all")))
        win=self.plan_canvas.create_window((0,0),window=self.plan_zone,anchor="nw")
        self.plan_canvas.bind("<Configure>",lambda e:self.plan_canvas.itemconfigure(win,width=e.width))
        self.plan_canvas.configure(yscrollcommand=sb.set)
        self.plan_canvas.pack(side="left",fill="both",expand=True,padx=(0,2))
        self.after(100, lambda: self._bind_slow_wheel(getattr(self,"plan_inner",self.plan_canvas), self.plan_canvas, "plan"))
        sb.pack(side="right",fill="y")

        # Local wheel binding only: do not capture the wheel in Compétences & métiers.
        self.plan_canvas.bind("<Enter>",lambda e:self.plan_canvas.bind("<MouseWheel>",self._plan_wheel))
        self.plan_canvas.bind("<Leave>",lambda e:self.plan_canvas.unbind_all("<MouseWheel>"))
        self.refresh_plan_action()

    def _plan_wheel(self,event):
        try:
            delta=getattr(event,"delta",0)
            if delta:
                self.plan_canvas.yview_scroll(-1 if delta>0 else 1,"units")
                return "break"
        except Exception:
            pass
        return None
    def _plan_cv_priorities(self):
        if not self.last_diag:return []
        score,rows=self.last_diag
        cvtxt=str(getattr(self,"cv_text","") or getattr(self,"extracted_text","") or "")
        cvlines=[re.sub(r"\s+"," ",x).strip() for x in cvtxt.splitlines() if re.sub(r"\s+"," ",x).strip()]
        target=self.get_offer_rome() if hasattr(self,"get_offer_rome") else {}
        code=str(target.get("code") or "").strip().upper()
        target_label=str(target.get("libelle") or target.get("label") or "").strip()

        def norm(x):
            x=str(x or "").lower()
            x=re.sub(r"[^a-zà-ÿ0-9 ]+"," ",x)
            return set(w for w in x.split() if len(w)>=4)

        cvwords=norm(cvtxt)

        # Build the actual ROME expectations for the selected profession from the fiche already used by the app.
        expectations=[]
        if code:
            try:
                fiche=self._get_rome_fiche(code) or {}
                for g in fiche.get("groupesCompetencesMobilisees",[]) or []:
                    for c in g.get("competences",[]) or []:
                        lib=str(c.get("libelle") or "").strip()
                        if lib:expectations.append(("Compétence",lib))
                for g in fiche.get("groupesSavoirs",[]) or []:
                    for c in g.get("savoirs",[]) or []:
                        lib=str(c.get("libelle") or "").strip()
                        if lib:expectations.append(("Savoir",lib))
            except Exception:
                pass

        def best_cv_line(label):
            lw=norm(label)
            best="",0
            for line in cvlines:
                sw=norm(line)
                n=len(lw & sw)
                if n>best[1] and 4<len(line)<220:best=(line,n)
            return best if isinstance(best,tuple) else ("",0)

        priorities=[]
        used=set()

        # First priority pool: ROME expectations that are present but weakly expressed in the CV,
        # or important expectations not identifiable in the CV. No competence is attributed without evidence.
        for typ,lib in expectations:
            if lib.lower() in used:continue
            used.add(lib.lower())
            line,overlap=best_cv_line(lib)
            words=norm(lib)
            direct=len(words & cvwords)
            if line and (overlap>=2 or direct>=2):
                priorities.append({
                    "rank":90+min(overlap,5),
                    "title":"Mieux valoriser une compétence utile au métier visé",
                    "detail":"Une correspondance est identifiable entre le CV et une attente ROME de "+(target_label or "ce métier")+".",
                    "why":"Cette compétence est pertinente pour le métier visé mais elle peut être rendue plus explicite pour le recruteur.",
                    "todo":"Reformuler l’élément déjà présent en précisant l’action réellement réalisée et son contexte.",
                    "example":"Dans votre CV : « "+line+" »\nAttente ROME rapprochée : « "+lib+" »\nProposition : conserver les faits du CV et préciser comment cette activité démontre « "+lib+" ».\nÀ confirmer avec le candidat avant toute reformulation.",
                    "rome":lib
                })
            else:
                priorities.append({
                    "rank":65,
                    "title":typ+" ROME à vérifier avec le candidat",
                    "detail":"« "+lib+" » fait partie des éléments associés au métier visé, mais n’est pas suffisamment identifiable dans le CV analysé.",
                    "why":"L’absence dans le CV ne signifie pas que le candidat ne maîtrise pas cette compétence.",
                    "todo":"Demander au candidat s’il a déjà mobilisé cette compétence dans une expérience, une formation ou une activité. Si oui, l’illustrer par une situation réelle ; sinon, ne pas l’ajouter.",
                    "example":"À vérifier avec le candidat : « "+lib+" ».\nAucune formulation ne doit être ajoutée au CV sans exemple réel permettant de la justifier.",
                    "rome":lib
                })
            if len(priorities)>=10:break

        # Fundamental CV issues compete with the ROME-specific priorities instead of automatically occupying the top four.
        for x in rows:
            if x[3].startswith("✓") or x[3].startswith("—"):continue
            title=str(x[0]); detail=str(x[5] or "")
            low=title.lower()
            severity=max(0,int(x[2])-int(x[1]))
            rank=55+severity
            if "titre" in low or "objectif" in low:
                rank+=25
                todo="Faire apparaître clairement le métier visé"+(" : "+target_label if target_label else "")+"."
                ex=("Proposition de titre : « "+target_label+" »") if target_label else "Préciser l’intitulé exact du métier visé."
                why="Le recruteur doit comprendre immédiatement le poste recherché."
            elif "date" in low or "coh" in low:
                todo="Harmoniser les dates sans modifier les périodes réelles."
                ex="Utiliser partout un même format, par exemple « MM/AAAA – MM/AAAA »."
                why="Une chronologie homogène facilite la compréhension du parcours."
            elif "coord" in low:
                todo="Vérifier téléphone, e-mail professionnel et ville."
                ex="Téléphone • e-mail professionnel • ville."
                why="Le recruteur doit pouvoir contacter facilement le candidat."
            elif "lisib" in low or "structure" in low or "ats" in low:
                todo="Clarifier les rubriques et conserver une mise en page simple."
                ex="Profil • Expériences professionnelles • Compétences • Formation."
                why="Une structure claire facilite la lecture humaine et le traitement du CV."
            else:
                # Generic diagnostic issues stay useful, but below strong ROME/CV evidence.
                todo=detail or "Reprendre cette rubrique en fonction du métier visé."
                ex="À adapter uniquement à partir des informations réellement présentes dans le CV."
                why="Ce point a été identifié dans le diagnostic du CV."
            priorities.append({"rank":rank,"title":title,"detail":detail,"why":why,"todo":todo,"example":ex,"rome":""})

        priorities.sort(key=lambda x:x.get("rank",0),reverse=True)

        # Diversify the final 4: avoid returning four missing ROME skills when stronger CV issues exist.
        final=[]; missing_count=0
        for x in priorities:
            missing=("à vérifier avec le candidat" in x["title"].lower())
            if missing and missing_count>=2:continue
            final.append(x)
            if missing:missing_count+=1
            if len(final)>=3:break
        return final

    def _plan_nearby_jobs(self):
        _cv=self._plan_cv_mode_nearby()
        if _cv is not None:return _cv
        job=self.get_offer_rome()

        # Exploration du profil : aucun métier ROME n'a été sélectionné.
        if not str(job.get("code") or "").strip():
            prof=self._cv_profile_competences()
            transfers=self._cv_transferables()
            nearby=self._cv_exploration_jobs()
            tab=str(getattr(self,"skill_tab","Vue d’ensemble") or "Vue d’ensemble")

            if tab=="Vue d’ensemble":
                title="Compétences reconnues dans le CV"
                ctk.CTkLabel(self.skills_content,text=title,text_color=NAVY,font=("Segoe UI",18,"bold"),
                             anchor="w").pack(fill="x",padx=20,pady=(18,5))
                ctk.CTkLabel(self.skills_content,text="Exploration du profil sans métier visé : seules les compétences identifiables dans le CV sont affichées.",
                             text_color=MUTED,font=("Segoe UI",10),anchor="w",justify="left",wraplength=820).pack(fill="x",padx=20,pady=(0,12))
                for typ in ("Savoir-faire","Savoirs","Savoir-être"):
                    vals=prof.get(typ,[])
                    ctk.CTkLabel(self.skills_content,text=typ,text_color=NAVY,font=("Segoe UI",12,"bold"),anchor="w").pack(fill="x",padx=20,pady=(8,3))
                    if vals:
                        ctk.CTkLabel(self.skills_content,text=" • ".join(x["libelle"] for x in vals),text_color=TEXT,
                                     font=("Segoe UI",10),anchor="w",justify="left",wraplength=820).pack(fill="x",padx=20,pady=(0,5))
                    else:
                        ctk.CTkLabel(self.skills_content,text="Aucun élément suffisamment explicite repéré dans le CV.",
                                     text_color=MUTED,font=("Segoe UI",9),anchor="w").pack(fill="x",padx=20,pady=(0,5))
                return

            if tab in ("Savoir-faire","Savoirs","Savoir-être"):
                ctk.CTkLabel(self.skills_content,text=tab,text_color=NAVY,font=("Segoe UI",18,"bold"),anchor="w").pack(fill="x",padx=20,pady=(18,5))
                vals=prof.get(tab,[])
                if vals:
                    for x in vals:
                        self._skill_row(x["libelle"],"✓ Identifiée dans le CV")
                else:
                    ctk.CTkLabel(self.skills_content,text="Aucune compétence de cette catégorie n’est suffisamment explicite dans le CV.",
                                 text_color=MUTED,font=("Segoe UI",10),anchor="w").pack(fill="x",padx=20,pady=15)
                return

            if tab=="Compétences transférables":
                ctk.CTkLabel(self.skills_content,text="Compétences transférables",text_color=NAVY,font=("Segoe UI",18,"bold"),anchor="w").pack(fill="x",padx=20,pady=(18,5))
                ctk.CTkLabel(self.skills_content,text="Compétences identifiées dans le CV pouvant être mobilisées dans différents contextes professionnels.",
                             text_color=MUTED,font=("Segoe UI",10),anchor="w",justify="left",wraplength=820).pack(fill="x",padx=20,pady=(0,10))
                for x in transfers:
                    self._skill_row(x["libelle"],"✓ Identifiée dans le CV • "+x["type"])
                if not transfers:
                    ctk.CTkLabel(self.skills_content,text="Aucune compétence transférable suffisamment explicite n’a été repérée.",
                                 text_color=MUTED,font=("Segoe UI",10),anchor="w").pack(fill="x",padx=20,pady=15)
                return

            if tab=="Métiers proches":
                ctk.CTkLabel(self.skills_content,text="Métiers à explorer à partir de votre CV",text_color=NAVY,font=("Segoe UI",18,"bold"),anchor="w").pack(fill="x",padx=20,pady=(18,5))
                ctk.CTkLabel(self.skills_content,text="Ces pistes sont proposées à partir des compétences reconnues dans le CV. Elles servent à explorer des possibilités et ne constituent pas une validation d’aptitude au métier.",
                             text_color=MUTED,font=("Segoe UI",10),anchor="w",justify="left",wraplength=820).pack(fill="x",padx=20,pady=(0,12))
                for j in nearby:
                    block=ctk.CTkFrame(self.skills_content,fg_color="#FAFAFD",corner_radius=12,border_width=1,border_color=LINE)
                    block.pack(fill="x",padx=20,pady=6)
                    ctk.CTkLabel(block,text=j["libelle"]+" • ROME "+j["code"],text_color=NAVY,font=("Segoe UI",11,"bold"),anchor="w").pack(fill="x",padx=14,pady=(10,3))
                    common=" • ".join(x["libelle"] for x in j.get("common",[]))
                    ctk.CTkLabel(block,text="Compétences communes : "+common,text_color="#16803A",font=("Segoe UI",9),anchor="w",justify="left",wraplength=790).pack(fill="x",padx=14,pady=(0,6))
                    actions=ctk.CTkFrame(block,fg_color="transparent");actions.pack(fill="x",padx=14,pady=(0,10))
                    ctk.CTkButton(actions,text="Voir MétierScope",height=31,corner_radius=9,fg_color=NAVY,hover_color="#202965",
                                  command=lambda c=j["code"],l=j["libelle"]:self._open_metierscope(c,l)).pack(side="left",padx=(0,8))
                    ctk.CTkButton(actions,text="Ajouter",height=31,corner_radius=9,fg_color="#FFFFFF",text_color=NAVY,border_width=1,border_color="#2F6FED",
                                  command=lambda jj=j:self._add_explored_job(jj)).pack(side="left")
                if not nearby:
                    ctk.CTkLabel(self.skills_content,text="Le CV ne contient pas encore assez d’éléments explicites pour proposer des métiers proches.",
                                 text_color=MUTED,font=("Segoe UI",10),anchor="w").pack(fill="x",padx=20,pady=15)
                return
        code=str(job.get("code") or "").upper()
        if code and code not in self.rome_nearby_cache and code not in self.rome_nearby_loading:
            self.after(30,lambda c=code:self._fetch_nearby_jobs(c))
        rows=self._nearby_from_rome_fiche(code) if code else []
        return list(rows)[:4]

    def _training_suggestions_for_bridge(self,job_label,missing):
        job=str(job_label or "").strip()
        skills=[str(x or "").strip() for x in (missing or []) if str(x or "").strip()]
        out=[]
        jl=job.lower()
        # Prefer recognizable training themes when the ROME target makes the domain clear.
        if any(k in jl for k in ("création d'entreprise","creation d'entreprise","entreprene","reprise d'entreprise")):
            out += ["Accompagnement à la création et à la reprise d’entreprise",
                    "Conseiller en création ou reprise d’entreprise"]
        elif any(k in jl for k in ("recrut","ressources humaines","rh")):
            out += ["Techniques de recrutement et conduite d’entretien",
                    "Sourcing et recherche de candidats"]
        elif any(k in jl for k in ("insertion","emploi","orientation professionnelle")):
            out += ["Accompagnement des parcours professionnels",
                    "Techniques d’entretien et d’accompagnement professionnel"]
        elif any(k in jl for k in ("commercial","vente","relation client")):
            out += ["Techniques de vente et relation client",
                    "Développement commercial et prospection"]
        elif any(k in jl for k in ("management","manager","responsable d'équipe","responsable d’équipe")):
            out += ["Management d’équipe",
                    "Animation et pilotage d’une équipe"]

        # Concrete training themes for the CV-only exploration professions.
        if "assistanat" in jl or "assistant" in jl:
            out += ["Titre professionnel Assistant de direction",
                    "Bureautique et outils collaboratifs"]
        elif "médiation" in jl or "mediation" in jl:
            out += ["Titre professionnel Médiateur social accès aux droits et services",
                    "Techniques de médiation et gestion des situations difficiles"]
        elif "formation professionnelle" in jl or "formateur" in jl:
            out += ["Titre professionnel Formateur professionnel d’adultes",
                    "Conception et animation d’une action de formation"]
        elif "insertion professionnelle" in jl:
            out += ["Titre professionnel Conseiller en insertion professionnelle",
                    "Accompagnement des parcours professionnels"]
        elif "ressources humaines" in jl:
            out += ["Titre professionnel Assistant ressources humaines",
                    "Techniques de recrutement et conduite d’entretien"]

        # Complete with the actual ROME gaps, phrased as search themes rather than invented certifications.
        for skill in skills[:3]:
            candidate="Développer la compétence : "+skill
            if candidate.lower() not in {x.lower() for x in out}:out.append(candidate)

        # Keep the display simple and remove duplicates.
        clean=[]
        for x in out:
            if x and x.lower() not in {y.lower() for y in clean}:clean.append(x)
        return clean[:3]

    def _plan_bridges(self):
        if not (getattr(self,"selected_job",None) or {}).get("code"):
            prof=self._cv_profile_competences()
            have={x["libelle"].lower() for arr in prof.values() for x in arr}
            seeds={
                "K1801":["Accompagnement individuel","Conduite d’entretien","Animation d’ateliers","Insertion professionnelle","Relation entreprises"],
                "M1502":["Conduite d’entretien","Recrutement","Relation entreprises","Communication"],
                "K2111":["Animation d’ateliers","Accompagnement individuel","Formation professionnelle","Communication"],
                "M1704":["Relation entreprises","Conseil","Communication","Organisation"],
                "M1604":["Suivi administratif","Organisation","Outils bureautiques","Communication"],
                "K1205":["Accueil et information du public","Accompagnement individuel","Écoute","Communication"],
                "D1402":["Prospection","Relation entreprises","Conseil","Communication"],
            }
            selected=self._plan_selected_jobs()
            selected_codes={j.get("code") for j in selected}
            # Always include selected professions first, then complementary close professions.
            pool=list(selected)
            for j in self._cv_exploration_jobs():
                if j.get("code") not in selected_codes:
                    pool.append({"code":j.get("code",""),"libelle":j.get("libelle","")})
            out=[]
            for j in pool:
                code=str(j.get("code") or "")
                req=seeds.get(code,[])
                common=[x for x in req if x.lower() in have]
                missing=[x for x in req if x.lower() not in have]
                # Keep selected jobs even when no gap is detected; complementary jobs
                # are useful only when they show a development path.
                if code in selected_codes or (common and missing):
                    suggestions=self._training_suggestions_for_bridge(j.get("libelle",""),missing)
                    if not suggestions:
                        suggestions=["Formation ou professionnalisation liée au métier : "+str(j.get("libelle",""))]
                    out.append({"code":code,"libelle":j.get("libelle",""),
                                "common":common[:4],"missing":missing[:3],
                                "training_suggestions":suggestions[:3],
                                "selected":code in selected_codes})
                if len(out)>=6:break
            return out
        source=self.get_offer_rome()
        source_code=str(source.get("code") or "").strip().upper()
        if not source_code:return []
        if source_code not in self.rome_nearby_cache:
            if source_code not in self.rome_nearby_loading:
                self.after(30,lambda c=source_code:self._fetch_nearby_jobs(c))
            return []

        candidates=list(self._nearby_from_rome_fiche(source_code) or [])
        out=[]
        for job in candidates[:12]:
            code=str(job.get("code") or "").strip().upper()
            if not code or code==source_code:continue

            common_objs=[x for x in job.get("common",[]) if isinstance(x,dict)]
            common=[str(x.get("libelle") or "").strip() for x in common_objs if x.get("libelle")]
            common_codes={str(x.get("code") or "").strip() for x in common_objs if x.get("code")}
            target=[x for x in job.get("target_competences",[]) if isinstance(x,dict)]

            missing=[]
            seen=set()
            for comp in target:
                ccode=str(comp.get("code") or "").strip()
                lib=str(comp.get("libelle") or "").strip()
                if not lib or (ccode and ccode in common_codes):continue
                key=(ccode or lib.lower())
                if key in seen:continue
                seen.add(key);missing.append(lib)

            # A bridge needs at least one demonstrated point of support and one skill to develop.
            if common and missing:
                label=str(job.get("libelle") or "")
                out.append({"code":code,"libelle":label,
                            "common":common[:5],"missing":missing[:4],
                            "training_suggestions":self._training_suggestions_for_bridge(label,missing[:4]),
                            "common_count":len(common_codes)})
            if len(out)>=3:break
        return out

    def _plan_transferables(self):
        job=self.get_offer_rome();code=str(job.get("code") or "").upper()
        if not code:return []
        lists=self._transfer_lists(code)
        out=[]
        labels={"knowhow":"Savoir-faire","knowledge":"Savoir","soft":"Savoir-être"}
        for sec in ("knowhow","knowledge","soft"):
            for item,detail in lists.get(sec,[]):
                out.append({"title":item.get("libelle",""),"type":labels[sec],"detail":detail})
        return out[:4]

    def _plan_card(self,title,subtitle=None):
        c=self.rounded_frame(self.plan_zone,CARD,LINE,RADIUS_CARD,30,6)
        tk.Label(c,text=title,bg=CARD,fg=NAVY,font=("Segoe UI",13,"bold")).pack(anchor="w",padx=20,pady=(15,3))
        if subtitle:
            tk.Label(c,text=subtitle,bg=CARD,fg=MUTED,font=("Segoe UI",9),
                     wraplength=850,justify="left").pack(anchor="w",padx=20,pady=(0,10))
        return c

    def refresh_plan_action(self):
        if not hasattr(self,"plan_zone"):return
        for w in self.plan_zone.winfo_children():w.destroy()
        _top_actions=ctk.CTkFrame(self.plan_zone,fg_color="transparent")
        _top_actions.pack(fill="x",padx=6,pady=(2,10))
        ctk.CTkButton(_top_actions,text="Générer le plan",height=36,width=145,corner_radius=10,
                      fg_color=NAVY,command=self.export_plan_pdf).pack(side="right")

        # Jobs included in this plan. Multi-selection is independent from the other modules.
        _plan_jobs=self._plan_job_choices()
        if _plan_jobs:
            selbox=ctk.CTkFrame(self.plan_zone,fg_color="#FFFFFF",corner_radius=16,border_width=1,border_color=LINE)
            selbox.pack(fill="x",padx=6,pady=(4,12))
            ctk.CTkLabel(selbox,text="Métiers à intégrer au plan d’action",text_color=NAVY,
                         font=("Segoe UI",13,"bold"),anchor="w").pack(fill="x",padx=16,pady=(12,3))
            ctk.CTkLabel(selbox,text="Sélectionnez un ou plusieurs métiers parmi ceux que vous avez ajoutés.",
                         text_color=MUTED,font=("Segoe UI",9),anchor="w").pack(fill="x",padx=16,pady=(0,8))
            wrap=ctk.CTkFrame(selbox,fg_color="transparent");wrap.pack(fill="x",padx=12,pady=(0,12))
            for _j in _plan_jobs:
                _c=_j["code"]; _on=_c in self.plan_selected_job_codes
                ctk.CTkButton(wrap,text=("✓ " if _on else "")+_j["libelle"]+" • "+_c,
                              height=34,corner_radius=10,fg_color=(NAVY if _on else "#F0F2FA"),
                              text_color=("#FFFFFF" if _on else NAVY),hover_color="#DDE3F6",
                              command=lambda c=_c:self._toggle_plan_job(c)).pack(side="left",padx=4,pady=3)


        cv=self._plan_cv_priorities()
        nearby=self._plan_nearby_jobs()
        _cv_trans=self._plan_cv_mode_transferables()
        if _cv_trans is not None:
            transfers=[{"title":x.get("libelle",""),"type":x.get("type","Compétence"),
                        "detail":"Compétence identifiée dans le CV et mobilisable dans plusieurs contextes."}
                       for x in _cv_trans]
        else:
            transfers=self._plan_transferables()
        bridges=self._plan_bridges()

        c=self._plan_card("🎯 Priorités pour améliorer le CV","Les 3 recommandations à appliquer en priorité.")
        if cv:
            for i,x in enumerate(cv[:3],1):
                accent="#E1000F" if i==1 else "#D97706"
                row=tk.Frame(c,bg="#FAFAFD",highlightbackground=LINE,highlightthickness=1)
                row.pack(fill="x",padx=20,pady=6)
                tk.Label(row,text=f"{i}. {x['title']}",bg="#FAFAFD",fg=NAVY,
                         font=("Segoe UI",10,"bold"),anchor="w",justify="left").pack(fill="x",padx=14,pady=(11,4))
                explanation=x.get("why") or x.get("detail") or "Ce point peut être amélioré pour faciliter la lecture du CV."
                tk.Label(row,text=explanation,bg="#FAFAFD",fg=TEXT,font=("Segoe UI",9),
                         anchor="w",justify="left",wraplength=800).pack(fill="x",padx=14,pady=(0,5))
                tk.Label(row,text="✏ Ma suggestion",bg="#FAFAFD",fg=accent,
                         font=("Segoe UI",9,"bold"),anchor="w").pack(fill="x",padx=14,pady=(3,1))
                suggestion=x.get("todo") or ""
                tk.Label(row,text=suggestion,bg="#FAFAFD",fg=TEXT,font=("Segoe UI",9,"bold"),
                         anchor="w",justify="left",wraplength=800).pack(fill="x",padx=22,pady=(0,10))
        else:
            tk.Label(c,text="Analysez d’abord le CV pour obtenir les recommandations.",
                     bg=CARD,fg=MUTED,font=("Segoe UI",9),anchor="w").pack(fill="x",padx=22,pady=(4,12))
        tk.Frame(c,bg=CARD,height=8).pack()

        c=self._plan_card("💼 Métiers proches de mes compétences","Des métiers qui utilisent plusieurs compétences déjà identifiées dans votre profil.")
        if nearby:
            for j in nearby[:3]:
                block=ctk.CTkFrame(c,fg_color="#FAFAFD",corner_radius=12,border_width=1,border_color=LINE)
                block.pack(fill="x",padx=20,pady=6)
                tk.Label(block,text=f"{j.get('libelle','')} • ROME {j.get('code','')}",bg="#FAFAFD",fg=NAVY,font=("Segoe UI",10,"bold")).pack(anchor="w",padx=14,pady=(11,4))
                common=[str(x.get("libelle") or "") for x in j.get("common",[]) if x.get("libelle")]
                if common:
                    tk.Label(block,text="Compétences utiles : "+" • ".join(common[:5]),bg="#FAFAFD",fg="#16803A",font=("Segoe UI",9),wraplength=800,justify="left").pack(anchor="w",padx=14,pady=(0,8))
                ctk.CTkButton(block,text="Voir le métier sur MétierScope",height=32,corner_radius=10,fg_color=NAVY,hover_color="#202965",
                              command=lambda cde=j.get("code",""),lbl=j.get("libelle",""):self._open_metierscope(cde,lbl)).pack(anchor="w",padx=14,pady=(0,11))
        else:
            tk.Label(c,text="Aucun métier proche disponible pour le moment.",bg=CARD,fg=MUTED,font=("Segoe UI",9)).pack(anchor="w",padx=22,pady=(4,12))
        tk.Frame(c,bg=CARD,height=8).pack()

        c=self._plan_card("🚀 Des métiers accessibles en développant mes compétences",
                          "Des pistes à explorer en renforçant certaines compétences.")
        if bridges:
            for j in bridges:
                common=j.get("common",[])
                missing=j.get("missing",[])
                block=ctk.CTkFrame(c,fg_color="#FAFAFD",corner_radius=12,border_width=1,border_color=LINE)
                block.pack(fill="x",padx=20,pady=7)
                tk.Label(block,text=f"{j.get('libelle','')} • ROME {j.get('code','')}",bg="#FAFAFD",fg=NAVY,font=("Segoe UI",10,"bold")).pack(anchor="w",padx=14,pady=(11,5))
                tk.Label(block,text="✓ Vos atouts",bg="#FAFAFD",fg="#16803A",font=("Segoe UI",9,"bold")).pack(anchor="w",padx=14)
                tk.Label(block,text=" • ".join(common[:4]),bg="#FAFAFD",fg=TEXT,font=("Segoe UI",9),wraplength=800,justify="left").pack(anchor="w",padx=22,pady=(0,5))
                tk.Label(block,text="À développer",bg="#FAFAFD",fg="#D97706",font=("Segoe UI",9,"bold")).pack(anchor="w",padx=14)
                tk.Label(block,text=" • ".join(missing[:3]),bg="#FAFAFD",fg=TEXT,font=("Segoe UI",9),wraplength=800,justify="left").pack(anchor="w",padx=22,pady=(0,5))
                tk.Label(block,text="🎓 Suggestions de formations",bg="#FAFAFD",fg="#6D28D9",font=("Segoe UI",9,"bold")).pack(anchor="w",padx=14)
                suggestions=j.get("training_suggestions") or self._training_suggestions_for_bridge(j.get("libelle",""),missing)
                for suggestion in suggestions[:3]:
                    tk.Label(block,text="• "+suggestion,bg="#FAFAFD",fg=TEXT,font=("Segoe UI",9),
                             wraplength=800,justify="left").pack(anchor="w",padx=22,pady=1)
                tk.Label(block,text="Intitulés suggérés pour orienter la recherche ; disponibilité à vérifier dans le catalogue.",
                         bg="#FAFAFD",fg=MUTED,font=("Segoe UI",8,"italic"),wraplength=800,justify="left").pack(anchor="w",padx=22,pady=(3,6))
                actions=ctk.CTkFrame(block,fg_color="transparent"); actions.pack(fill="x",padx=14,pady=(0,11))
                ctk.CTkButton(actions,text="Rechercher une formation",height=32,corner_radius=10,fg_color="#FFFFFF",text_color=NAVY,border_width=1,border_color="#2F6FED",hover_color="#F3F6FF",
                              command=lambda jj=j:self._open_training_public_search(
                                  (jj.get("training_suggestions") or [jj.get("libelle","")])[0]
                              )).pack(side="left",padx=(0,8))
                ctk.CTkButton(actions,text="Voir le métier",height=32,corner_radius=10,fg_color=NAVY,hover_color="#202965",
                              command=lambda cde=j.get("code",""),lbl=j.get("libelle",""):self._open_metierscope(cde,lbl)).pack(side="left")
        else:
            _pj=self.get_offer_rome()
            _pc=str(_pj.get("code") or "").strip().upper()
            if _pc and (_pc in self.rome_nearby_loading or _pc not in self.rome_nearby_cache):
                msg="Analyse des passerelles métiers en cours… Les résultats vont s’afficher automatiquement."
            elif _pc:
                msg="Aucune passerelle suffisamment pertinente n’a été identifiée à partir des compétences actuellement repérées."
            else:
                msg="Sélectionnez d’abord un métier visé pour rechercher des passerelles."
            tk.Label(c,text=msg,bg=CARD,fg=MUTED,font=("Segoe UI",9),wraplength=820,justify="left").pack(anchor="w",padx=22,pady=(4,12))
        tk.Frame(c,bg=CARD,height=8).pack()

        c=self._plan_card("🔄 Compétences transférables à valoriser","4 compétences maximum déjà identifiées dans le CV et mobilisables pour le métier analysé.")
        if transfers:
            for i,x in enumerate(transfers,1):
                tk.Label(c,text=f"{i}. {x['title']}",bg=CARD,fg=TEXT,font=("Segoe UI",10,"bold")).pack(anchor="w",padx=22,pady=(4,1))
                tk.Label(c,text=x["type"]+" • "+x["detail"],bg=CARD,fg=MUTED,font=("Segoe UI",9),wraplength=830,justify="left").pack(anchor="w",padx=34,pady=(0,4))
        else:
            tk.Label(c,text="Aucune compétence transférable disponible pour le moment.",bg=CARD,fg=MUTED,font=("Segoe UI",9)).pack(anchor="w",padx=22,pady=(4,12))
        tk.Frame(c,bg=CARD,height=8).pack()

        self.plan_zone.update_idletasks()
        try:self.plan_canvas.configure(scrollregion=self.plan_canvas.bbox("all"))
        except Exception:pass

        bottom=ctk.CTkFrame(self.plan_zone,fg_color="transparent")
        bottom.pack(fill="x",padx=30,pady=(6,24))
        ctk.CTkButton(bottom,text="Générer le plan d’action en PDF",height=44,corner_radius=12,
                      fg_color=NAVY,hover_color="#202965",command=self.export_plan_pdf).pack(side="right")

    def export_plan_pdf(self):
        _pdf_plan_codes=set(getattr(self,"plan_selected_job_codes",[]) or [])
        _pdf_plan_jobs=[j for j in self._jobs_for_downstream_modules() if not _pdf_plan_codes or j.get("code") in _pdf_plan_codes]
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak, KeepTogether, CondPageBreak
            from reportlab.lib.utils import ImageReader
        except Exception:
            messagebox.showerror("PDF","ReportLab n'est pas installé. Relancez le fichier .bat.");return

        path=filedialog.asksaveasfilename(title="Enregistrer le plan d’action",defaultextension=".pdf",
            filetypes=[("Document PDF","*.pdf")],initialfile="Plan_action_Perspectives_Emploi.pdf")
        if not path:return

        cv=self._plan_cv_priorities()[:3]
        nearby=self._plan_nearby_jobs()[:3]
        bridges=self._plan_bridges()[:6]
        _cv_trans=self._plan_cv_mode_transferables()
        if _cv_trans is not None:
            transfers=[{"title":x.get("libelle",""),"type":x.get("type","Compétence"),
                        "detail":"Compétence identifiée dans le CV et mobilisable dans plusieurs contextes."}
                       for x in _cv_trans][:4]
        else:
            transfers=self._plan_transferables()[:4]
        job=(_pdf_plan_jobs[0] if _pdf_plan_jobs else {})
        job_label=str(job.get("libelle") or "").strip()
        job_code=str(job.get("code") or "").strip().upper()

        navy=colors.HexColor("#283276"); blue=colors.HexColor("#008ECF")
        pale=colors.HexColor("#F7F8FC"); line=colors.HexColor("#D9DDEA")
        textc=colors.HexColor("#202642"); muted=colors.HexColor("#66708A")
        green=colors.HexColor("#16803A"); orange=colors.HexColor("#D97706")
        red=colors.HexColor("#E1000F"); purple=colors.HexColor("#6D28D9")

        styles=getSampleStyleSheet()
        ttl=ParagraphStyle("ttl",parent=styles["Normal"],fontName="Helvetica-Bold",fontSize=19,leading=22,textColor=navy)
        intro=ParagraphStyle("intro",parent=styles["Normal"],fontSize=8.5,leading=11,textColor=muted)
        sec=ParagraphStyle("sec",parent=styles["Normal"],fontName="Helvetica-Bold",fontSize=11.5,leading=14,textColor=navy,spaceBefore=7,spaceAfter=5)
        body=ParagraphStyle("body",parent=styles["Normal"],fontSize=8.4,leading=11.2,textColor=textc)
        small=ParagraphStyle("small",parent=body,fontSize=7.7,leading=10,textColor=muted)
        label=ParagraphStyle("label",parent=body,fontName="Helvetica-Bold",textColor=navy)

        doc=SimpleDocTemplate(path,pagesize=A4,leftMargin=32,rightMargin=32,topMargin=25,bottomMargin=28)

        def header():
            logo_flow=Spacer(1,1)
            lp=resource_path("bloc_marque_rf_france_travail.jpg")
            if lp.exists():
                try:
                    iw,ih=ImageReader(str(lp)).getSize()
                    scale=min(145/float(iw),40/float(ih))
                    logo_flow=RLImage(str(lp),width=iw*scale,height=ih*scale)
                except Exception:pass
            left=[Paragraph("Plan d'action personnalisé",ttl),
                  Paragraph("Votre profil, vos compétences, vos opportunités",intro)]
            t=Table([[left,logo_flow]],colWidths=[355,150])
            t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("ALIGN",(1,0),(1,0),"RIGHT"),
                                   ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
                                   ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]))
            return t

        def section_title(n,title,subtitle=""):
            elems=[Paragraph(str(n)+". "+title,sec)]
            if subtitle: elems.append(Paragraph(subtitle,small))
            return elems

        def card(elements,accent=blue):
            t=Table([[elements]],colWidths=[500])
            t.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,-1),pale),("BOX",(0,0),(-1,-1),0.55,line),
                ("LINEBEFORE",(0,0),(0,-1),3,accent),
                ("LEFTPADDING",(0,0),(-1,-1),11),("RIGHTPADDING",(0,0),(-1,-1),10),
                ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)
            ]))
            return t

        story=[header(),Spacer(1,5)]
        if _pdf_plan_jobs:
            _jobs_txt="<br/>".join(str(j.get("libelle",""))+(" - ROME "+str(j.get("code","")) if j.get("code") else "") for j in _pdf_plan_jobs)
            target=Table([[Paragraph("<b>Métiers retenus</b>",small),
                           Paragraph(_jobs_txt,body)]],
                         colWidths=[80,425])
            target.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#EEF4FF")),
                                        ("BOX",(0,0),(-1,-1),0.5,colors.HexColor("#C9D8F3")),
                                        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                                        ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
                                        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
            story += [target,Spacer(1,6)]

        _secno=1
        if cv:
            story += section_title(_secno,"Mes priorités CV","Les trois changements à traiter en premier."); _secno+=1
            for i,x in enumerate(cv,1):
                elems=[Paragraph("<b>"+str(i)+". "+str(x.get("title",""))+"</b>",body)]
                why=str(x.get("why") or x.get("detail") or "").strip()
                todo=str(x.get("todo") or "").strip()
                if why: elems.append(Paragraph(why,small))
                if todo: elems.append(Paragraph("<b>Suggestion :</b> "+todo,body))
                story += [KeepTogether([card(elems,red if i==1 else orange),Spacer(1,4)])]

        if nearby:
            story.append(Spacer(1,10)); story.append(CondPageBreak(90))
            story += section_title(_secno,"Métiers proches de mes compétences","Des métiers qui utilisent plusieurs compétences déjà repérées."); _secno+=1
            for j in nearby:
                common=" • ".join([str(x.get("libelle") or "") for x in j.get("common",[]) if isinstance(x,dict) and x.get("libelle")][:5])
                elems=[Paragraph("<b>"+str(j.get("libelle",""))+"</b>  <font color='#66708A'>ROME "+str(j.get("code",""))+"</font>",body)]
                if common: elems.append(Paragraph("<font color='#16803A'><b>Compétences utiles :</b></font> "+common,small))
                story += [KeepTogether([card(elems,green),Spacer(1,4)])]

        if bridges:
            story.append(Spacer(1,10)); story.append(CondPageBreak(110))
            story += section_title(_secno,"Des métiers accessibles en développant mes compétences",
                                   "Métiers retenus et autres pistes proches : acquis, compétences à développer et formations possibles."); _secno+=1
            for j in bridges:
                common=" • ".join([str(x) for x in j.get("common",[]) if str(x)][:4])
                missing=" • ".join([str(x) for x in j.get("missing",[]) if str(x)][:3])
                suggestions=(j.get("training_suggestions") or self._training_suggestions_for_bridge(j.get("libelle",""),j.get("missing",[])))[:3]
                elems=[Paragraph("<b>"+str(j.get("libelle",""))+"</b>  <font color='#66708A'>ROME "+str(j.get("code",""))+"</font>",body)]
                if common: elems.append(Paragraph("<font color='#16803A'><b>Mes atouts :</b></font> "+common,small))
                if missing: elems.append(Paragraph("<font color='#D97706'><b>À développer :</b></font> "+missing,small))
                if suggestions:
                    elems.append(Paragraph("<font color='#6D28D9'><b>Formations possibles :</b></font>",small))
                    for sug in suggestions: elems.append(Paragraph("• "+str(sug),small))
                story += [KeepTogether([card(elems,purple),Spacer(1,5)])]

        if transfers:
            story.append(Spacer(1,10)); story.append(CondPageBreak(90))
            story += section_title(_secno,"Compétences transférables à valoriser","Des compétences déjà identifiées qui peuvent servir dans plusieurs contextes professionnels."); _secno+=1
            rows=[]
            for x in transfers:
                rows.append([Paragraph("<b>"+str(x.get("title",""))+"</b>",body),
                             Paragraph(str(x.get("type","")),small)])
            t=Table(rows,colWidths=[390,115])
            t.setStyle(TableStyle([("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.white,pale]),
                                   ("BOX",(0,0),(-1,-1),0.5,line),("INNERGRID",(0,0),(-1,-1),0.25,line),
                                   ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
                                   ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
                                   ("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
            story.append(t)

        # Common service block on every generated PDF.
        story.append(Spacer(1,12)); story.append(CondPageBreak(175))
        story += section_title(_secno,"Services utiles pour aller plus loin","Des outils pour poursuivre les démarches en autonomie.")
        services=[
            ("MétierScope","Explorer les métiers, les compétences, les conditions d’accès et les métiers proches.","https://candidat.francetravail.fr/metierscope/"),
            ("France Travail — Formations","Rechercher les formations disponibles selon le métier et le territoire.","https://candidat.francetravail.fr/formations/recherche"),
            ("France Travail — Offres d’emploi","Consulter les offres d’emploi et affiner la recherche par métier, contrat et territoire.","https://candidat.francetravail.fr/offres/recherche"),
            ("La Bonne Boîte","Identifier des entreprises à potentiel d’embauche et préparer des candidatures spontanées.","https://labonneboite.francetravail.fr/"),
            ("Mes événements emploi","Trouver des forums, job datings, ateliers, réunions d’information et rencontres professionnelles.","https://mesevenementsemploi.francetravail.fr/mes"),
            ("CVDesignR","Créer, importer et améliorer un CV avec des modèles et des outils d’aide à la candidature.","https://cvdesignr.com/fr"),
        ]
        svc=[]
        for name,desc,url in services:
            svc += [Paragraph("<b>"+name+"</b>",body),
                    Paragraph(desc,small),
                    Paragraph('<link href="'+url+'" color="#008ECF">'+url+"</link>",small),
                    Spacer(1,4)]
        story += [KeepTogether([card(svc,blue),Spacer(1,5)])]

        def footer(canvas,doc):
            canvas.saveState()
            canvas.setStrokeColor(line);canvas.line(32,20,A4[0]-32,20)
            canvas.setFont("Helvetica",7);canvas.setFillColor(muted)
            canvas.drawString(32,10,"Perspectives Emploi")
            canvas.drawRightString(A4[0]-32,10,"Page "+str(doc.page))
            canvas.restoreState()

        doc.build(story,onFirstPage=footer,onLaterPages=footer)
        messagebox.showinfo("PDF","Plan d'action PDF généré avec succès.")

    def _open_training_public_search(self,label=""):
        q=urllib.parse.quote(str(label or "").strip())
        webbrowser.open("https://candidat.francetravail.fr/formations/recherche?quoi="+q)

    def placeholder(self,n):
        p=self.pages[n];self.heading(p,n,"Module prévu dans la suite de Perspectives Emploi V4.")
        c=self.card(p);tk.Label(c,text="Le module est positionné dans l'interface. Il sera connecté aux données France Travail après validation de V4.2.",bg=CARD,fg=TEXT,font=("Segoe UI",11),wraplength=800,justify="left").pack(anchor="w",padx=22,pady=24)

    def config_api(self):
        cfg=load_cfg();w=tk.Toplevel(self);w.title("Connexion France Travail.io");w.geometry("550x360");w.configure(bg=BG);w.grab_set()
        tk.Label(w,text="Connexion France Travail.io",bg=BG,fg=TEXT,font=("Segoe UI",17,"bold")).pack(anchor="w",padx=25,pady=(14,5))
        c=tk.Frame(w,bg=CARD,highlightbackground=LINE,highlightthickness=1);c.pack(fill="both",expand=True,padx=25,pady=(5,22))
        cid=tk.StringVar(value=cfg.get("client_id",""));sec=tk.StringVar(value=cfg.get("client_secret",""));res=tk.StringVar()
        for lab,var,mask in [("Client ID",cid,False),("Client Secret",sec,True)]:
            tk.Label(c,text=lab,bg=CARD,fg=TEXT,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=20,pady=(15,4))
            ttk.Entry(c,textvariable=var,show="•" if mask else "").pack(fill="x",padx=20,ipady=5)
        tk.Label(c,textvariable=res,bg=CARD,fg=GOOD,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=20,pady=10)
        def test():
            try:
                token(cid.get().strip(),sec.get().strip(),ROME_SCOPE)
                token(cid.get().strip(),sec.get().strip(),ROME_FICHE_SCOPE)
                res.set("✓ Connexion API principale : OK")
            except Exception as ex:res.set("✕ Échec");messagebox.showerror("API",str(ex))
        r=tk.Frame(c,bg=CARD);r.pack(fill="x",padx=20,pady=8)
        tk.Button(r,text="Tester",command=test,bg="#008ECF",fg="white",relief="flat",padx=15,pady=8).pack(side="left")
        def save():
            if cid.get().strip() and sec.get().strip():save_cfg(cid.get().strip(),sec.get().strip());w.destroy();self.status.set("Connexion API enregistrée")
        tk.Button(r,text="Enregistrer sur ce PC",command=save,bg=NAVY,fg="white",relief="flat",padx=15,pady=8).pack(side="left",padx=8)

if __name__=="__main__":App().mainloop()
