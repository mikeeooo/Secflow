# SecFlow · Monitorizare MIA

Prototip universitar pentru un **analist bancar antifraudă**: monitorizează un portofoliu fictiv de transferuri instant în stil MIA, investighează alerte și consultă istoricul clienților. Interfață minimalistă în română, alb/albastru.

## Pornire locală

Python 3.11+, din acest director:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
export SECFLOW_DEMO_PASSWORD='alege-o-parola-locala'
.venv/bin/python manage.py setup_demo
.venv/bin/python manage.py run_demo
```

Deschide [SecFlow local](http://127.0.0.1:8000). `run_demo` pornește aplicația și procesul de analiză în fundal. Conturile `admin` și `analyst` primesc parola aleasă doar la prima creare.

CSV-ul existent `data/generated/secflow_transactions.csv` este necesar. Importul implicit folosește 2.000 de rânduri PaySim și toate cele 4.520 de scenarii generate. `setup_demo --paysim-limit 0` importă întregul set pregătit de 54.520 de rânduri. Datele, baza locală și fișierul de blocare al workerului sunt excluse din Git.

## Ce vede analistul

- **Monitorizare:** tranzacții MIA simulate, clienți cu semnale de risc și cazuri active.
- **Tranzacții:** nume de clienți, moment, sumă, decizie, căutare și export CSV.
- **Cazuri:** dosare active și istorice, note, responsabil și concluzie.
- **Clienți și conturi:** profil fictiv, istoric de tranzacții și dosare, restricții cu motiv.
- **Rezultate:** statistici calculate automat; parametrii și teoria algoritmilor nu încarcă interfața.

În liste sunt afișate doar semnalele de risc. **Deschiderea profilului unui client** arată și estimarea alertelor pentru următoarea oră de simulare, folosind activitatea recentă a acelui client. Estimarea volumului de alerte nu este probabilitate de fraudă.

Administratorul poate crea o cerere de test. Cererea este salvată imediat, apoi analizată de worker; pagina afișează automat rezultatul. Analistul lucrează cu rezultate și investigații, fără a lansa manual algoritmii.

## Algoritmii

| Implementare proprie | Semnal analizat |
|---|---|
| Isolation Forest | Cât de ușor se separă observația de referință |
| DBSCAN | Grup dens sau observație izolată în fereastra recentă |
| Local Outlier Factor | Densitatea locală față de vecinii din referință |

Scorul combină 30% IF + 25% LOF + 15% DBSCAN + 30% reguli. Sub 45: permisă; 45–64: de verificat; de la 65: blocată. O restricție existentă a expeditorului blochează cererea indiferent de scor. Pragurile sunt demonstrative; rezultatele PaySim sunt mai slabe decât cele ale scenariilor generate. Formule, exemple, complexități și rezultate măsurate: [ALGORITHMS.md](docs/ALGORITHMS.md).

## Arhitectura

```text
Browser → Django → SQLite (tranzacții, coadă și investigații)
                       ↑
               worker Python unic
                IF + DBSCAN + LOF
```

Django este singura dependență directă. Pagini randate pe server, SQLite și un worker local; fără Redis, Celery sau frontend separat. Coada persistă la repornire. Eșecurile sunt înregistrate, iar administratorul le poate relua. Vezi [arhitectura](docs/ARCHITECTURE.md).

## Date demonstrative și verificare

Numele clienților sunt fictive, generate determinist pentru conturile sursă. ID-urile originale rămân în date. Cererile generate sunt afișate ca **MDL demo**, fără conversia sau reclasificarea sumelor PaySim. Datele calendaristice reprezintă timpul simulării, începând cu 1 octombrie 2026. Dosarele istorice pregătite sunt marcate demonstrative; etichetele scenariilor justifică doar concluzia acelor exemple, fără a intra în detecție.

```sh
.venv/bin/python manage.py test tests
.venv/bin/python manage.py check
.venv/bin/python manage.py benchmark
```

`prepare_profiles` completează idempotent profilurile și istoricul, fără a modifica numele deja atribuite sau dosarele investigate. Workerul poate rula separat prin `manage.py analysis_worker` dacă folosești `runserver`.

Prototipul simulează un flux MIA; nu este conectat la sistemul BNM sau la o bancă și nu transferă bani reali. Context oficial: [MIA — Banca Națională a Moldovei](https://mia.bnm.md/ro/page/despre-mia).
