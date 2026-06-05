import streamlit as st
import random
from supabase import create_client, Client
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Undercover", page_icon="🕵️‍♂️", layout="centered")

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

# --- LOGIQUE ---
def creer_salon(nom):
    if nom.strip() == "":
        st.error("⚠️ S'il te plaît, choisis un pseudo !")
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
        st.error("⚠️ Aucun mot dans la base de données !")
        return
        
    paire = random.choice(mots)
    nb_joueurs = len(joueurs)
    
    # Distribution personnalisée
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
    # Réinitialiser les votes et éliminations
    supabase.table("joueurs").update({"est_elimine": False, "vote_contre": None}).eq("code_salon", code).execute()
    st.session_state.afficher_mot = False
    st.session_state.page = "lobby"


# ==========================================
# ÉCRAN 1 : L'ACCUEIL
# ==========================================
if st.session_state.page == "accueil":
    st.title("🕵️‍♂️ Undercover")
    pseudo = st.text_input("Ton Pseudo", max_chars=12)
    
    tab1, tab2 = st.tabs(["Créer un salon", "Rejoindre un salon"])
    with tab1:
        if st.button("Créer la partie", use_container_width=True, type="primary"):
            creer_salon(pseudo)
            st.rerun()
    with tab2:
        code_input = st.text_input("Code du Salon (4 lettres)", max_chars=4)
        if st.button("Entrer dans le salon", use_container_width=True):
            rejoindre_salon(pseudo, code_input)
            st.rerun()

# ==========================================
# ÉCRAN 2 : LE LOBBY
# ==========================================
elif st.session_state.page == "lobby":
    st.title(f"Salon : {st.session_state.code_salon}")
    
    # Auto-refresh pour tout le monde toutes les 3 secondes
    st_autorefresh(interval=3000, limit=None, key="lobby_refresh")
    
    statut_salon = supabase.table("salons").select("statut").eq("code_salon", st.session_state.code_salon).execute().data
    if statut_salon and statut_salon[0]["statut"] == "en_jeu":
        st.session_state.page = "jeu"
        st.rerun()
        
    st.subheader("Joueurs dans le salon :")
    reponse_joueurs = supabase.table("joueurs").select("pseudo").eq("code_salon", st.session_state.code_salon).execute().data
    
    nb_joueurs = len(reponse_joueurs)
    for joueur in reponse_joueurs:
        icone = "🟢" if joueur['pseudo'] == st.session_state.nom_joueur else "⚪"
        st.write(f"{icone} {joueur['pseudo']}")
    
    st.write("---")
    
    if st.session_state.est_createur:
        st.subheader("Paramètres de la partie")
        col1, col2 = st.columns(2)
        with col1:
            nb_u = st.number_input("Undercover", min_value=1, max_value=max(1, nb_joueurs-1), value=1)
        with col2:
            nb_w = st.number_input("Mr. White", min_value=0, max_value=max(0, nb_joueurs-nb_u-1), value=0)
            
        if st.button("🚀 Lancer la partie", type="primary", use_container_width=True):
            lancer_partie(st.session_state.code_salon, nb_u, nb_w)
            st.rerun()
    else:
        st.warning("⏳ En attente que le créateur lance la partie...")

# ==========================================
# ÉCRAN 3 : LA PHASE DE JEU
# ==========================================
elif st.session_state.page == "jeu":
    # Auto-refresh pour suivre l'état des votes et de la partie
    st_autorefresh(interval=3000, limit=None, key="jeu_refresh")
    
    statut_salon = supabase.table("salons").select("statut").eq("code_salon", st.session_state.code_salon).execute().data
    if statut_salon and statut_salon[0]["statut"] == "attente":
        st.session_state.page = "lobby"
        st.session_state.afficher_mot = False
        st.rerun()

    st.title("🕵️‍♂️ La partie a commencé !")
    
    tous_les_joueurs = supabase.table("joueurs").select("*").eq("code_salon", st.session_state.code_salon).execute().data
    mon_profil = next((j for j in tous_les_joueurs if j["pseudo"] == st.session_state.nom_joueur), None)
    
    if mon_profil:
        if mon_profil["est_elimine"]:
            st.error("💀 Tu as été éliminé !")
            st.write(f"Ton rôle était : **{mon_profil['role']}**")
        else:
            if st.button("👁️ Révéler / Masquer mon mot secret", use_container_width=True):
                st.session_state.afficher_mot = not st.session_state.afficher_mot
                
            if st.session_state.afficher_mot:
                st.success(f"**Ton mot :** {mon_profil['mot_attribue']}")
                if mon_profil["role"] == "Mr. White":
                    st.write(f"🤫 *Tu es **{mon_profil['role']}** !*")
                else:
                    st.write(f"*Ton rôle : {mon_profil['role']}*")
            else:
                st.write("🔒 *Mot masqué*")
                
            st.write("---")
            st.subheader("Voter contre un joueur")
            joueurs_en_vie = [j["pseudo"] for j in tous_les_joueurs if not j["est_elimine"] and j["pseudo"] != st.session_state.nom_joueur]
            
            choix_vote = st.selectbox("Qui soupçonnes-tu ?", ["(Choisir)"] + joueurs_en_vie)
            if st.button("Voter"):
                if choix_vote != "(Choisir)":
                    supabase.table("joueurs").update({"vote_contre": choix_vote}).eq("id", mon_profil["id"]).execute()
                    st.toast(f"Vote enregistré contre {choix_vote} !", icon="✅")
                    
    # --- RÉSULTAT DES VOTES ---
    st.write("---")
    st.write("**Votes actuels :**")
    votes_comptabilises = {}
    for j in tous_les_joueurs:
        if j["vote_contre"]:
            cible = j["vote_contre"]
            votes_comptabilises[cible] = votes_comptabilises.get(cible, 0) + 1
            st.write(f"• {j['pseudo']} a voté contre **{cible}**")
            
    # --- PANNEAU DU CRÉATEUR ---
    if st.session_state.est_createur:
        st.write("---")
        st.subheader("👑 Contrôles du Créateur")
        if votes_comptabilises:
            joueur_a_eliminer = st.selectbox("Éliminer le joueur (révèle son rôle):", list(votes_comptabilises.keys()))
            if st.button("Éliminer ce joueur", type="primary"):
                supabase.table("joueurs").update({"est_elimine": True}).eq("code_salon", st.session_state.code_salon).eq("pseudo", joueur_a_eliminer).execute()
                st.rerun()
                
        if st.button("🛑 Terminer la manche (Retour au salon)", use_container_width=True):
            terminer_manche(st.session_state.code_salon)
            st.rerun()
            
    # Affichage des rôles des joueurs éliminés
    elimines = [j for j in tous_les_joueurs if j["est_elimine"]]
    if elimines:
        st.write("---")
        st.write("💀 **Joueurs éliminés :**")
        for e in elimines:
            st.error(f"{e['pseudo']} était **{e['role']}** !")
