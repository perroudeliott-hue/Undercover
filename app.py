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
    # 1. Récupérer les joueurs et les mots
    joueurs = supabase.table("joueurs").select("*").eq("code_salon", code).execute().data
    mots = supabase.table("mots").select("*").execute().data
    
    if not mots:
        st.error("⚠️ Aucun mot dans la base de données !")
        return
        
    paire = random.choice(mots)
    nb_joueurs = len(joueurs)
    
    # 2. Préparer et mélanger les rôles (1 Undercover, le reste en Civils)
    roles = ["Undercover"] + ["Civil"] * (nb_joueurs - 1)
    random.shuffle(roles)
    
    # 3. Assigner les rôles en base de données
    for i, joueur in enumerate(joueurs):
        role_attribue = roles[i]
        mot_attribue = paire["mot_undercover"] if role_attribue == "Undercover" else paire["mot_civil"]
        
        supabase.table("joueurs").update({
            "role": role_attribue, 
            "mot_attribue": mot_attribue
        }).eq("id", joueur["id"]).execute()
        
    # 4. Passer le salon en statut "en_jeu"
    supabase.table("salons").update({"statut": "en_jeu"}).eq("code_salon", code).execute()

def quitter_salon():
    # Optionnel : On supprime le joueur de la base en quittant
    if st.session_state.nom_joueur and st.session_state.code_salon:
        supabase.table("joueurs").delete().eq("pseudo", st.session_state.nom_joueur).eq("code_salon", st.session_state.code_salon).execute()
    
    st.session_state.page = "accueil"
    st.session_state.code_salon = ""
    st.session_state.nom_joueur = ""
    st.session_state.est_createur = False


# ==========================================
# ÉCRAN 1 : L'ACCUEIL
# ==========================================
if st.session_state.page == "accueil":
    st.title("🕵️‍♂️ Undercover")
    st.write("Le jeu de bluff entre amis.")
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
    
    # --- Vérifier si le jeu a été lancé par le créateur ---
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
            
    if st.button("Quitter le salon", use_container_width=True):
        quitter_salon()
        st.rerun()

# ==========================================
# ÉCRAN 3 : LA PHASE DE JEU
# ==========================================
elif st.session_state.page == "jeu":
    st.title("🕵️‍♂️ La partie a commencé !")
    
    # Récupérer les infos secrètes du joueur
    infos_joueur = supabase.table("joueurs").select("role, mot_attribue").eq("code_salon", st.session_state.code_salon).eq("pseudo", st.session_state.nom_joueur).execute().data
    
    if infos_joueur:
        role = infos_joueur[0]["role"]
        mot = infos_joueur[0]["mot_attribue"]
        
        st.info("Garde ton écran à l'abri des regards !")
        
        afficher_mot = st.checkbox("👁️ Coche la case pour voir ton mot secret")
        if afficher_mot:
            st.success(f"**Ton mot :** {mot}")
            st.write(f"*Ton rôle : {role}*")
        else:
            st.write("🔒 *Mot masqué*")
    else:
        st.error("Erreur : Impossible de récupérer ton rôle.")

    st.write("---")
    if st.button("Finir la partie et quitter", use_container_width=True):
        quitter_salon()
        st.rerun()
