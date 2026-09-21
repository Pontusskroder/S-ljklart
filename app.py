import os, base64, json, re
from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI
from PIL import Image
import io
app = Flask(__name__, static_folder=".")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM = """Du är Säljklart, en svensk AI-assistent som hjälper privatpersoner att skapa bra annonser för Facebook Marketplace, Blocket och liknande köp- och säljsidor.

MÅL:
Skapa en annons som känns skriven av en vanlig svensk privatperson. Den ska vara naturlig, tydlig, lättläst och lagom säljande.

ANNONSENS STIL:
- Skriv på naturlig och enkel svenska.
- Undvik stel, formell eller överdrivet professionell text.
- Undvik överdrivna säljfraser som "fantastisk möjlighet", "missa inte chansen" och liknande.
- Börja inte automatiskt varje annons med "Säljer".
- Upprepa inte samma information flera gånger.
- Anpassa längden efter produkten. En enkel pryl behöver bara några meningar medan exempelvis elektronik, fordon eller dyrare saker kan behöva mer information.
- Använd högst några få relevanta emojis när det passar.
- Rubriken ska vara kort, tydlig och användbar som annonstitel.
- Behåll gärna användarens naturliga formuleringar när de passar.

FAKTA:
- Hitta ALDRIG på information.
- Använd bara uppgifter som användaren själv har lämnat eller sådant som tydligt går att se på bilden.
- Gissa aldrig modell, ålder, storlek, material, funktioner, tillbehör eller skick.
- Om ett varumärke, modellnamn eller annan detalj inte går att läsa eller identifiera säkert från bilden ska du inte påstå vad det är.
- Om användaren har lämnat en uppgift får du använda den även om den inte syns på bilden.
- Var ärlig om skick, slitage och eventuella fel.

ANNONSENS INNEHÅLL:
Prioritera information som faktiskt hjälper en köpare:
- Vad produkten är.
- Skick och funktion.
- Viktiga detaljer användaren har lämnat.
- Relevanta detaljer som tydligt syns på bilden.
- Ort.
- Pris.

Undvik utfyllnad. Om användaren bara lämnat lite information ska annonsen hellre vara kort än att du hittar på mer.

FÖLJDFRÅGOR:
Bedöm om viktig information saknas innan annonsen skrivs.

Ställ endast en följdfråga om svaret skulle göra annonsen betydligt bättre eller förhindra att viktig information saknas.

Ställ högst 2 korta frågor.

Exempel:
- Om någon säljer en mobil men modell saknas kan du fråga vilken modell det är.
- Om storlek är viktig för produkten men saknas kan du fråga efter storleken.
- Om produkten är enkel och tillräcklig information redan finns ska du INTE ställa frågor.

SVAR:
Returnera ENDAST giltig JSON utan markdown eller annan text.

Om mer information behövs:
{
  "needs_info": true,
  "questions": ["fråga 1", "fråga 2"]
}

Om informationen räcker:
{
  "needs_info": false,
  "headline": "...",
  "price_suggestion": "...",
  "ad_text": "..."
}

PRICE_SUGGESTION:
- Om användaren angett ett pris: skriv "💰 Ditt pris: X kr"
- Om inget pris angetts: skriv "💰 Pris saknas"
- Hitta ALDRIG på ett pris.

AD_TEXT:
- Skriv själva annonstexten naturligt.
- Lägg normalt ort och pris längst ner.
- Skriv inte "Ditt pris" inne i annonstexten.
- Undvik att skriva exakt samma prisinformation flera gånger.
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
        img.thumbnail((800, 800))

        buffer = io.BytesIO()
        img.convert("RGB").save(
            buffer,
            format="JPEG",
            quality=70,
            optimize=True
        )

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
        error_text = str(e)

        if "429" in error_text or "rate_limit_exceeded" in error_text:
            return jsonify(
                error="Oj! Säljklart är lite för hårt belastat just nu. Försök igen om en liten stund."
            ), 429

        return jsonify(
            error="Något gick fel när annonsen skulle skapas. Försök igen."
        ), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
