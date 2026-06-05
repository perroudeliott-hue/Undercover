import streamlit as st
import random
from supabase import create_client, Client
from streamlit_autorefresh import st_autorefresh

# 1. Configuration de la page
st.set_page_config(page_title="Undercover", page_icon="🕵️‍♂️", layout="centered", initial_sidebar_state="collapsed")

# --- INJECTION CSS (DESIGN DE L'APPLICATION) ---
st.markdown("""
    <style>
    /* Masquer le menu, le header et le footer de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Réduire l'espace vide en haut pour les mobiles */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 600px;
    }
    
    /* Style général des boutons (façon App Mobile) */
    .stButton > button {
        width: 100%;
        border-radius: 25px;
        height: 50px;
        font-weight: 600;
        font-size: 16px;
        border: none;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: all 0.2s ease-in-out;
    }
    
    /* Boutons secondaires au survol */
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
    }

    /* Style spécifique pour le bouton Primaire (Rouge Undercover) */
    .stButton > button[kind="primary"] {
        background-color: #E63946;
        color: white;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #D62828;
    }
    
    /* Titres stylisés */
    .app-title {
        text-align: center;
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 1rem;
        color: #E63946;
    }
    .app-subtitle {
        text-align: center;
        font-size: 1.1rem;
        margin-bottom: 2rem;
        opacity: 0.8;
    }
    
    /* Conteneurs pour faire des "Cartes" */
    .card {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- CONNEXION À SUPABASE ---
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_connection()

# --- VARIABLES DE SESSION ---
if "page" not in st.session_state:
    st.session_state.page = "accueil"
if "nom_joueur" not in st.session_state:
    st.session_state.nom_joueur = ""
if "code_salon" not in st.session_state:
    st.session_state.code_salon = ""
if "est_createur" not in st.session_state:
    st.session_state.est_createur = False
if "afficher_mot" not in st.session_state:
    st.session_state.afficher_mot = False

# --- LOGIQUE DU JEU ---
def creer_salon(nom):
    if nom.strip() == "":
        st.error("⚠️ Choisis un pseudo !")
        return
    lettres = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    code = "".join(random.choice(lettres) for _ in range(4))
    
    supabase.table("salons").insert({"code_salon": code, "statut": "attente"}).execute()
    supabase.table("joueurs").insert({"code_salon": code, "pseudo": nom, "est_elimine": False}).execute()
    
    st.session_state.nom_joueur = nom
    st.session_state.code_salon = code
    st.session_state.est_createur = True
    st.session_state.page = "lobby"

def rejoindre_salon(nom, code):
    if nom.strip() == "" or code.strip() == "":
        st.error("⚠️ Remplis ton pseudo ET le code du salon !")
        return
    code = code.upper()
    reponse = supabase.table("salons").select("*").eq("code_salon", code).execute()
    
    if not reponse.data:
        st.error("❌ Ce salon n'existe pas !")
        return
        
    supabase.table("joueurs").insert({"code_salon": code, "pseudo": nom, "est_elimine": False}).execute()
    st.session_state.nom_joueur = nom
    st.session_state.code_salon = code
    st.session_state.est_createur = False
    st.session_state.page = "lobby"

def lancer_partie(code, nb_undercover, nb_white):
    joueurs = supabase.table("joueurs").select("*").eq("code_salon", code).execute().data
    mots = supabase.table("mots").select("*").execute().data
    
    if not mots:
        st.error("⚠️ Aucun mot dans la base !")
        return
        
    paire = random.choice(mots)
    nb_joueurs = len(joueurs)
    
    roles = ["Undercover"] * nb_undercover + ["Mr. White"] * nb_white
    while len(roles) < nb_joueurs:
        roles.append("Civil")
    random.shuffle(roles)
    
    for i, joueur in enumerate(joueurs):
        role_attribue = roles[i]
        if role_attribue == "Undercover":
            mot_attribue = paire["mot_undercover"]
        elif role_attribue == "Mr. White":
            mot_attribue = "Tu n'as pas de mot. Fais semblant !"
        else:
            mot_attribue = paire["mot_civil"]
            
        supabase.table("joueurs").update({
            "role": role_attribue, 
            "mot_attribue": mot_attribue,
            "est_elimine": False,
            "vote_contre": None
        }).eq("id", joueur["id"]).execute()
        
    supabase.table("salons").update({"statut": "en_jeu"}).eq("code_salon", code).execute()
    st.session_state.afficher_mot = False

def terminer_manche(code):
    supabase.table("salons").update({"statut": "attente"}).eq("code_salon", code).execute()
    supabase.table("joueurs").update({"est_elimine": False, "vote_contre": None}).eq("code_salon", code).execute()
    st.session_state.afficher_mot = False
    st.session_state.page = "lobby"


# ==========================================
# ÉCRAN 1 : L'ACCUEIL
# ==========================================
if st.session_state.page == "accueil":
    st.markdown('<div class="app-title">🕵️‍♂️ Undercover</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">Le jeu de bluff entre amis</div>', unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        pseudo = st.text_input("👤 Ton Pseudo", max_chars=12, placeholder="Ex: Agent 007")
        
        tab1, tab2 = st.tabs(["🆕 Créer", "🤝 Rejoindre"])
        with tab1:
            st.write("Crée un salon et invite tes amis.")
            if st.button("Créer la partie", use_container_width=True, type="primary"):
                creer_salon(pseudo)
                st.rerun()
        with tab2:
            code_input = st.text_input("🔑 Code du Salon", max_chars=4, placeholder="ABCD")
            if st.button("Entrer dans le salon", use_container_width=True):
                rejoindre_salon(pseudo, code_input)
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# ÉCRAN 2 : LE LOBBY
# ==========================================
elif st.session_state.page == "lobby":
    st_autorefresh(interval=3000, limit=None, key="lobby_refresh")
    
    statut_salon = supabase.table("salons").select("statut").eq("code_salon", st.session_state.code_salon).execute().data
    if statut_salon and statut_salon[0]["statut"] == "en_jeu":
        st.session_state.page = "jeu"
        st.rerun()
    
    st.markdown(f'<div class="app-title">Code : {st.session_state.code_salon}</div>', unsafe_allow_html=True)
    
    with st.container():
        st.subheader("👥 Joueurs connectés :")
        reponse_joueurs = supabase.table("joueurs").select("pseudo").eq("code_salon", st.session_state.code_salon).execute().data
        nb_joueurs = len(reponse_joueurs)
        
        for joueur in reponse_joueurs:
            if joueur['pseudo'] == st.session_state.nom_joueur:
                st.markdown(f"**🟢 {joueur['pseudo']}** (Toi)")
            else:
                st.markdown(f"⚪ {joueur['pseudo']}")
    
    st.write("---")
    
    if st.session_state.est_createur:
        st.subheader("⚙️ Paramètres")
        col1, col2 = st.columns(2)
        with col1:
            nb_u = st.number_input("Undercover", min_value=1, max_value=max(1, nb_joueurs-1), value=1)
        with col2:
            nb_w = st.number_input("Mr. White", min_value=0, max_value=max(0, nb_joueurs-nb_u-1), value=0)
            
        st.write("") # Espace
        if st.button("🚀 Lancer la partie", type="primary", use_container_width=True):
            lancer_partie(st.session_state.code_salon, nb_u, nb_w)
            st.rerun()
    else:
        st.info("⏳ Le créateur configure la partie...")

# ==========================================
# ÉCRAN 3 : LA PHASE DE JEU
# ==========================================
elif st.session_state.page == "jeu":
    st_autorefresh(interval=3000, limit=None, key="jeu_refresh")
    
    statut_salon = supabase.table("salons").select("statut").eq("code_salon", st.session_state.code_salon).execute().data
    if statut_salon and statut_salon[0]["statut"] == "attente":
        st.session_state.page = "lobby"
        st.session_state.afficher_mot = False
        st.rerun()

    st.markdown('<div class="app-title">🕵️‍♂️ En jeu</div>', unsafe_allow_html=True)
    
    tous_les_joueurs = supabase.table("joueurs").select("*").eq("code_salon", st.session_state.code_salon).execute().data
    mon_profil = next((j for j in tous_les_joueurs if j["pseudo"] == st.session_state.nom_joueur), None)
    
    if mon_profil:
        if mon_profil["est_elimine"]:
            st.error("💀 Tu as été éliminé !")
            st.write(f"Ton rôle : **{mon_profil['role']}**")
        else:
            with st.container():
                st.markdown('<div class="card">', unsafe_allow_html=True)
                if st.button("👁️ Révéler / Masquer mon mot", use_container_width=True):
                    st.session_state.afficher_mot = not st.session_state.afficher_mot
                    
                if st.session_state.afficher_mot:
                    st.success(f"🔑 **Mot :** {mon_profil['mot_attribue']}")
                    st.caption(f"Ton rôle : {mon_profil['role']}")
                else:
                    st.info("🔒 Mot caché à l'abri des regards")
                st.markdown('</div>', unsafe_allow_html=True)
                
            st.write("---")
            st.subheader("🗳️ Tribunal")
            joueurs_en_vie = [j["pseudo"] for j in tous_les_joueurs if not j["est_elimine"] and j["pseudo"] != st.session_state.nom_joueur]
            
            choix_vote = st.selectbox("Contre qui votes-tu ?", ["(Sélectionner)"] + joueurs_en_vie)
            if st.button("Voter contre ce joueur"):
                if choix_vote != "(Sélectionner)":
                    supabase.table("joueurs").update({"vote_contre": choix_vote}).eq("id", mon_profil["id"]).execute()
                    st.toast(f"Vote enregistré !", icon="✅")
                    
    # --- RÉSULTAT DES VOTES ---
    st.write("---")
    st.write("**Urne en direct :**")
    votes_comptabilises = {}
    for j in tous_les_joueurs:
        if j["vote_contre"]:
            cible = j["vote_contre"]
            votes_comptabilises[cible] = votes_comptabilises.get(cible, 0) + 1
            st.write(f"👉 {j['pseudo']} accuse **{cible}**")
            
    # --- PANNEAU DU CRÉATEUR ---
    if st.session_state.est_createur:
        st.write("---")
        st.error("👑 Zone Créateur")
        if votes_comptabilises:
            joueur_a_eliminer = st.selectbox("Confirmer l'élimination :", list(votes_comptabilises.keys()))
            if st.button("💀 Éliminer ce joueur"):
                supabase.table("joueurs").update({"est_elimine": True}).eq("code_salon", st.session_state.code_salon).eq("pseudo", joueur_a_eliminer).execute()
                st.rerun()
                
        if st.button("🔄 Nouvelle Manche (Retour Salon)", use_container_width=True, type="primary"):
            terminer_manche(st.session_state.code_salon)
            st.rerun()
            
    # Joueurs éliminés
    elimines = [j for j in tous_les_joueurs if j["est_elimine"]]
    if elimines:
        st.write("---")
        for e in elimines:
            st.caption(f"💀 {e['pseudo']} était {e['role']}")
