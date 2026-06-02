#!/usr/bin/env python3
"""
LBC Sniper - Détecte les bons deals sur Leboncoin et envoie une alerte Telegram
"""

import feedparser
import requests
import time
import json
import os
import re
from datetime import datetime
from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    EBAY_APP_ID,
    SEARCHES,
    CHECK_INTERVAL_MINUTES,
    MIN_MARGIN_EUROS,
    BUY_PRICE_RATIO
)

SEEN_IDS_FILE = "seen_ids.json"

URGENCY_KEYWORDS = [
    "urgent", "urgente", "urgence",
    "déménagement", "demenagement",
    "vente rapide", "à saisir", "a saisir",
    "besoin liquidités", "besoin de liquidités",
    "prix à débattre", "prix a debattre",
    "départ immédiat", "depart immediat",
    "fin de mois", "quitte paris",
    "cause divorce", "cause séparation",
]


def detect_urgency(text):
    text_lower = text.lower()
    found = [kw for kw in URGENCY_KEYWORDS if kw in text_lower]
    return found


def load_seen_ids():
    if os.path.exists(SEEN_IDS_FILE):
        with open(SEEN_IDS_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen_ids(ids):
    with open(SEEN_IDS_FILE, "w") as f:
        json.dump(list(ids), f)


def parse_price(text):
    """Extrait le prix depuis le titre ou la description d'une annonce"""
    matches = re.findall(r'(\d[\d\s]*)\s*€', text.replace('\xa0', ' '))
    if matches:
        price_str = matches[0].replace(' ', '')
        try:
            return int(price_str)
        except:
            return None
    return None


def get_lbc_rss(search_config):
    """Récupère les annonces via le flux RSS Leboncoin"""
    keyword = search_config["keyword"].replace(" ", "+")
    max_price = search_config.get("max_price", "")

    url = f"https://www.leboncoin.fr/recherche.rss?text={keyword}"
    if max_price:
        url += f"&price=0-{max_price}"

    print(f"  [RSS URL] {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=10)
    feed = feedparser.parse(response.content)
    return feed.entries


def get_ebay_sold_price(keyword, ebay_app_id):
    """Récupère le prix moyen des articles vendus sur eBay"""
    url = "https://svcs.ebay.com/services/search/FindingService/v1"
    params = {
        "OPERATION-NAME": "findCompletedItems",
        "SERVICE-VERSION": "1.0.0",
        "SECURITY-APPNAME": ebay_app_id,
        "RESPONSE-DATA-FORMAT": "JSON",
        "keywords": keyword,
        "itemFilter(0).name": "SoldItemsOnly",
        "itemFilter(0).value": "true",
        "itemFilter(1).name": "Condition",
        "itemFilter(1).value": "3000",  # Used
        "sortOrder": "EndTimeSoonest",
        "paginationInput.entriesPerPage": "10",
        "outputSelector": "SellingStatus"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        items = (
            data
            .get("findCompletedItemsResponse", [{}])[0]
            .get("searchResult", [{}])[0]
            .get("item", [])
        )

        prices = []
        for item in items:
            price = float(
                item.get("sellingStatus", [{}])[0]
                .get("currentPrice", [{}])[0]
                .get("__value__", 0)
            )
            if price > 0:
                prices.append(price)

        if prices:
            return round(sum(prices) / len(prices))
        return None

    except Exception as e:
        print(f"[eBay] Erreur : {e}")
        return None


def send_telegram(message):
    """Envoie un message Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.ok
    except Exception as e:
        print(f"[Telegram] Erreur : {e}")
        return False


def analyze_deal(entry, search_config):
    """Analyse une annonce et retourne les infos du deal si intéressant"""
    title = entry.get("title", "")
    link = entry.get("link", "")
    summary = entry.get("summary", "")

    # Extraire le prix depuis le titre ou le résumé
    lbc_price = parse_price(title) or parse_price(summary)
    if not lbc_price:
        return None

    # Prix max configuré pour cette recherche
    max_price = search_config.get("max_price")
    if max_price and lbc_price > max_price:
        return None

    # Récupérer le prix eBay
    ebay_price = get_ebay_sold_price(search_config["keyword"], EBAY_APP_ID)
    if not ebay_price:
        return None

    # Calcul
    max_buy_price = round(ebay_price * BUY_PRICE_RATIO)
    margin = ebay_price - lbc_price

    # Filtrer si pas assez rentable
    if lbc_price > max_buy_price:
        return None
    if margin < MIN_MARGIN_EUROS:
        return None

    full_text = f"{title} {summary}"
    urgency_signals = detect_urgency(full_text)

    return {
        "title": title,
        "link": link,
        "lbc_price": lbc_price,
        "ebay_price": ebay_price,
        "max_buy_price": max_buy_price,
        "margin": margin,
        "urgency_signals": urgency_signals
    }


def format_message(deal):
    margin = deal["margin"]
    urgency_signals = deal.get("urgency_signals", [])
    is_urgent = len(urgency_signals) > 0

    if is_urgent:
        emoji = "🚨🔥 VENDEUR URGENT — "
    elif margin >= 100:
        emoji = "🔥🔥 "
    else:
        emoji = "🔥 "

    urgency_line = ""
    if is_urgent:
        tags = ", ".join([f"#{kw.replace(' ', '_')}" for kw in urgency_signals])
        urgency_line = f"⚡️ Signaux urgence : <b>{tags}</b>\n"

    return (
        f"{emoji}<b>DEAL DÉTECTÉ</b>\n\n"
        f"📦 {deal['title']}\n\n"
        f"{urgency_line}"
        f"💰 Prix demandé : <b>{deal['lbc_price']}€</b>\n"
        f"🎯 Prix d'achat max : <b>{deal['max_buy_price']}€</b>\n"
        f"📈 Prix de revente estimé (eBay) : <b>{deal['ebay_price']}€</b>\n"
        f"💵 Marge potentielle : <b>~{deal['margin']}€</b>\n\n"
        f"🔗 <a href='{deal['link']}'>Voir l'annonce</a>\n\n"
        f"⏰ {datetime.now().strftime('%H:%M - %d/%m/%Y')}"
    )


def run():
    print(f"[LBC Sniper] Démarrage — vérification toutes les {CHECK_INTERVAL_MINUTES} min")
    seen_ids = load_seen_ids()

    while True:
        print(f"\n[{datetime.now().strftime('%H:%M')}] Scan en cours...")

        for search_config in SEARCHES:
            keyword = search_config["keyword"]
            print(f"  → Recherche : {keyword}")

            try:
                entries = get_lbc_rss(search_config)
            except Exception as e:
                print(f"  [RSS] Erreur : {e}")
                continue
            print(f"  [RSS] {len(entries)} annonces trouvées")
            for entry in entries:
                entry_id = entry.get("id") or entry.get("link")
                if entry_id in seen_ids:
                    continue

                seen_ids.add(entry_id)
                deal = analyze_deal(entry, search_config)

                if deal:
                    print(f"  ✅ Deal trouvé : {deal['title']} — marge {deal['margin']}€")
                    message = format_message(deal)
                    send_telegram(message)
                else:
                    print(f"  ✗ Pas rentable : {entry.get('title', '')[:50]}")

            time.sleep(2)  # Pause entre chaque recherche

        save_seen_ids(seen_ids)
        print(f"[Sniper] Prochain scan dans {CHECK_INTERVAL_MINUTES} minutes...")
        time.sleep(CHECK_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    run()
