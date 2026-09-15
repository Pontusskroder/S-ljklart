import os, base64
from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI

app = Flask(__name__, static_folder=".")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM = """Du är Säljklart, en svensk AI-assistent som skriver bättre annonser för privatpersoner.
Skriv naturlig, trovärdig svenska. Överdriv aldrig och hitta inte på egenskaper som användaren inte uppgett.
Om en bild finns, använd den endast för att beskriva sådant som faktiskt syns.
Returnera ENDAST JSON med nycklarna headline, price_suggestion, ad_text.
headline: kort och tydlig annonsrubrik.
price_suggestion: om användaren angett pris, skriv '💰 Ditt pris: X kr'. Om inte, skriv '💰 Prisförslag: behöver mer marknadsdata' — hitta inte på ett pris.
ad_text: färdig annons med stycken och eventuell punktlista. Ta med plats om den angivits.
"""

@app.get("/")
def index():
    return send_from_directory(".", "index.html")

@app.post("/api/create-ad")
def create_ad():
    if not client.api_key:
        return jsonify(error="OPENAI_API_KEY saknas på servern."), 500

    item = request.form.get("item","").strip()
    desc = request.form.get("desc","").strip()
    price = request.form.get("price","").strip()
    place = request.form.get("place","").strip()

    if not item and not desc and "image" not in request.files:
        return jsonify(error="Lägg till en bild eller skriv vad du säljer."), 400

    content = [{
        "type": "input_text",
        "text": f"Produkt: {item}\nBeskrivning: {desc}\nPris: {price}\nOrt: {place}"
    }]

    image = request.files.get("image")
    if image and image.filename:
        raw = image.read()
        mime = image.mimetype or "image/jpeg"
        b64 = base64.b64encode(raw).decode("utf-8")
        content.append({"type":"input_image","image_url":f"data:{mime};base64,{b64}"})

    try:
        response = client.responses.create(
            model="gpt-5.6-luna",
            instructions=SYSTEM,
            input=[{"role":"user","content":content}],
        )
        import json
        text = response.output_text
        data = json.loads(text)
        return jsonify(data)
    except Exception as e:
        return jsonify(error=f"AI-fel: {e}"), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
