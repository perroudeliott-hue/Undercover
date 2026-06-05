import streamlit as st
import random
from supabase import create_client, Client
from streamlit_autorefresh import st_autorefresh
from collections import Counter

st.set_page_config(page_title="Undercover", page_icon="🕵️‍♂️", layout="centered", initial_sidebar_state="collapsed")

# --- INJECTION CSS ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 600px; }
    .stButton > button { width: 100%; border-radius: 25px; height: 50px; font-weight: 600; font-size: 16px; border: none; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); transition: all 0.2s ease-in-out; }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15); }
    .stButton > button[kind="primary"] { background-color: #E63946; color: white; }
    .stButton > button[kind="primary"]:hover { background-color: #D62828; }
    .app-title { text-align: center; font-size: 2.5rem; font-weight: 800; margin-bottom: 1rem; color: #E63946; }
    .app-subtitle { text-align: center; font-size: 1.1rem; margin-bottom: 2rem; opacity: 0.8; }
    .card { background-color: rgba(255, 255, 255, 0.05); padding: 1.5rem; border-radius: 15px; margin-bottom: 1rem; }
    .vote-btn button { background-color: #333 !important; color: white !important; border-radius: 10px !important; margin-bottom: 10px; }
    .vote-btn button:hover { background-color: #555 !important; }
    </style>
""", unsafe_allow_html=True)

LISTE_AVATARS = [
    "🕵️‍♂️", "🦊", "👽", "🐙", "🤖", "🐶", "🐱", "🐭", "🐹", "🐰", 
    "🐻", "🐼", "🐨", "🐯", "🦁", "🐮", "🐷", "🐸", "🐵", "🦉", 
    "🦄", "🦖", "🐉", "💩", "👻", "🤡", "👺", "🐧", "🦥", "🦦", "🍄", "🥑"
]

@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_connection()

# --- INITIALISATION ---
if "page" not in st.session_state:
    st.session_state.page = "accueil"
    st.session_state.nom_joueur = ""
    st.session_state.code_salon = ""
    st.session_state.est_createur = False
    st.session_state.afficher_mot = False
    st.session_state.animation_jouee = False
    st.session_state.verrou_action = False
    st.session_state.dernier_statut = ""

    if "pseudo" in st.query_params and "salon" in st.query_params:
        p_url = st.query_params["pseudo"]
        s_url = st.query_params["salon"]
        c_url = st.query_params.get("createur", "false") == "true"
        
        verif = supabase.table("joueurs").select("*").eq("code_salon", s_url).eq("pseudo", p_url).execute().data
        if verif:
            st.session_state.nom_joueur = p_url
            st.session_state.code_salon = s_url
            st.session_state.est_createur = c_url
            statut = supabase.table("salons").select("statut").eq("code_salon", s_url).execute().data
            if statut and statut[0]["statut"] == "attente":
                st.session_state.page = "lobby"
            else:
                st.session_state.page = "jeu"

# --- LOGIQUE ---
def creer_salon(nom, avatar):
    if nom.strip() == "":
        st.error("⚠️ Choisis un pseudo !")
        return
    code = "".join(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(4))
    supabase.table("salons").insert({"code_salon": code, "statut": "attente"}).execute()
    supabase.table("joueurs").insert({"code_salon": code, "pseudo": nom, "avatar": avatar, "est_elimine": False}).execute()
    
    st.session_state.nom_joueur = nom
    st.session_state.code_salon = code
    st.session_state.est_createur = True
    st.session_state.page = "lobby"
    st.query_params["pseudo"] = nom
    st.query_params["salon"] = code
    st.query_params["createur"] = "true"

def rejoindre_salon(nom, code, avatar):
    if nom.strip() == "" or code.strip() == "":
        st.error("⚠️ Remplis ton pseudo ET le code du salon !")
        return
    code = code.upper()
    reponse = supabase.table("salons").select("*").eq("code_salon", code).execute()
    if not reponse.data:
        st.error("❌ Ce salon n'existe pas !")
        return
    supabase.table("joueurs").insert({"code_salon": code, "pseudo": nom, "avatar": avatar, "est_elimine": False}).execute()
    
    st.session_state.nom_joueur = nom
    st.session_state.code_salon = code
    st.session_state.est_createur = False
    st.session_state.page = "lobby"
    st.query_params["pseudo"] = nom
    st.query_params["salon"] = code
    st.query_params["createur"] = "false"

def quitter_salon():
    if st.session_state.nom_joueur and st.session_state.code_salon:
        supabase.table("joueurs").delete().eq("pseudo", st.session_state.nom_joueur).eq("code_salon", st.session_state.code_salon).execute()
    st.query_params.clear()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

def lancer_partie(code, nb_undercover, nb_white):
    joueurs = supabase.table("joueurs").select("*").eq("code_salon", code).execute().data
    mots = supabase.table("mots").select("*").execute().data
    if not mots:
        st.error("⚠️ Aucun mot dans la base !")
        return
    paire = random.choice(mots)
    nb_joueurs = len(joueurs)
    roles = ["Undercover"] * nb_undercover + ["Mr. White"] * nb_white
    while len(roles) < nb_joueurs: roles.append("Civil")
    random.shuffle(roles)
    civils_pseudos = []
    
    for i, joueur in enumerate(joueurs):
        role_attribue = roles[i]
        if role_attribue == "Undercover": mot_attribue = paire["mot_undercover"]
        elif role_attribue == "Mr. White": mot_attribue = "Aucun"
        else:
            mot_attribue = paire["mot_civil"]
            civils_pseudos.append(joueur["pseudo"])
            
        supabase.table("joueurs").update({"role": role_attribue, "mot_attribue": mot_attribue, "est_elimine": False, "vote_contre": None}).eq("id", joueur["id"]).execute()
        
    joueur_qui_commence = random.choice(civils_pseudos) if civils_pseudos else joueurs[0]["pseudo"]
    
    supabase.table("salons").update({"statut": "en_jeu", "premier_joueur": joueur_qui_commence, "vainqueur": None, "cibles_egalite": None}).eq("code_salon", code).execute()
    st.session_state.afficher_mot = False
    st.session_state.animation_jouee = False

def nouveau_tour(code):
    supabase.table("joueurs").update({"vote_contre": None}).eq("code_salon", code).execute()
    supabase.table("salons").update({"statut": "en_jeu", "cibles_egalite": None}).eq("code_salon", code).execute()
    st.session_state.afficher_mot = False

def terminer_manche(code):
    supabase.table("salons").update({"statut": "attente", "premier_joueur": None, "vainqueur": None, "cibles_egalite": None}).eq("code_salon", code).execute()
    supabase.table("joueurs").update({"est_elimine": False, "vote_contre": None}).eq("code_salon", code).execute()
    st.session_state.afficher_mot = False
    st.session_state.animation_jouee = False
    st.session_state.page = "lobby"

def verifier_victoire(joueurs_en_vie):
    roles_en_vie = [j["role"] for j in joueurs_en_vie]
    nb_vivants = len(roles_en_vie)
    if "Undercover" not in roles_en_vie and "Mr. White" not in roles_en_vie: return "Civils"
    elif "Undercover" in roles_en_vie and nb_vivants <= 2: return "Undercover"
    elif "Mr. White" in roles_en_vie and nb_vivants <= 2: return "Mr. White"
    return None


# ==========================================
# ÉCRAN 1 : L'ACCUEIL
# ==========================================
if st.session_state.page == "accueil":
    st.markdown('<div class="app-title">🕵️‍♂️ Undercover</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">Le jeu de bluff entre amis</div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 4])
        with col1: avatar = st.selectbox("Avatar", LISTE_AVATARS, label_visibility="collapsed")
        with col2: pseudo = st.text_input("Ton Pseudo", max_chars=12, placeholder="Ex: Agent 007", label_visibility="collapsed")
            
        st.write("")
        tab1, tab2 = st.tabs(["🆕 Créer", "🤝 Rejoindre"])
        with tab1:
            if st.button("Créer la partie", use_container_width=True, type="primary"):
                creer_salon(pseudo, avatar)
                st.rerun()
        with tab2:
            code_input = st.text_input("🔑 Code du Salon", max_chars=4, placeholder="ABCD")
            if st.button("Entrer dans le salon", use_container_width=True):
                rejoindre_salon(pseudo, code_input, avatar)
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# ÉCRAN 2 : LE LOBBY
# ==========================================
elif st.session_state.page == "lobby":
    st_autorefresh(interval=3000, limit=None, key="lobby_refresh")
    statut_salon = supabase.table("salons").select("statut").eq("code_salon", st.session_state.code_salon).execute().data
    if statut_salon and statut_salon[0]["statut"] != "attente":
        st.session_state.page = "jeu"
        st.rerun()
    
    st.markdown(f'<div class="app-title">Code : {st.session_state.code_salon}</div>', unsafe_allow_html=True)
    with st.container():
        st.subheader("👥 Joueurs connectés :")
        reponse_joueurs = supabase.table("joueurs").select("pseudo, avatar").eq("code_salon", st.session_state.code_salon).execute().data
        nb_joueurs = len(reponse_joueurs)
        for joueur in reponse_joueurs:
            avatar_j = joueur.get('avatar', '⚪')
            if joueur['pseudo'] == st.session_state.nom_joueur:
                st.markdown(f"**{avatar_j} {joueur['pseudo']}** *(Toi)*")
            else:
                st.markdown(f"{avatar_j} {joueur['pseudo']}")
    
    st.write("---")
    if st.session_state.est_createur:
        st.subheader("⚙️ Paramètres")
        col1, col2 = st.columns(2)
        with col1: nb_u = st.number_input("Undercover", min_value=1, max_value=max(1, nb_joueurs-1), value=1)
        with col2: nb_w = st.number_input("Mr. White", min_value=0, max_value=max(0, nb_joueurs-nb_u-1), value=0)
        st.write("")
        if st.button("🚀 Lancer la partie", type="primary", use_container_width=True):
            lancer_partie(st.session_state.code_salon, nb_u, nb_w)
            st.rerun()
    else:
        st.info("⏳ Le créateur configure la partie...")
        
    st.write("---")
    if st.button("🚪 Quitter le salon"):
        quitter_salon()

# ==========================================
# ÉCRAN 3 : LA PHASE DE JEU
# ==========================================
elif st.session_state.page == "jeu":
    st_autorefresh(interval=3000, limit=None, key="jeu_refresh")
    
    salon_info = supabase.table("salons").select("*").eq("code_salon", st.session_state.code_salon).execute().data
    if not salon_info or salon_info[0]["statut"] == "attente":
        st.session_state.page = "lobby"
        st.session_state.afficher_mot = False
        st.rerun()
        
    statut_actuel = salon_info[0]["statut"]
    vainqueur_actuel = salon_info[0].get("vainqueur")

    # GESTION DU VERROU (Évite l'écran blanc)
    if st.session_state.dernier_statut != statut_actuel:
        st.session_state.verrou_action = False
        st.session_state.dernier_statut = statut_actuel
    
    tous_les_joueurs = supabase.table("joueurs").select("*").eq("code_salon", st.session_state.code_salon).execute().data
    mon_profil = next((j for j in tous_les_joueurs if j["pseudo"] == st.session_state.nom_joueur), None)
    joueurs_en_vie = [j for j in tous_les_joueurs if not j["est_elimine"]]
    
    # --- PHASE Z : ÉCRAN DE VICTOIRE ---
    if statut_actuel == "victoire" or vainqueur_actuel:
        if not st.session_state.animation_jouee:
            if vainqueur_actuel == "Civils": st.balloons()
            else: st.snow()
            st.session_state.animation_jouee = True

        st.markdown('<div class="app-title">🏆 Fin de Partie</div>', unsafe_allow_html=True)
        
        if vainqueur_actuel == "Civils": st.success("🎉 **Les Civils ont gagné !** Tous les imposteurs ont été démasqués.")
        elif vainqueur_actuel == "Undercover": st.error("🕵️ **L'Undercover a gagné !** Il s'est fondu dans la masse jusqu'à la fin.")
        elif vainqueur_actuel == "Mr. White": st.warning("👻 **Mr. White a gagné !** Il a survécu sans que personne ne se doute qu'il ne savait rien.")
            
        st.write("---")
        st.subheader("Révélation des rôles :")
        for j in tous_les_joueurs:
            statut_vie = "💀" if j["est_elimine"] else j.get("avatar", "❤️")
            st.write(f"{statut_vie} **{j['pseudo']}** était **{j['role']}** ({j['mot_attribue']})")
            
        if st.session_state.est_createur:
            st.write("---")
            if st.button("Retour au salon", type="primary"):
                terminer_manche(st.session_state.code_salon)
                st.rerun()
        else:
            st.info("⏳ En attente du créateur...")

    # --- PHASE A : DÉBAT ---
    elif statut_actuel == "en_jeu":
        st.markdown('<div class="app-title">🕵️‍♂️ Phase de Débat</div>', unsafe_allow_html=True)
        if salon_info[0].get("premier_joueur"): st.info(f"🗣️ C'est **{salon_info[0]['premier_joueur']}** qui donne le premier mot !")
            
        if mon_profil and not mon_profil["est_elimine"]:
            with st.container():
                st.markdown('<div class="card">', unsafe_allow_html=True)
                if st.button("👁️ Révéler / Masquer mon mot", use_container_width=True):
                    st.session_state.afficher_mot = not st.session_state.afficher_mot
                if st.session_state.afficher_mot:
                    if mon_profil["role"] == "Mr. White":
                        st.success("🤫 **Tu es Mr. White !**")
                        st.caption("Tu n'as pas de mot. Écoute les autres et bluffe !")
                    else: st.success(f"🔑 **Ton mot :** {mon_profil['mot_attribue']}")
                else: st.info("🔒 Mot caché à l'abri des regards")
                st.markdown('</div>', unsafe_allow_html=True)
        elif mon_profil and mon_profil["est_elimine"]:
            st.error("💀 Tu es éliminé, observe le débat en silence !")

        if st.session_state.est_createur:
            st.write("---")
            if st.button("Passer aux votes 🗳️", type="primary"):
                supabase.table("salons").update({"statut": "en_vote"}).eq("code_salon", st.session_state.code_salon).execute()
                st.rerun()

    # --- PHASE B : VOTE ---
    elif statut_actuel == "en_vote":
        st.markdown('<div class="app-title">🗳️ Phase de Vote</div>', unsafe_allow_html=True)
        a_vote = [j for j in joueurs_en_vie if j["vote_contre"] is not None]
        
        # Le verrou garantit que cette logique lourde ne s'exécute qu'une seule fois
        if len(a_vote) == len(joueurs_en_vie) and len(joueurs_en_vie) > 0 and not st.session_state.verrou_action:
            st.session_state.verrou_action = True
            
            votes = [j["vote_contre"] for j in a_vote]
            compte = Counter(votes)
            top_votes = compte.most_common()
            
            if len(top_votes) > 1 and top_votes[0][1] == top_votes[1][1]:
                max_v = top_votes[0][1]
                joueurs_a_egalite = [p for p, v in top_votes if v == max_v]
                cibles_str = ",".join(joueurs_a_egalite)
                supabase.table("joueurs").update({"vote_contre": None}).eq("code_salon", st.session_state.code_salon).execute()
                supabase.table("salons").update({"statut": "en_egalite", "cibles_egalite": cibles_str}).eq("code_salon", st.session_state.code_salon).execute()
                st.rerun()
            else:
                joueur_elimine = top_votes[0][0] 
                supabase.table("joueurs").update({"est_elimine": True}).eq("code_salon", st.session_state.code_salon).eq("pseudo", joueur_elimine).execute()
                nouveaux_survivants = [j for j in joueurs_en_vie if j["pseudo"] != joueur_elimine]
                gagnant = verifier_victoire(nouveaux_survivants)
                
                if gagnant: 
                    supabase.table("salons").update({"statut": "victoire", "vainqueur": gagnant}).eq("code_salon", st.session_state.code_salon).execute()
                else: 
                    supabase.table("salons").update({"statut": "resultats"}).eq("code_salon", st.session_state.code_salon).execute()
                st.rerun()

        if mon_profil and not mon_profil["est_elimine"]:
            if mon_profil["vote_contre"]: st.success("✅ Tu as voté ! Attends que les autres terminent.")
            else:
                st.write("Qui souhaites-tu éliminer ?")
                st.markdown('<div class="vote-btn">', unsafe_allow_html=True)
                for cible in joueurs_en_vie:
                    if cible["pseudo"] != st.session_state.nom_joueur:
                        avatar_cible = cible.get("avatar", "👤")
                        if st.button(f"👉 Voter contre {avatar_cible} {cible['pseudo']}", key=f"vote_{cible['pseudo']}"):
                            supabase.table("joueurs").update({"vote_contre": cible["pseudo"]}).eq("id", mon_profil["id"]).execute()
                            st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        else: st.error("💀 Tu es éliminé, tu ne peux pas voter.")
            
        st.write("---")
        st.caption(f"Votes enregistrés : {len(a_vote)} / {len(joueurs_en_vie)}")

    # --- PHASE B Bis : ÉGALITÉ ---
    elif statut_actuel == "en_egalite":
        st.markdown('<div class="app-title">⚖️ Égalité !</div>', unsafe_allow_html=True)
        cibles_list = salon_info[0]["cibles_egalite"].split(",")
        st.warning(f"🚨 Égalité parfaite entre **{' et '.join(cibles_list)}** ! \n\nVous avez 30 secondes pour vous défendre avant l'ultime vote de départage.")
        a_vote = [j for j in joueurs_en_vie if j["vote_contre"] is not None]
        
        if len(a_vote) == len(joueurs_en_vie) and len(joueurs_en_vie) > 0 and not st.session_state.verrou_action:
            st.session_state.verrou_action = True
            
            votes = [j["vote_contre"] for j in a_vote]
            compte = Counter(votes)
            top_votes = compte.most_common()
            joueur_elimine = top_votes[0][0]
            
            supabase.table("joueurs").update({"est_elimine": True}).eq("code_salon", st.session_state.code_salon).eq("pseudo", joueur_elimine).execute()
            nouveaux_survivants = [j for j in joueurs_en_vie if j["pseudo"] != joueur_elimine]
            gagnant = verifier_victoire(nouveaux_survivants)
            
            if gagnant: 
                supabase.table("salons").update({"statut": "victoire", "vainqueur": gagnant, "cibles_egalite": None}).eq("code_salon", st.session_state.code_salon).execute()
            else: 
                supabase.table("salons").update({"statut": "resultats", "cibles_egalite": None}).eq("code_salon", st.session_state.code_salon).execute()
            st.rerun()

        if mon_profil and not mon_profil["est_elimine"]:
            if mon_profil["vote_contre"]: st.success("✅ Tu as revoté !")
            else:
                st.write("Choisis qui doit être éliminé :")
                st.markdown('<div class="vote-btn">', unsafe_allow_html=True)
                for cible in cibles_list:
                    avatar_cible = next((j["avatar"] for j in joueurs_en_vie if j["pseudo"] == cible), "👤")
                    if st.button(f"👉 Voter contre {avatar_cible} {cible}", key=f"revote_{cible}"):
                        supabase.table("joueurs").update({"vote_contre": cible}).eq("id", mon_profil["id"]).execute()
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        else: st.error("💀 Tu es éliminé, tu ne peux pas voter.")
             
        st.write("---")
        st.caption(f"Votes de départage enregistrés : {len(a_vote)} / {len(joueurs_en_vie)}")

    # --- PHASE C : RÉSULTATS INTERMÉDIAIRES ---
    elif statut_actuel == "resultats":
        st.markdown('<div class="app-title">💀 Résultat</div>', unsafe_allow_html=True)
        elimines = [j for j in tous_les_joueurs if j["est_elimine"]]
        st.subheader("Le village a tranché...")
        dernier_elimine = next((e for e in elimines if e.get("vote_contre") or e["est_elimine"]), None)
        
        if dernier_elimine:
             avatar_e = dernier_elimine.get("avatar", "👤")
             st.error(f"**{avatar_e} {dernier_elimine['pseudo']}** a été éliminé !")
             st.write(f"Son rôle était : **{dernier_elimine['role']}**")
             if dernier_elimine["role"] != "Mr. White": st.write(f"Son mot était : {dernier_elimine['mot_attribue']}")
        
        st.write("---")
        if st.session_state.est_createur:
            st.write("L'imposteur est toujours là...")
            if st.button("Nouveau tour (Continuer la partie)", type="primary"):
                nouveau_tour(st.session_state.code_salon)
                st.rerun()
        else:
            st.info("⏳ En attente du créateur pour la suite...")
