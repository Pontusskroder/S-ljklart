# Säljklart – AI-prototyp

Det här är versionen där "Gör min annons" faktiskt anropar OpenAI via en säker server.
API-nyckeln ligger INTE i webbsidan.

## Starta lokalt

1. Installera Python 3.10+.
2. Öppna terminalen i den här mappen.
3. Kör:
   `pip install -r requirements.txt`
4. Sätt din OpenAI API-nyckel som miljövariabel:
   macOS/Linux:
   `export OPENAI_API_KEY="din-nyckel"`
   Windows PowerShell:
   `$env:OPENAI_API_KEY="din-nyckel"`
5. Kör:
   `python app.py`
6. Öppna `http://127.0.0.1:5000`

Viktigt: lägg aldrig API-nyckeln direkt i HTML/JavaScript eller lägg upp den på GitHub.

Modellen är vald för låg kostnad och stöd för text + bild. Prisförslag är medvetet inte påhittade i denna prototyp; nästa steg kan koppla på riktig marknadsdata.
