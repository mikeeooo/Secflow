# Demonstrație rapidă

1. Deschide http://127.0.0.1:8000 și autentifică-te cu `analyst` sau `admin`.
2. Overview: explică numărul transferurilor, cazurile nerezolvate și restricțiile. Datele sunt simulate, iar monedele nu sunt adunate între ele.
3. Transactions: caută `SIM_000003841`. Deschide rezultatul: suma 5976.41, șapte autentificări eșuate, dispozitiv nou. Compară cele trei scoruri și regulile.
4. Open investigation: citește nota demonstrativă existentă sau alege alt caz deschis, setează Investigating, adaugă o notă, salvează. Un caz rezolvat păstrează rezultatul investigației.
5. Manage sender restriction: introdu un motiv și deblochează contul. Transferul refuzat anterior rămâne Block. Audit trail păstrează schimbarea.
6. Transactions → Simulate transfer: alege conturi generate, sumă și dispozitiv; vezi noua decizie. Dacă expeditorul este restricționat, cererea este refuzată. Nu se mută bani reali.
7. Algorithm Results: explică referința, validarea, testul, confusion matrix și diferența dintre anomalie și fraudă. Compară rezultatele PaySim extins cu benchmarkul PaySim original.
8. Admin: schimbă parametrii și rulează din nou. Istoricul investigațiilor și deciziile inițiale se păstrează.
9. Exportă CSV/JSON sau folosește Print report pentru PDF din browser.

## Verificare realizată

- 18 teste automate trecute, incluzând cele ale datasetului original.
- Migrațiile SQLite și verificarea Django trecute.
- Primul replay: 6.520 transferuri importate, 256 de referință și 6.264 evaluate, aproximativ 6,3 secunde pe acest calculator.
- Un transfer manual suplimentar verificat: expeditor restricționat → Block → caz nou, fără etichetă de adevăr inventată.
- Autentificarea, filtrarea, detaliile și salvarea investigației verificate în browser.
- Desktop și mobil inspectate; cele cinci observații ale revizorului independent au fost corectate și marcate resolved.
- Motorul CLI Impeccable nu a putut rula în mediul local; verificarea vizuală și de cod s-a făcut direct.

Capturi: `.impeccable/review/desktop.png`, `mobile.png`, `case.png`. Rezultate reproductibile: `artifacts/benchmark.json`, `artifacts/latest-run.json`.
