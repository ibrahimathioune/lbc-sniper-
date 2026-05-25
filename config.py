# ============================================================
#  CONFIG LBC SNIPER — Modifie ce fichier selon tes besoins
# ============================================================

# --- TELEGRAM ---
TELEGRAM_BOT_TOKEN = "8617850044:AAFdXOEG4Mq9OWGaN3dWvv-YUeLK5c5x5h4"   # Ex: 7412345678:AAFxxxxx
TELEGRAM_CHAT_ID   = "5521890020" # Ex: 123456789

# --- EBAY API ---
EBAY_APP_ID = "Ibrahima-LBCSinpe-PRD-2183ec2e3-9023d18d"    # Créé gratuitement sur developer.ebay.com

# --- STRATÉGIE ---
BUY_PRICE_RATIO   = 0.60   # Achète max à 60% du prix de revente estimé
MIN_MARGIN_EUROS  = 50     # Marge minimale pour recevoir une alerte (€)
CHECK_INTERVAL_MINUTES = 15  # Fréquence de scan (en minutes)

# --- TES RECHERCHES ---
# Pour chaque niche que tu veux surveiller, ajoute un bloc ici.
# category : laisse "" si tu veux toutes catégories
# max_price : prix max que tu veux voir apparaître (filtre les articles trop chers)
# region : "ile_de_france" par défaut, ou "" pour toute la France

SEARCHES = [
    {
        "keyword": "raquette padel",
        "category": "",
        "max_price": 200,
        "region": "ile_de_france"
    },
    {
        "keyword": "vélo électrique",
        "category": "",
        "max_price": 800,
        "region": "ile_de_france"
    },
    {
        "keyword": "trottinette électrique",
        "category": "",
        "max_price": 400,
        "region": "ile_de_france"
    },
    {
        "keyword": "sneakers Jordan",
        "category": "",
        "max_price": 150,
        "region": "ile_de_france"
    },
    {
        "keyword": "console PS5",
        "category": "",
        "max_price": 350,
        "region": "ile_de_france"
    },
]
