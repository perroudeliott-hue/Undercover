import streamlit as st
import random
from supabase import create_client, Client

# Configurer la page
st.set_page_config(page_title="Undercover", page_icon="🕵️‍♂️", layout="centered")

# --- CONNEXION À SUPABASE ---
# st.cache_resource évite de se reconnecter à chaque clic sur l'écran
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

# --- FONCTIONS DE LOGIQUE (AVEC BASE DE DONNÉES) ---
def creer_salon(nom):
    if nom.strip() == "":
        st.error("⚠️ S'il te plaît, choisis un pseudo !")
        return
        
    # Génère un code aléatoire
    lettres = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    code = "".join(random.choice(lettres) for _ in range(4))
    
    # 1. Insérer le nouveau salon dans Supabase
    supabase.table("salons").insert({"code_salon": code, "statut": "attente"}).execute()
    
    # 2. Insérer le joueur dans la table des joueurs
    supabase.table("joueurs").insert({"code_salon": code, "pseudo": nom}).execute()
    
    # Mettre à jour l'état du téléphone
    st.session_state.nom_joueur = nom
    st.session_state.code_salon = code
    st.session_state.est_createur = True
    st.session_state.page = "lobby"

def rejoindre_salon(nom, code):
    if nom.strip() == "" or code.strip() == "":
        st.error("⚠️ Remplis ton pseudo ET le code du salon !")
        return
        
    code = code.upper()
    
    # 1. Vérifier si le salon existe dans Supabase
    reponse = supabase.table("salons").select("*").eq("code_salon", code).execute()
    
    # Si la réponse est vide, le salon n'existe pas
    if not reponse.data:
        st.error("❌ Ce salon n'existe pas ou le code est faux !")
        return
        
    # 2. Ajouter le joueur dans Supabase
    supabase.table("joueurs").insert({"code_salon": code, "pseudo": nom}).execute()
    
    st.session_state.nom_joueur = nom
    st.session_state.code_salon = code
    st.session_state.est_createur = False
    st.session_state.page = "lobby"

def quitter_salon():
    # Optionnel : On pourrait supprimer le joueur de la base de données ici
    st.session_state.page = "accueil"
    st.session_state.code_salon = ""
    st.session_state.est_createur = False


# ==========================================
# ÉCRAN 1 : L'ACCUEIL
# ==========================================
if st.session_state.page == "accueil":
    st.title("🕵️‍♂️ Undercover")
    st.write("Le jeu de bluff entre amis.")
    
    pseudo = st.text_input("Ton Pseudo", max_chars=12, placeholder="Ex: Batman")
    
    tab1, tab2 = st.tabs(["Créer un salon", "Rejoindre un salon"])
    
    with tab1:
        st.write("Crée un nouveau salon et partage le code avec tes amis.")
        if st.button("Créer la partie", use_container_width=True, type="primary"):
            creer_salon(pseudo)
            st.rerun()
            
    with tab2:
        code_input = st.text_input("Code du Salon (4 lettres)", max_chars=4, placeholder="ABCD")
        if st.button("Entrer dans le salon", use_container_width=True):
            rejoindre_salon(pseudo, code_input)
            st.rerun()

# ==========================================
# ÉCRAN 2 : LE LOBBY (SALON D'ATTENTE)
# ==========================================
elif st.session_state.page == "lobby":
    st.title(f"Salon : {st.session_state.code_salon}")
    st.write(f"Joueur : **{st.session_state.nom_joueur}**")
    
    st.subheader("Joueurs dans le salon :")
    
    # --- LECTURE DE LA BASE DE DONNÉES EN DIRECT ---
    reponse_joueurs = supabase.table("joueurs").select("pseudo").eq("code_salon", st.session_state.code_salon).execute()
    
    for joueur in reponse_joueurs.data:
        if joueur['pseudo'] == st.session_state.nom_joueur:
            st.write(f"🟢 **{joueur['pseudo']}** (Toi)")
        else:
            st.write(f"⚪ {joueur['pseudo']}")
    
    st.write("---")
    
    # Bouton de rafraîchissement manuel
    if st.button("🔄 Actualiser la liste", use_container_width=True):
        st.rerun()
    
    if st.session_state.est_createur:
        st.info("👑 Tu es le chef du salon.")
        if st.button("🚀 Lancer la partie", type="primary", use_container_width=True):
            st.session_state.page = "jeu"
            st.rerun()
    else:
        st.warning("⏳ En attente que le créateur lance la partie...")
        if st.button("Simuler le lancement (Test)", use_container_width=True):
            st.session_state.page = "jeu"
            st.rerun()
            
    if st.button("Quitter le salon", use_container_width=True):
        quitter_salon()
        st.rerun()

# ==========================================
# ÉCRAN 3 : LA PHASE DE JEU (A VENIR)
# ==========================================
elif st.session_state.page == "jeu":
    st.title("🕵️‍♂️ Partie en cours !")
    st.write("Le système de distribution des rôles arrive bientôt...")
    if st.button("Quitter la partie", use_container_width=True):
        quitter_salon()
        st.rerun()
