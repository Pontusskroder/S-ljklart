import os, base64, json, re
from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI
from PIL import Image
import io
app = Flask(__name__, static_folder=".")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM = """Du är Säljklart, en svensk AI-assistent som hjälper privatpersoner skriva riktigt bra annonser för Facebook Marketplace, Blocket och liknande.

MÅL:
Skriv en annons som känns som att en vanlig svensk privatperson har skrivit den: naturlig, tydlig, kort och lagom säljande.

REGLER:
- Hitta ALDRIG på fakta.
- Använd bara uppgifter som användaren har skrivit eller som faktiskt kan ses tydligt i bilden.
- Gissa aldrig modell, ålder, funktioner, material, tillbehör, skick eller tekniska egenskaper.
- Om användaren har angett en detalj, får du använda den även om den inte syns i bilden.
- Var ärlig om skick och eventuella fel.
- Undvik överdriven säljsnack och tomma klyschor.
- Rubriken ska vara kort, tydlig och lockande utan att överdriva.
- Annonsen ska normalt vara 2–4 korta stycken och gärna ha pris/plats längst ner.
- Använd några få relevanta emojis när det passar, men inte för många.

SAKNADE UPPGIFTER:
Bedöm om någon uppgift är viktig nog att fråga efter innan annonsen skrivs.
Fråga bara om det verkligen skulle göra annonsen betydligt bättre. Ställ högst 2 frågor.
Exempel på viktig information kan vara modell, storlek, antal, ålder eller om viktiga tillbehör ingår — men fråga bara om informationen är relevant för just produkten.
Om tillräckligt med information finns: ställ inga frågor.

SVAR:
Returnera ENDAST giltig JSON, utan markdown.
Om du behöver mer information:
{
  "needs_info": true,
  "questions": ["fråga 1", "fråga 2"]
}
Om du har tillräckligt:
{
  "needs_info": false,
  "headline": "...",
  "price_suggestion": "...",
  "ad_text": "..."
}

price_suggestion:
- Om användaren angett ett pris: skriv "💰 Ditt pris: X kr"
- Om inget pris angetts: skriv "💰 Pris saknas"
- Hitta aldrig på ett pris.
"""

def parse_json(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)

def build_content(item, desc, price, place, image):
    content = [{
        "type": "input_text",
        "text": f"Produkt: {item}\nBeskrivning: {desc}\nPris: {price}\nOrt: {place}"
  }] 
  if image and image.filename:
        raw = image.read()

        img = Image.open(io.BytesIO(raw))
        img.thumbnail((1200, 1200))

        buffer = io.BytesIO()
        img.convert("RGB").save(buffer, format="JPEG", quality=80, optimize=True)

        raw = buffer.getvalue()
        mime = "image/jpeg"
        b64 = base64.b64encode(raw).decode("utf-8")
        
  
        content.append({
            "type": "input_image",
            "image_url": f"data:{mime};base64,{b64}"
        })
    return content

@app.get("/")
def index():
    return send_from_directory(".", "index.html")

@app.post("/api/create-ad")
def create_ad():
    if not client.api_key:
        return jsonify(error="OPENAI_API_KEY saknas på servern."), 500

    item = request.form.get("item", "").strip()
    desc = request.form.get("desc", "").strip()
    price = request.form.get("price", "").strip()
    place = request.form.get("place", "").strip()
    answers = request.form.get("answers", "").strip()

    image = request.files.get("image")

    if not item and not desc and not image:
        return jsonify(error="Lägg till en bild eller skriv vad du säljer."), 400

    extra = f"\nSvar på följdfrågor:\n{answers}" if answers else ""
    content = build_content(item, desc, price, place, image)
    if extra:
        content[0]["text"] += extra

    try:
        response = client.responses.create(
            model="gpt-5.6-luna",
            instructions=SYSTEM,
            input=[{"role": "user", "content": content}],
        )
        data = parse_json(response.output_text)

        if data.get("needs_info"):
            return jsonify(
                needs_info=True,
                questions=data.get("questions", [])[:2]
            )

        return jsonify(
            needs_info=False,
            headline=data.get("headline", "Din annons"),
            price_suggestion=data.get("price_suggestion", ""),
            ad_text=data.get("ad_text", "")
        )
    except Exception as e:
        return jsonify(error=f"AI-fel: {e}"), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
