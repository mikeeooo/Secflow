# Integrarea MIA în SecFlow · 22 octombrie 2026

## Ce este proiectul activ

`mia_university_demo/` este aplicația SecFlow integrată. Backendul FastAPI, generatorul, caracteristicile istorice, modelele, politica de risc, SQLite și evaluarea provin din demo-ul MIA. Interfața React a fost adaptată la stilul SecFlow: fundal alb, navigare structurală deschisă, tabele aerisite și albastru rezervat acțiunilor. Django rămâne în repository ca implementare anterioară.

| Etapă din planul universitar | Rezultat în aplicația integrată |
| --- | --- |
| Săptămâna 1 · generator cronologic | `src/mia_demo/simulation/`, `config/generator.yaml`, `data/manifest.json` și setul sintetic local de 10.000 de cereri |
| Săptămâna 2 · caracteristici istorice | `src/mia_demo/features/`, calcule pe observații disponibile înaintea cererii și teste de limite temporale |
| Săptămâna 3 · IF și LOF | `src/mia_demo/ml/`, modelul local `model-v1-ba3a098dbf83`, ordine fixă a caracteristicilor și calibrare separată |
| Săptămâna 4 · risc și API | `src/mia_demo/risk/`, `api.py`, decizii persistate și adapter mock idempotent |
| Săptămâna 5 · DBSCAN și UI | constatări zilnice datate, șase zone React și flux de revizuire auditat |
| Săptămâna 6 · evaluare | `reports/evaluation.json`, `reports/methodology.md`, comparații și limite explicite |

Setul MIA este complet sintetic și nu se combină cu PaySim. Modelul și raportul provin din rularea reproductibilă a proiectului sursă; nu au fost reantrenate în timpul integrării. Cele 150.000 de cereri din plan rămân o țintă de volum configurabilă, fără benchmark livrat la acel volum. Rularea livrată este pentru 10.000 de cereri și 400 de conturi.

## Verificări efectuate pe copia integrată

- `PYTHONPATH=src .venv/bin/python -m pytest -q`: **26 teste trecute**, 2 avertismente de mediu/dependențe.
- `npm ci --offline`, `npm test` și `npm run build`: instalarea din cache, cele trei cazuri de interval local (vară, iarnă, schimbarea orei), tipurile și buildul au trecut.
- Hashul SHA-256 al `data/manifest.json` este identic cu sursa (`a63d3836d3190c32d5b594281eccd5c443a2be2cb8e18406ad84101e50b68950`).
- API-ul pornit local a răspuns `status=ok`, `simulation=true`, cu modelul `model-v1-ba3a098dbf83`; proxy-ul React `/api/health` a răspuns identic.
- În browser au fost deschise monitorizarea, tranzacțiile, conturile, simulatorul, investigația și evaluarea. Meniul îngust pune focusul pe prima legătură, îl limitează în meniu, se închide cu Escape și întoarce focusul la buton. După alegerea unei pagini, focusul ajunge în conținut. Când este închis, meniul nu rămâne în ordinea de tastatură; primul Tab ajunge la linkul „Sari la conținut”.
- Un test sintetic a produs `Permit` și plata mock `Finalizată`; presetul atipic a produs `Verify`, apoi aprobarea a păstrat decizia `Verify`, a finalizat plata mock și a adăugat intrarea în jurnal; presetul de viteză mare a produs `Block` cu plata `Neexecutată`.
- Filtrul de tranzacții pentru 21 octombrie a inclus încercările de la 00:08–00:58 ora Chișinăului, care ar fi fost excluse cu o limită UTC directă. Baza de date a fost apoi readusă la copia din proiectul sursă, pentru a livra un demo curat.
- Capturi ale interfeței integrate la lățimea disponibilă în browser: `reports/integrated-overview-mobile.jpg` și `reports/integrated-evaluation-mobile.jpg`.

Instalarea Python complet nouă nu a putut fi verificată offline în sandbox, fiindcă wheel-ul `scipy` din lockfile nu era în cache. Pentru rularea locală verificată s-au folosit pachetele deja instalate în mediul virtual copiat din sursă și `PYTHONPATH=src`. Comanda obișnuită `uv sync --extra dev --frozen` rămâne documentată pentru un mediu cu acces la registrul de pachete. Mediul virtual este ignorat de Git; setul sintetic, baza SQLite, modelele și raportul sunt incluse în fișierele proiectului, iar regenerarea se poate face cu `uv run mia-demo all --robustness` după instalare.
