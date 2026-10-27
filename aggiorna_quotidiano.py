import os
import json
import datetime
import urllib.request
import xml.etree.ElementTree as ET

API_KEY = os.getenv("LLM_API_KEY")
API_URL = "https://api.openai.com/v1/chat/completions"

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
    system_prompt = """
Sei il caporedattore de "L'OGGETTIVO".
Prendi i lanci d'agenzia grezzi, epura qualsiasi aggettivazione sensazionalistica, framing emotivo o propaganda, e restituisci l'evento in modo esaustivo, fisico e misurabile.
Stile di scrittura: alla Niccolò Ammaniti (asciutto, visivo, frasi brevi, dettagli cinestetici e materiali), ma con svolgimento logico chiarissimo (chi fa cosa, numeri certi, conseguenze reali).

Restituisci ESCLUSIVAMENTE un JSON valido con questa struttura esatta:
{
  "kicker": "LUOGO • AMBITO",
  "headline": "TITOLO ESAUSTIVO CON DINAMICA, CIFRE E CONSEGUENZE IMMEDIATE",
  "what": "Cosa è accaduto realmente in una frase secca",
  "numbers": "Parametri misurabili accertati (cifre, orari, persone, euro, metri)",
  "consequence": "Effetto materiale immediato sul territorio",
  "body": "<p>Svolgimento cronologico alla Ammaniti...</p>",
  "bias_media": "Esempio del titolo emotivo/clickbait usato dai media tradizionali",
  "fact_pure": "Sintesi del fatto nudo e verificato"
}
"""
    user_prompt = f"Sezione: {sezione}\nLanci d'agenzia grezzi di oggi:\n{testi_grezzi}"

    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2
    }).encode('utf-8')

    req = urllib.request.Request(API_URL, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    })

    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        return json.loads(res['choices'][0]['message']['content'])

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
