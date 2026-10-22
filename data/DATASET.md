# Setul sintetic SecFlow

**Origine:** generat local de `src/mia_demo/simulation/generator.py`; nu este extras din MIA și nu conține persoane reale. Fișierele vechi PaySim din proiectul părinte nu sunt modificate sau amestecate cu această populație.

Configurația implicită (`config/generator.yaml`) are 400 de conturi locale, 10.000 de **cereri de plată** și 100 de zile fixe, 13 iulie–20 octombrie 2026. Data de sfârșit este aproape de momentul prezentării, astfel încât cererile noi au istoric recent pentru ferestrele de 5 minute, 24 de ore și 30 de zile. Fluxul de observații este mai mare decât numărul de cereri, deoarece o cerere are o observație de încercare și, dacă a fost finalizată în istoricul sintetic, una de finalizare; există și intrări din PSP-uri externe fictive. Un set de 2.000 de conturi și aproximativ 150.000 de cereri se poate genera prin parametrii CLI, dar experimentele livrate folosesc volumul de dezvoltare de 10.000 pentru reproductibilitate rapidă. Testul automat verifică și prevalența unui volum de 11.000 de cereri; volumul de 150.000 nu a fost evaluat ca timp de execuție.

## Fișiere

| Fișier | Conținut |
|---|---|
| `accounts.jsonl` | conturi locale și solduri inițiale, în bani |
| `closing_balances.json` | soldurile după istoricul generat |
| `events.jsonl` | încercări, finalizări și intrări, cu `occurred_at` și `observed_at` UTC |
| `sessions.jsonl` | dispozitive și sesiuni observate |
| `account_events.jsonl` | resetări de parolă simulate |
| `requests.jsonl` | cererile scorabile; nu conțin etichete de fraudă |
| `features.jsonl` | caracteristici istorice calculate înaintea fiecărei cereri |
| `private/evaluation_labels.jsonl` | adevărul sintetic folosit numai pentru evaluare |
| `manifest.json` | numărări, parametri, amprentă SHA-256 și avertisment de proveniență |

## Construcție și delimitări

Conturile au destinatari preferați, ore de activitate obișnuite, sume variabile, plăți locale și externe și intrări recurente de tip salariu. Soldurile sunt întregi în bani și nu devin negative. Există cumpărături legitime neobișnuite care se suprapun cu semnalele de risc. PSP-ul local cunoaște doar propriile plăți și încasări; nu inventăm istoricul financiar al destinatarilor de la alte PSP-uri.

Cele cinci scenarii sunt: preluare de cont, flux rapid printr-un cont intermediar, transferuri repetate, inginerie socială și lanț/ciclu între conturi locale. Fiecare instanță rămâne într-o singură perioadă. În setul implicit, zilele 81–100 conțin 20 de cereri etichetate din 2.000 (1%). Etichetele sunt separate fizic de datele accesibile motorului de caracteristici. `observed_at`, nu `occurred_at`, determină ce era disponibil la momentul deciziei. Cererea curentă și sesiunea ei nu sunt tratate drept istoric.

| Zile | Utilizare |
|---|---|
| 1–10 | încălzirea istoricului |
| 11–60 | antrenare fără etichete și preprocesare |
| 61–70 | calibrare CDF pe rânduri noi |
| 71–80 | verificarea politicii fixate |
| 81–100 | test final blocat |

Toate valorile sunt alegeri de proiect universitar; nu sunt statistici ori praguri oficiale MIA.
