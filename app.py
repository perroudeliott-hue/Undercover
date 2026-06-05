import streamlit as st
import random
from supabase import create_client, Client

st.set_page_config(page_title="Undercover", page_icon="🕵️‍♂️", layout="centered")

# --- CONNEXION À SUPABASE ---
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_connection()

# --- INITIALISATION DES VARIABLES DE SESSION ---
if "page" not in st.session_state:
    st.session_state.page = "accueil"
if "nom_joueur" not in st.session_state:
    st.session_state.nom_joueur = ""
if "code_salon" not in st.session_state:
    st.session_state.code_salon = ""
if "est_createur" not in st.session_state:
    st.session_state.est_createur = False
# Nouvelle variable pour gérer l'affichage du mot secret avec un bouton
if "afficher_mot" not in st.session_state:
    st.session_state.afficher_mot = False

# --- FONCTIONS DE LOGIQUE ---
def creer_salon(nom):
    if nom.strip() == "":
        st.error("⚠️ S'il te plaît, choisis un pseudo !")
        return
    lettres = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    code = "".join(random.choice(lettres) for _ in range(4))
    
    supabase.table("salons").insert({"code_salon": code, "statut": "attente"}).execute()
    supabase.table("joueurs").insert({"code_salon": code, "pseudo": nom}).execute()
    
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
        st.error("❌ Ce salon n'existe pas ou le code est faux !")
        return
        
    supabase.table("joueurs").insert({"code_salon": code, "pseudo": nom}).execute()
    st.session_state.nom_joueur = nom
    st.session_state.code_salon = code
    st.session_state.est_createur = False
    st.session_state.page = "lobby"

def lancer_partie(code):
    joueurs = supabase.table("joueurs").select("*").eq("code_salon", code).execute().data
    mots = supabase.table("mots").select("*").execute().data
    
    if not mots:
        st.error("⚠️ Aucun mot dans la base de données !")
        return
        
    paire = random.choice(mots)
    nb_joueurs = len(joueurs)
    
    # --- DISTRIBUTION DES RÔLES (AVEC MR. WHITE) ---
    roles = ["Undercover"]
    
    # On ajoute Mr. White uniquement s'il y a 4 joueurs ou plus
    if nb_joueurs >= 4:
        roles.append("Mr. White")
        
    # On comble le reste avec des Civils
    while len(roles) < nb_joueurs:
        roles.append("Civil")
        
    random.shuffle(roles)
    
    # Assigner les rôles
    for i, joueur in enumerate(joueurs):
        role_attribue = roles[i]
        
        if role_attribue == "Undercover":
            mot_attribue = paire["mot_undercover"]
        elif role_attribue == "Mr. White":
            mot_attribue = "Tu n'as pas de mot. Fais semblant de savoir !"
        else:
            mot_attribue = paire["mot_civil"]
            
        supabase.table("joueurs").update({
            "role": role_attribue, 
            "mot_attribue": mot_attribue
        }).eq("id", joueur["id"]).execute()
        
    supabase.table("salons").update({"statut": "en_jeu"}).eq("code_salon", code).execute()
    st.session_state.afficher_mot = False # Réinitialise l'affichage pour la nouvelle partie

def terminer_manche(code):
    # Ramène le salon en statut "attente"
    supabase.table("salons").update({"statut": "attente"}).eq("code_salon", code).execute()
    st.session_state.afficher_mot = False
    st.session_state.page = "lobby"

def quitter_salon():
    if st.session_state.nom_joueur and st.session_state.code_salon:
        supabase.table("joueurs").delete().eq("pseudo", st.session_state.nom_joueur).eq("code_salon", st.session_state.code_salon).execute()
    
    st.session_state.page = "accueil"
    st.session_state.code_salon = ""
    st.session_state.nom_joueur = ""
    st.session_state.est_createur = False
    st.session_state.afficher_mot = False


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
    
    # Vérifie si le jeu a été lancé
    statut_salon = supabase.table("salons").select("statut").eq("code_salon", st.session_state.code_salon).execute().data
    if statut_salon and statut_salon[0]["statut"] == "en_jeu":
        st.session_state.page = "jeu"
        st.rerun()
        
    st.subheader("Joueurs dans le salon :")
    reponse_joueurs = supabase.table("joueurs").select("pseudo").eq("code_salon", st.session_state.code_salon).execute()
    for joueur in reponse_joueurs.data:
        icone = "🟢" if joueur['pseudo'] == st.session_state.nom_joueur else "⚪"
        st.write(f"{icone} {joueur['pseudo']}")
    
    st.write("---")
    if st.button("🔄 Actualiser la liste", use_container_width=True):
        st.rerun()
    
    if st.session_state.est_createur:
        if st.button("🚀 Lancer la partie", type="primary", use_container_width=True):
            lancer_partie(st.session_state.code_salon)
            st.rerun()
    else:
        st.warning("⏳ En attente que le créateur lance la partie...")
            
    st.write("---")
    if st.button("Quitter définitivement le salon"):
        quitter_salon()
        st.rerun()

# ==========================================
# ÉCRAN 3 : LA PHASE DE JEU
# ==========================================
elif st.session_state.page == "jeu":
    # Vérifie si le créateur a terminé la manche
    statut_salon = supabase.table("salons").select("statut").eq("code_salon", st.session_state.code_salon).execute().data
    if statut_salon and statut_salon[0]["statut"] == "attente":
        st.session_state.page = "lobby"
        st.session_state.afficher_mot = False
        st.rerun()

    st.title("🕵️‍♂️ La partie a commencé !")
    
    infos_joueur = supabase.table("joueurs").select("role, mot_attribue").eq("code_salon", st.session_state.code_salon).eq("pseudo", st.session_state.nom_joueur).execute().data
    
    if infos_joueur:
        role = infos_joueur[0]["role"]
        mot = infos_joueur[0]["mot_attribue"]
        
        st.info("Garde ton écran à l'abri des regards !")
        
        # --- NOUVEAU BOUTON INTERRUPTEUR ---
        if st.button("👁️ Révéler / Masquer mon mot secret", use_container_width=True):
            st.session_state.afficher_mot = not st.session_state.afficher_mot
            st.rerun()
            
        if st.session_state.afficher_mot:
            st.success(f"**Ton mot :** {mot}")
            if role == "Mr. White":
                st.write(f"🤫 *Tu es **{role}** !*")
            else:
                st.write(f"*Ton rôle : {role}*")
        else:
            st.write("🔒 *Mot masqué*")
    else:
        st.error("Erreur : Impossible de récupérer ton rôle.")

    st.write("---")
    
    # --- BOUTONS DE FIN DE MANCHE ---
    if st.session_state.est_createur:
        if st.button("🛑 Terminer la manche (Retour au salon)", use_container_width=True, type="primary"):
            terminer_manche(st.session_state.code_salon)
            st.rerun()
    else:
        st.caption("Seul le créateur peut terminer la manche.")
        if st.button("🔄 Rafraîchir l'écran", use_container_width=True):
            st.rerun()
