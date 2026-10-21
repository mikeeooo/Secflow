# SecFlow · proiect universitar MIA

Aplicația integrată este în [mia_university_demo](mia_university_demo/README.md). Folosește date P2P **sintetice**, un backend FastAPI cu SQLite și o interfață React în stilul SecFlow. Aplicația Django anterioară rămâne în acest repository ca implementare istorică; demo-ul integrat pornește din folderul `mia_university_demo/`.

## Algoritmi și decizie

- **Isolation Forest** ordonează plățile neobișnuite față de distribuția globală.
- **Local Outlier Factor** compară fiecare plată cu vecini apropiați.
- **DBSCAN** grupează separat comportamentul zilnic al conturilor pentru investigare.
- **Regulile explicite** adaugă context observabil: frecvență, dispozitiv, destinatar, sumă și flux rapid după încasări.

Scorul 0–100 este un **rang de anomalie**, nu probabilitate de fraudă. `Permit`, `Verify` și `Block` sunt decizii simulate; nicio plată reală nu este transmisă. Etichetele scenariilor sunt păstrate separat și folosite doar pentru evaluare.

## Pornire

```sh
cd mia_university_demo
uv sync --extra dev --frozen
cd frontend && npm ci && cd ..
uv run uvicorn mia_demo.api:app --host 127.0.0.1 --port 8001
```

În alt terminal:

```sh
cd mia_university_demo/frontend
npm run dev -- --port 5173
```

Deschide [interfața](http://127.0.0.1:5173). Pentru verificare: `uv run pytest -q`, apoi în `frontend/`: `npx tsc --noEmit` și `npm run build`. Setul de date, modelul și raportul sunt generate și incluse local; comenzile de regenerare, proveniența și limitele sunt documentate în [README-ul aplicației integrate](mia_university_demo/README.md).
