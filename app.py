import streamlit as st
import random
from supabase import create_client, Client
from streamlit_autorefresh import st_autorefresh
from collections import Counter

# 1. Configuration de la page
st.set_page_config(page_title="Undercover", page_icon="🕵️‍♂️", layout="centered", initial_sidebar_state="collapsed")

# --- INJECTION CSS ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 600px; }
    .stButton > button {
        width: 100%; border-radius: 25px; height: 50px; font-weight: 600;
        font-size: 16px; border: none; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: all 0.2s ease-in-out;
    }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15); }
    .stButton > button[kind="primary"] { background-color: #E63946; color: white; }
    .stButton > button[kind="primary"]:hover { background-color: #D62828; }
    .app-title { text-align: center; font-size: 2.5rem; font-weight: 800; margin-bottom: 1rem; color: #E63946; }
    .app-subtitle { text-align: center; font-size: 1.1rem; margin-bottom: 2rem; opacity: 0.8; }
    .card { background-color: rgba(255, 255, 255, 0.05); padding: 1.5rem; border-radius: 15px; margin-bottom: 1rem; }
    </style>
""", unsafe_allow_html=True)

# --- CONNEXION ---
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_connection()

# --- VARIABLES SESSION ---
if "page" not in st.session_state: st.session_state.page = "accueil"
if "nom_joueur" not in st.session_state: st.session_state.nom_joueur = ""
if "code_salon" not in st.session_state: st.session_state.code_salon = ""
if "est_createur" not in st.session_state: st.session_state.est_createur = False
if "afficher_mot" not in st.session_state: st.session_state.afficher_mot = False

# --- LOGIQUE ---
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
    supabase.table("salons").update({"statut": "en_jeu", "premier_joueur": joueur_qui_commence}).eq("code_salon", code).execute()
    st.session_state.afficher_mot = False

def nouveau_tour(code):
    # Réinitialise les votes pour le prochain tour et repasse en mode découverte/débat
    supabase.table("joueurs").update({"vote_contre": None}).eq("code_salon", code).execute()
    supabase.table("salons").update({"statut": "en_jeu"}).eq("code_salon", code).execute()
    st.session_state.afficher_mot = False

def terminer_manche(code):
    supabase.table("salons").update({"statut": "attente", "premier_joueur": None}).eq("code_salon", code).execute()
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
    if statut_salon and statut_salon[0]["statut"] != "attente":
        st.session_state.page = "jeu"
        st.rerun()
    
    st.markdown(f'<div class="app-title">Code : {st.session_state.code_salon}</div>', unsafe_allow_html=True)
    with st.container():
        st.subheader("👥 Joueurs connectés :")
        reponse_joueurs = supabase.table("joueurs").select("pseudo").eq("code_salon", st.session_state.code_salon).execute().data
        nb_joueurs = len(reponse_joueurs)
        for joueur in reponse_joueurs:
            icone = "🟢" if joueur['pseudo'] == st.session_state.nom_joueur else "⚪"
            st.markdown(f"**{icone} {joueur['pseudo']}**")
    
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

# ==========================================
# ÉCRAN 3 : LA PHASE DE JEU (MULTISTADE)
# ==========================================
elif st.session_state.page == "jeu":
    st_autorefresh(interval=3000, limit=None, key="jeu_refresh")
    salon_info = supabase.table("salons").select("statut, premier_joueur").eq("code_salon", st.session_state.code_salon).execute().data
    
    if not salon_info or salon_info[0]["statut"] == "attente":
        st.session_state.page = "lobby"
        st.session_state.afficher_mot = False
        st.rerun()
        
    statut_actuel = salon_info[0]["statut"]
    tous_les_joueurs = supabase.table("joueurs").select("*").eq("code_salon", st.session_state.code_salon).execute().data
    mon_profil = next((j for j in tous_les_joueurs if j["pseudo"] == st.session_state.nom_joueur), None)
    joueurs_en_vie = [j for j in tous_les_joueurs if not j["est_elimine"]]
    
    # ----------------------------------------
    # PHASE A : DÉCOUVERTE ET DÉBAT
    # ----------------------------------------
    if statut_actuel == "en_jeu":
        st.markdown('<div class="app-title">🕵️‍♂️ Phase de Débat</div>', unsafe_allow_html=True)
        if salon_info[0].get("premier_joueur"):
            st.info(f"🗣️ C'est **{salon_info[0]['premier_joueur']}** qui donne le premier mot !")
            
        if mon_profil and not mon_profil["est_elimine"]:
            with st.container():
                st.markdown('<div class="card">', unsafe_allow_html=True)
                if st.button("👁️ Révéler / Masquer mon mot", use_container_width=True):
                    st.session_state.afficher_mot = not st.session_state.afficher_mot
                if st.session_state.afficher_mot:
                    if mon_profil["role"] == "Mr. White":
                        st.success("🤫 **Tu es Mr. White !**")
                        st.caption("Tu n'as pas de mot. Écoute les autres et bluffe !")
                    else:
                        st.success(f"🔑 **Ton mot :** {mon_profil['mot_attribue']}")
                else:
                    st.info("🔒 Mot caché à l'abri des regards")
                st.markdown('</div>', unsafe_allow_html=True)
        elif mon_profil and mon_profil["est_elimine"]:
            st.error("💀 Tu es éliminé, observe le débat en silence !")

        if st.session_state.est_createur:
            st.write("---")
            if st.button("Passer aux votes 🗳️", type="primary"):
                supabase.table("salons").update({"statut": "en_vote"}).eq("code_salon", st.session_state.code_salon).execute()
                st.rerun()

    # ----------------------------------------
    # PHASE B : LES VOTES
    # ----------------------------------------
    elif statut_actuel == "en_vote":
        st.markdown('<div class="app-title">🗳️ Phase de Vote</div>', unsafe_allow_html=True)
        
        # Logique d'exécution automatique
        a_vote = [j for j in joueurs_en_vie if j["vote_contre"] is not None]
        if len(a_vote) == len(joueurs_en_vie) and len(joueurs_en_vie) > 0:
            # Tout le monde a voté, on calcule le perdant
            votes = [j["vote_contre"] for j in a_vote]
            compte = Counter(votes)
            joueur_elimine = compte.most_common(1)[0][0] # Prend celui qui a le plus de votes
            
            supabase.table("joueurs").update({"est_elimine": True}).eq("code_salon", st.session_state.code_salon).eq("pseudo", joueur_elimine).execute()
            supabase.table("salons").update({"statut": "resultats"}).eq("code_salon", st.session_state.code_salon).execute()
            st.rerun()

        if mon_profil and not mon_profil["est_elimine"]:
            if mon_profil["vote_contre"]:
                st.success("✅ Tu as voté ! Attends que les autres terminent.")
            else:
                st.write("Contre qui veux-tu voter ?")
                cibles = [j["pseudo"] for j in joueurs_en_vie if j["pseudo"] != st.session_state.nom_joueur]
                choix_vote = st.selectbox("Sélectionne un suspect :", ["(Sélectionner)"] + cibles)
                if st.button("Confirmer mon vote", type="primary"):
                    if choix_vote != "(Sélectionner)":
                        supabase.table("joueurs").update({"vote_contre": choix_vote}).eq("id", mon_profil["id"]).execute()
                        st.rerun()
        else:
            st.error("💀 Tu es éliminé, tu ne peux pas voter.")
            
        st.write("---")
        st.caption(f"Votes enregistrés : {len(a_vote)} / {len(joueurs_en_vie)}")
        for j in a_vote:
            st.write(f"✅ {j['pseudo']} a voté.")

    # ----------------------------------------
    # PHASE C : LES RÉSULTATS
    # ----------------------------------------
    elif statut_actuel == "resultats":
        st.markdown('<div class="app-title">💀 Résultat</div>', unsafe_allow_html=True)
        
        # On cherche le joueur qui vient d'être éliminé (celui qui a est_elimine à True et qui a reçu des votes)
        elimines = [j for j in tous_les_joueurs if j["est_elimine"]]
        
        st.subheader("Le village a tranché...")
        for e in elimines:
            st.error(f"**{e['pseudo']}** a été éliminé !")
            st.write(f"Son rôle était : **{e['role']}**")
            if e["role"] != "Mr. White":
                st.write(f"Son mot était : {e['mot_attribue']}")
            st.write("---")

        if st.session_state.est_createur:
            st.write("Que voulez-vous faire ?")
            if st.button("Nouveau tour de vote (Continuer la partie)", type="primary"):
                nouveau_tour(st.session_state.code_salon)
                st.rerun()
            if st.button("Terminer la manche (Retour Lobby)"):
                terminer_manche(st.session_state.code_salon)
                st.rerun()
        else:
            st.info("⏳ En attente du créateur pour la suite...")
