import streamlit as st
import random

# Configurer la page pour une navigation mobile agréable
st.set_page_config(page_title="Undercover", page_icon="🕵️‍♂️", layout="centered")

# --- INITIALISATION DES VARIABLES DE SESSION ---
# Ces variables restent en mémoire tant que l'onglet du téléphone est ouvert
if "page" not in st.session_state:
    st.session_state.page = "accueil"
if "nom_joueur" not in st.session_state:
    st.session_state.nom_joueur = ""
if "code_salon" not in st.session_state:
    st.session_state.code_salon = ""
if "est_createur" not in st.session_state:
    st.session_state.est_createur = False

# --- FONCTIONS DE LOGIQUE (SQUELETTE) ---
def creer_salon(nom):
    if nom.strip() == "":
        st.error("⚠️ S'il te plaît, choisis un pseudo !")
        return
    # Génère un code aléatoire de 4 lettres
    lettres = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    code = "".join(random.choice(lettres) for _ in range(4))
    
    st.session_state.nom_joueur = nom
    st.session_state.code_salon = code
    st.session_state.est_createur = True
    st.session_state.page = "lobby"

def rejoindre_salon(nom, code):
    if nom.strip() == "" or code.strip() == "":
        st.error("⚠️ Remplis ton pseudo ET le code du salon !")
        return
    st.session_state.nom_joueur = nom
    st.session_state.code_salon = code.upper()
    st.session_state.est_createur = False
    st.session_state.page = "lobby"

def quitter_salon():
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
    
    # Onglets pour séparer la création et la recherche de partie
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
    # Pour l'instant, ces joueurs sont fictifs (en attendant Supabase)
    st.write(f"🟢 {st.session_state.nom_joueur} (Toi)")
    st.write("⚪ Ami_1 (Fictif)")
    st.write("⚪ Ami_2 (Fictif)")
    
    st.write("---")
    
    if st.session_state.est_createur:
        st.info("👑 Tu es le chef du salon. Attends que tes amis soient connectés pour lancer.")
        if st.button("🚀 Lancer la partie", type="primary", use_container_width=True):
            st.session_state.page = "jeu"
            st.rerun()
    else:
        st.warning("⏳ En attente que le créateur lance la partie...")
        # Bouton temporaire pour tester l'écran suivant sans être créateur
        if st.button("Simuler le lancement (Test)", use_container_width=True):
            st.session_state.page = "jeu"
            st.rerun()
            
    if st.button("Quitter le salon", use_container_width=True):
        quitter_salon()
        st.rerun()

# ==========================================
# ÉCRAN 3 : LA PHASE DE JEU
# ==========================================
elif st.session_state.page == "jeu":
    st.title("🕵️‍♂️ Partie en cours !")
    st.write(f"Code : {st.session_state.code_salon} | Joueur : {st.session_state.nom_joueur}")
    
    st.write("---")
    st.subheader("Ton mot secret :")
    
    # Une case à cocher pour masquer/afficher le mot secret sur le téléphone
    afficher_mot = st.checkbox("👁️ Afficher mon mot secret (Cache ton écran !)")
    
    if afficher_mot:
        # Exemple fictif pour le test
        st.info("Ton mot est : **Chocolat** \n\n Ton rôle : **Civil**")
    else:
        st.write("🔒 Le mot est masqué. Coche la case pour le voir.")
        
    st.write("---")
    if st.button("Quitter la partie", use_container_width=True):
        quitter_salon()
        st.rerun()
