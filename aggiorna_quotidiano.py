import os
import json
import datetime
import urllib.request
import xml.etree.ElementTree as ET

API_KEY = os.getenv("LLM_API_KEY")
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

FEEDS = {
    "nord": "https://www.ansa.it/lombardia/notizie/lombardia_rss.xml",
    "centro": "https://www.ansa.it/lazio/notizie/lazio_rss.xml",
    "sud": "https://www.ansa.it/campania/notizie/campania_rss.xml",
    "esteri": "https://www.ansa.it/sito/notizie/mondo/mondo_rss.xml",
    "sport": "https://www.ansa.it/sito/notizie/sport/sport_rss.xml",
    "futuro": "https://www.ansa.it/canale_scienza_tecnica/notizie/scienzaetecnica_rss.xml"
}

def scarica_titoli_rss(url, max_items=4):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            tree = ET.fromstring(response.read())
            items = []
            for item in tree.findall(".//item")[:max_items]:
                titolo = item.find("title").text if item.find("title") is not None else ""
                desc = item.find("description").text if item.find("description") is not None else ""
                clean_desc = desc.replace("<[^>]*>", "").strip()
                items.append(f"- Titolo: {titolo} | Dettagli: {clean_desc}")
            return "\n".join(items) if items else "Nessun lancio disponibile."
    except Exception as e:
        return f"Errore recupero feed: {str(e)}"

def chiama_ia_debiasing(sezione, testi_grezzi):
    prompt_completo = f"""
Sei il caporedattore de "L'OGGETTIVO".
Prendi i lanci d'agenzia grezzi, epura qualsiasi aggettivazione sensazionalistica, framing emotivo o propaganda, e restituisci l'evento in modo esaustivo, fisico e misurabile.
Stile di scrittura del corpo: alla Niccolò Ammaniti (asciutto, visivo, frasi brevi, dettagli cinestetici e materiali), ma con svolgimento logico chiarissimo (chi fa cosa, numeri certi, conseguenze reali).

Restituisci ESCLUSIVAMENTE un JSON valido (senza blocchi di codice markdown ```json, solo il testo puro delle parentesi graffe) con questa struttura esatta:
{{
  "kicker": "LUOGO • AMBITO",
  "headline": "TITOLO ESAUSTIVO CON DINAMICA, CIFRE E CONSEGUENZE IMMEDIATE",
  "what": "Cosa è accaduto realmente in una frase secca",
  "numbers": "Parametri misurabili accertati (cifre, orari, persone, euro, metri)",
  "consequence": "Effetto materiale immediato sul territorio",
  "body": "<p>Svolgimento cronologico alla Ammaniti...</p>",
  "bias_media": "Esempio del titolo emotivo/clickbait usato dai media tradizionali",
  "fact_pure": "Sintesi del fatto nudo e verificato"
}}

Sezione: {sezione}
Lanci d'agenzia grezzi di oggi:
{testi_grezzi}
"""

    payload = json.dumps({
        "contents": [{
            "parts": [{"text": prompt_completo}]
        }],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.2
        }
    }).encode('utf-8')

    req = urllib.request.Request(API_URL, data=payload, headers={
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY
    })

    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        testo_json = res['candidates'][0]['content']['parts'][0]['text']
        return json.loads(testo_json)

def main():
    oggi = datetime.date.today()
    numero_edizione = (oggi - datetime.date(oggi.year, 1, 1)).days + 1
    
    edizione = {
        "data": oggi.strftime("%A %d %B %Y").upper(),
        "numero_edizione": numero_edizione,
        "sezioni": {}
    }

    for sez, url in FEEDS.items():
        grezzi = scarica_titoli_rss(url)
        articolo = chiama_ia_debiasing(sez, grezzi)
        edizione["sezioni"][sez] = articolo

    with open("edizione_oggi.json", "w", encoding="utf-8") as f:
        json.dump(edizione, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
