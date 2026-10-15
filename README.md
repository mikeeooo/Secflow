# SecFlow

Proiect universitar de monitorizare a transferurilor MIA simulate. Interfață în română, alb/albastru, cu grafice, alerte, clienți fictivi și investigații. **Isolation Forest, DBSCAN și Local Outlier Factor rulează în fundal**, fără controale sau detalii tehnice în interfața analistului.

## Pornire

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
export SECFLOW_DEMO_PASSWORD='alege-o-parola-locala'
.venv/bin/python manage.py setup_demo
.venv/bin/python manage.py run_demo
```

Deschide [SecFlow local](http://127.0.0.1:8000). Conturile `admin` și `analyst` primesc parola aleasă doar la prima creare. `run_demo` pornește aplicația și workerul local. Scenariul începe automat; **Pauză scenariu** permite investigarea unui moment. La final, **Reia scenariul** adaugă un ciclu nou, păstrând istoricul și notele.

## Demonstrația

- **Monitorizare:** interval de 1/6/24 ore simulate, grafic transferuri/alerte, decizii, coadă și timp real măsurat de procesare.
- **Tranzacții:** căutare, decizie, risc și export CSV.
- **Cazuri:** note, responsabil, concluzie și dosare istorice demonstrative.
- **Clienți:** nume fictive, cont, istoric, restricții și estimarea alertelor pentru următoarea oră.
- **Rezultate:** alarme corecte, fraude simulate detectate și alarme false pe testul separat.

Scenariul reproductibil are **1.520 de transferuri / 48 de conturi**: 256 referință, 256 validare, 768 istoric de test și 240 cereri redate succesiv, aproximativ una la 3 secunde. Include fraude simulate și plăți legitime neobișnuite. CSV-ul și manifestul sunt generate automat de `datasets/demo_mia.py`; nu trebuie descărcate date pentru pornire. Timpul avansează accelerat din 1 octombrie 2026; sumele reprezintă MDL demonstrativi. Nu există integrare bancară sau transferuri reale.

Scorul MIA este gradual, 0–100: **55 de puncte din semnalele celor trei algoritmi + 45 din comportamentul observabil** (sumă, frecvență, dispozitiv, beneficiar, autentificări, încasări și istoric). Pragurile individuale se aleg pe validare; ponderile și pragurile deciziei sunt fixe. Sub 45: scăzut; 45–59: moderat; de la 60: ridicat. Verificare de la 45; blocare pentru o cerere nouă de la 70. În profil și la tranzacție se văd cauzele, elementele favorabile și calculul contribuțiilor. Listele arată scorul actual; decizia inițială și notele rămân păstrate. Profilul arată riscul **ultimului transfer evaluat**, nu maximul istoric.

Scorul nu este probabilitate de fraudă. Estimarea separată din profil prognozează **numărul alertelor**. Formule, implementare și limite: [ALGORITHMS.md](docs/ALGORITHMS.md). Evaluare reproductibilă a celor 768 de cereri originale de test: `manage.py evaluate_mia` → `artifacts/mia-continuous-evaluation.json`.

## Arhitectura simplă

```text
Browser → Django → SQLite (tranzacții, coadă, investigații, starea redării)
                       ↑
         un worker Python: redare → IF + DBSCAN + LOF → rezultat salvat
```

Django este singura dependență directă. HTML randat pe server, CSS, JavaScript și grafice SVG; fără frontend separat, Redis sau Celery. Dashboardul se actualizează la 3 secunde. Un singur worker, coadă persistentă, recuperare după repornire și protecție împotriva dublării cererilor. Endpointul autentificat `/metrics/` oferă măsurători în format Prometheus; demo-ul nu necesită servere Grafana/Prometheus. Vezi [arhitectura](docs/ARCHITECTURE.md).

```sh
.venv/bin/python manage.py test tests
.venv/bin/python manage.py check
```

Datele PaySim originale și scenariile anterioare rămân experimente separate. Import opțional: `setup_demo --legacy` (necesită CSV-ul vechi); benchmarkul original: `manage.py benchmark`. Datele generate, baza locală și fișierele de blocare nu intră în Git.
