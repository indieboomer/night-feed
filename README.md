# Night-Feed

**Samodzielnie hostowany agent AI generujący codzienny briefing audio o trendach w grach i technologii - po polsku, w stylu ASMR.**

## Czym jest Night-Feed?

Night-Feed to system, który automatycznie:

1. **Zbiera dane** - Steam Top Sellers, Steam Trending, wybrane kanały RSS (Hacker News, Eurogamer.pl, Spider's Web, GameDev.net i inne)
2. **Analizuje sygnały** - wykrywa trendy, nietypowe ruchy w rankingach, ciekawe wiadomości
3. **Generuje skrypt** - tworzy strukturalny skrypt podcastu (10-15 min) w języku polskim za pomocą LLM
4. **Konwertuje na audio** - zmienia tekst na mowę używając ElevenLabs (polski głos, styl ASMR)
5. **Publikuje podcast** - aktualizuje kanał RSS i udostępnia pliki MP3 przez NGINX

Jeden odcinek dziennie, codziennie o 21:30, gotowy do wysłuchania przed snem.

---

## Architektura

```
┌──────────────┐
│ Orchestrator │ (APScheduler, uruchamia codziennie o 21:30)
└──────┬───────┘
       │
       ├──► Collector ──► /data/signals.json
       │    (Steam API + RSS feeds)
       │
       ├──► Writer ──► /output/scripts/YYYY-MM-DD.txt
       │    (OpenAI GPT-4o, polskie prompty)
       │
       └──► Publisher ──► /output/episodes/YYYY-MM-DD.mp3
            (ElevenLabs TTS)  /output/feed.xml

┌────────┐
│ NGINX  │ Serwuje /feed.xml i /episodes/*.mp3
└────────┘
```

**Komunikacja:** Współdzielone wolumeny Docker, sekwencyjne wykonywanie, wymiana danych przez pliki

---

## Instalacja

### Wymagania

- Docker & Docker Compose
- Klucze API:
  - OpenAI API (GPT-4o) - [platform.openai.com](https://platform.openai.com)
  - ElevenLabs API - [elevenlabs.io](https://elevenlabs.io)
  - Steam API (opcjonalnie) - [steamcommunity.com/dev/apikey](https://steamcommunity.com/dev/apikey)

### Krok 1: Klonowanie repozytorium

```bash
git clone https://github.com/twoj-username/night-feed.git
cd night-feed
```

### Krok 2: Konfiguracja zmiennych środowiskowych

```bash
cp .env.example .env
nano .env
```

**Edytuj `.env` i uzupełnij:**

```bash
# OpenAI API
OPENAI_API_KEY=sk-twoj-klucz-openai

# ElevenLabs API
ELEVENLABS_API_KEY=twoj-klucz-elevenlabs
ELEVENLABS_VOICE_ID=pMsXgVXv3BLzUgSXRplE  # Lub ID własnego głosu

# Ustawienia podcastu
PODCAST_BASE_URL=http://localhost:8080  # Zmień na swój adres URL

# Opcjonalnie: Discord notyfikacje
DISCORD_WEBHOOK_URL=
ENABLE_NOTIFICATIONS=false
```

### Krok 3: Tworzenie katalogów danych

```bash
mkdir -p data output/episodes output/scripts
```

### Krok 4: Build i uruchomienie

```bash
docker-compose build
docker-compose up -d orchestrator nginx
```

### Krok 5: Sprawdzenie logów

```bash
docker-compose logs -f orchestrator
```

---

## Pierwszy test

Aby przetestować system bez czekania na 21:30:

```bash
# Uruchom kolektor ręcznie
docker-compose run collector python /app/collector.py

# Sprawdź zebrane dane
cat data/signals.json | head -20

# Uruchom writer
docker-compose run writer python /app/writer.py

# Sprawdź wygenerowany skrypt
cat output/scripts/$(date +%Y-%m-%d).txt | head -50

# Uruchom publisher
docker-compose run publisher python /app/publisher.py

# Sprawdź czy odcinek został wygenerowany
ls -lh output/episodes/
curl http://localhost:8080/feed.xml
```

---

## Dostęp do podcastu

Po wygenerowaniu pierwszego odcinka:

1. **Lokalnie:** Otwórz `http://localhost:8080/feed.xml` w aplikacji podcastowej
2. **Apple Podcasts:** Dodaj „Podcast według URL" → wpisz `http://localhost:8080/feed.xml`
3. **Inne aplikacje:** Pocket Casts, Overcast, AntennaPod – wszystkie wspierają RSS

---

## Deployment na serwer (automatyczny)

### GitHub Actions (Recommended)

**1. Przygotuj serwer:**

```bash
# Na serwerze
mkdir -p ~/night-feed
cd ~/night-feed
git clone https://github.com/twoj-username/night-feed.git .

# Stwórz .env (NIE commituj do git!)
cp .env.example .env
nano .env  # Uzupełnij klucze API

# Pierwsze uruchomienie
docker-compose build
docker-compose up -d
```

**2. Skonfiguruj klucz SSH:**

```bash
# Na lokalnej maszynie
ssh-keygen -t ed25519 -C "github-actions-night-feed" -f ~/.ssh/night_feed_deploy

# Skopiuj klucz publiczny na serwer
ssh-copy-id -i ~/.ssh/night_feed_deploy.pub uzytkownik@adres-serwera

# Testuj połączenie
ssh -i ~/.ssh/night_feed_deploy uzytkownik@adres-serwera "echo 'Connected!'"

# Skopiuj PRYWATNY klucz (całość)
cat ~/.ssh/night_feed_deploy
```

**3. Dodaj sekrety do GitHub:**

Repozytorium → Settings → Secrets and variables → Actions → New repository secret

- `SERVER_HOST` - IP lub domena serwera (np. `192.168.1.100`)
- `SERVER_USER` - Użytkownik SSH (np. `ubuntu`)
- `SSH_PRIVATE_KEY` - Cała zawartość pliku prywatnego klucza (z `-----BEGIN/END-----`)
- `SERVER_PORT` - Port SSH (domyślnie `22`)

**4. Push → Automatyczny deployment:**

```bash
git add .
git commit -m "Configure deployment"
git push origin main
```

GitHub Actions automatycznie połączy się z serwerem, pobierze kod, zbuduje i uruchomi kontenery.

---

## Konfiguracja

### Zmiana godziny generowania

Edytuj `.env`:

```bash
DAILY_RUN_TIME=06:00  # Zamiast 21:30
```

Restart:

```bash
docker-compose restart orchestrator
```

### Dodawanie źródeł RSS

Edytuj `config/rss_sources.yml`:

```yaml
sources:
  - name: twoje_zrodlo
    url: https://example.com/rss
    language: pl
    category: tech
    priority: high
```

Zmiany są stosowane przy następnym uruchomieniu kolektora.

### Zmiana głosu (ElevenLabs)

1. Przejdź do [elevenlabs.io/voice-library](https://elevenlabs.io/voice-library)
2. Wybierz polski głos lub sklonuj własny
3. Skopiuj Voice ID
4. Edytuj `.env`:

```bash
ELEVENLABS_VOICE_ID=nowe-voice-id
```

5. Lub edytuj `config/voice_settings.json` dla bardziej zaawansowanych ustawień głosu.

### Dostosowanie promptów

Edytuj `config/prompts/system_prompt.txt` - główna instrukcja dla LLM

Edytuj `config/prompts/user_prompt.j2` - szablon danych wejściowych

---

## Struktura katalogów

```
night-feed/
├── services/
│   ├── orchestrator/   # Scheduler i kontroler pipeline'u
│   ├── collector/      # Zbieranie danych (Steam + RSS)
│   ├── writer/         # Generowanie skryptu (OpenAI)
│   └── publisher/      # TTS (ElevenLabs) + RSS feed
│
├── nginx/              # Serwer HTTP dla feed.xml i MP3
├── config/             # Konfiguracja (RSS, prompty, głos)
├── data/               # Bazy danych, cache, historia (gitignored)
├── output/             # Wygenerowane odcinki i skrypty (gitignored)
│   ├── episodes/       # Pliki MP3
│   ├── scripts/        # Skrypty tekstowe
│   └── feed.xml        # Kanał RSS podcastu
│
├── .github/workflows/  # GitHub Actions deployment
├── scripts/            # Pomocnicze skrypty (deploy.sh)
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Koszty (miesięczne)

| Usługa | Koszt | Szczegóły |
|--------|-------|-----------|
| OpenAI GPT-4o | ~$4.50 | ~$0.15/dzień (3k tokenów input, 1.5k output) |
| ElevenLabs TTS | ~$3.00 | ~$0.10/dzień (13 min audio) |
| **RAZEM** | **~$7.50/mies** | |

*Infrastruktura: $0 (self-hosted)*

---

## Troubleshooting

### Collector nie zbiera danych Steam

```bash
# Sprawdź logi
docker-compose logs collector

# Przetestuj ręcznie
docker-compose run collector python /app/collector.py
```

Możliwa przyczyna: Steam API czasowo niedostępne. System ponowi próbę.

### Writer nie generuje skryptu

```bash
# Sprawdź klucz API
echo $OPENAI_API_KEY

# Sprawdź czy signals.json istnieje
cat data/signals.json

# Przetestuj manualnie
docker-compose run writer python /app/writer.py
```

### Publisher nie generuje audio

```bash
# Sprawdź klucz ElevenLabs
echo $ELEVENLABS_API_KEY

# Sprawdź Voice ID
cat config/voice_settings.json

# Przetestuj
docker-compose run publisher python /app/publisher.py
```

### RSS feed nie działa

```bash
# Sprawdź NGINX
curl http://localhost:8080/feed.xml

# Sprawdź czy plik istnieje
ls -lh output/feed.xml

# Sprawdź logi NGINX
docker-compose logs nginx
```

### GitHub Actions deployment fails

1. Sprawdź sekrety w GitHub (Settings → Secrets)
2. Testuj SSH lokalnie: `ssh uzytkownik@serwer "echo test"`
3. Sprawdź czy serwer ma git i docker-compose

---

## Zaawansowane

### Ręczne uruchomienie pipeline'u

```bash
docker exec night-feed-orchestrator python /app/run_pipeline.py
```

### Wyświetlanie historii wykonań

```bash
docker exec night-feed-orchestrator sqlite3 /data/execution_log.db "SELECT * FROM executions ORDER BY created_at DESC LIMIT 10;"
```

### Backup danych

```bash
# Backup baz danych
tar -czf backup-$(date +%Y%m%d).tar.gz data/ output/

# Kopiuj na inny serwer
scp backup-*.tar.gz user@backup-server:/backups/
```

### Zmiana modelu LLM

Edytuj `.env`:

```bash
LLM_MODEL=gpt-4o-mini  # Tańszy, ale gorsza jakość
# lub
LLM_MODEL=gpt-4o       # Droższy, lepsza jakość
```

---

## Licencja

MIT License

---

## Credits

- OpenAI GPT-4o - generowanie skryptów
- ElevenLabs - synteza mowy po polsku
- Steam API - dane o grach
- Kanały RSS - wiadomości tech/gaming
- Docker - konteneryzacja
- NGINX - hosting plików

---

## Support

Problemy? Otwórz [issue](https://github.com/twoj-username/night-feed/issues)

---

**Night-Feed** - Intelligence amplifier, not a public podcast tool.
