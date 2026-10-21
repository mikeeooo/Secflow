# Metodă experimentală și limite

**Populație:** date generate, conturi și dispozitive fictive, un PSP simulat. `data/manifest.json` identifică exact setul. Nicio cifră din raport nu este o statistică MIA. Etichetele separate din `data/private/evaluation_labels.jsonl` nu intră în antrenare sau în API.

**Cronologie:** zilele 1–10 încălzesc istoricul; 11–60 antrenează preprocesarea, IF și LOF fără etichete; 61–70 calibrează percentilele pe rânduri nevăzute; 71–80 verifică pragurile propuse de 60/85; 81–100 formează testul final blocat. Istoricul care traversează o graniță temporală poate informa o decizie ulterioară, dar niciun eveniment observat mai târziu nu intră în caracteristicile cererii.

**Comparație:** reguli singure, IF, LOF, IF+LOF și combinația sunt evaluate la pragul de alertă 60; `Verify` și `Block` sunt alerte, iar `Block` se numără separat. Raportul `evaluation.json` include precizie, recall, F1, rată de alarme false, aria sub curba precizie–recall, volumul alertelor, rezultate pe scenarii și timpul până la prima alertă. DBSCAN are un numitor separat: **cont-zi activ**, nu tranzacții. Sunt raportate atât noise, cât și regulile contextuale; etichetele de cluster nu se compară între zile.

**Variație:** comparația se repetă cu trei semințe ale generatorului; fiecare repetare antrenează și calibrează din propriul flux cronologic. Un test suplimentar aplică modelul de bază unor ID-uri de cont noi din aceeași familie de generator. Proiecțiile la 0,1% și 3% prevalență folosesc sensibilitatea și rata de alarme false măsurate; nu sunt prevalențe observate sau estimate pentru MIA.

**Latență:** `offline_assessment_latency` măsoară construirea scorului din caracteristici deja exportate, fără HTTP/SQLite. `api_benchmark` măsoară 30 de cereri locale prin FastAPI TestClient cu SQLite și model, dar fără transport de rețea. Sunt raportate p50/p95/p99, împreună cu platforma de test; ținta de 500 ms p95 este numai un obiectiv de inginerie al demo-ului, nu o cerință oficială MIA. Pentru DBSCAN, memoria `python_allocations_peak_mb` este alocarea Python urmărită, nu memoria nativă totală.

**Interpretare:** etichetele sunt scenarii inventate. Scorurile 0–100 și percentilele nu sunt probabilități de fraudă. Falsele alarme și cazurile ratate sunt păstrate în raport. O plată autorizată prin inginerie socială poate fi indistinctă de o plată normală dacă PSP-ul nu vede conversația victimei. Un ciclu local sau un punct DBSCAN rar este o observație pentru investigație. Istoricul offline rămâne fix chiar dacă o politică ar fi blocat o plată în contrafactual; API-ul live simulează separat decizia și efectul asupra soldului.

**Reproducere:** `uv run mia-demo all --robustness` și `uv run pytest -q`; versiunile sunt în `uv.lock`, modelul conține ordinea caracteristicilor, intervalele de antrenare/calibrare, parametrii, medianul de referință și amprenta lockfile-ului. Figura `model_comparison.png` este creată din același raport JSON.
