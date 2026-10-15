# Algoritmii SecFlow — ghid pentru susținere

Acest ghid explică implementarea efectivă. Teoria și parametrii rămân aici; platforma arată numai rezultate și observații pentru investigație. Toate cele trei metode sunt implementate în `detection/algorithms.py`, fără scikit-learn.

## Politica folosită în prezentarea MIA

Demonstrația implicită folosește `datasets/demo_mia.py` și `detection/mia.py`. Secțiunile 5, 7 și 9 de mai jos documentează **experimentul anterior PaySim/scenarii extinse**, păstrat separat pentru comparație; ponderile sale nu sunt politica dashboardului MIA.

Setul nou are 1.520 de cereri integral sintetice pentru 48 de conturi: 36 expeditori și 12 beneficiari. Sumele obișnuite au distribuție log-normală, cu medie de scară diferită între clienți. Scenariile includ sume foarte mari, dispozitive noi după autentificări eșuate și secvențe rapide. Există intenționat și sume mari legitime și dispozitive noi legitime. Etichetele sunt adevărul scenariului, nu constatări bancare reale. Proporția de fraude este îmbogățită pentru demonstrație și nu reproduce frecvența bancară.

| Segment cronologic | Rânduri | Utilizare |
|---|---:|---|
| Referință | 256 | Normalizare, arbori și densități; scenarii normale prin construcție |
| Validare | 256 | Selectarea pragurilor individuale IF și LOF |
| Test istoric | 768 | Raportarea evaluării separate, fără ajustarea pragurilor |
| Flux demonstrativ | 240 | Cereri ascunse până la redare, analizate succesiv de worker |

Parametri: 48 arbori, eșantion 64, seed 42, k=10, ε=1,8, minimum 4 puncte, fereastră de 24 cereri. `mia.fit()` maximizează F1 **numai pe validare**, din grilele IF `[0,5; 0,55; 0,6; 0,65; 0,7; 0,75]` și LOF `[1,3; 1,5; 2; 3; 5; 10]`. La egalitate alege pragul mai mare. Pentru seed-ul 73 al setului, rezultă IF ≥0,65 și LOF ≥3. DBSCAN semnalează eticheta −1. Testul nu decide pragurile.

Scorul actual este definit în `detection/risk.py`, versiunea `continuous-v2`. Înlocuiește voturile binare, care produceau numai câteva valori. Toate contribuțiile sunt deterministe; nu adăugăm zgomot pentru procente diferite.

```text
F = limitare(0,5 + (IF − prag_IF) / (2 × max(prag_IF − 0,35; 0,05)), 0, 1)
L = max(0, LOF − 1) / (max(0, LOF − 1) + max(prag_LOF − 1; 0,1))
D = 1 pentru noise DBSCAN, altfel 0
profil = 25×F + 20×L + 10×D                 [maximum 55 puncte]
scor = rotunjire(profil + factorii observabili) [maximum 100]
```

Cele două intensități continue păstrează diferențe între observațiile apropiate de prag și cele foarte îndepărtate. Un rezultat individual la prag înseamnă jumătate din contribuția sa posibilă, nu probabilitate 50% de fraudă. Pragurile individuale IF/LOF sunt alese pe validare; maparea, ponderile și pragurile finale 45/70 sunt alegeri fixe ale demo-ului, stabilite înainte de măsurarea noului test.

| Factor observabil | Maximum | Calcul, limitat între 0 și 1 |
|---|---:|---|
| Suma față de media proprie | 12 | `log2(max(raport,1))/4`; zero dacă nu există istoric |
| Frecvență | 8 | maxim dintre `cereri_60s/3` și `cereri_300s/6` |
| Dispozitiv nou | 6 | 1 nou, 0 folosit anterior |
| Autentificări eșuate | 8 | număr / 6 |
| Beneficiar nou | 4 | 1 nou, 0 folosit anterior |
| Încasări recente | 4 | număr în 5 minute / 4 |
| Istoric limitat | 3 | `(5 − număr_cereri_anterioare)/5` |

Contribuțiile se rotunjesc la două zecimale, se însumează și abia apoi totalul se rotunjește la întreg. Exemplu de aritmetică: profil 26,40 + sumă 8,20 + frecvență 4 + dispozitiv 6 + acces 5,33 + beneficiar 4 + încasări 0 + istoric 0 = 53,93 → **54/100**. Acesta este un exemplu ilustrativ, nu o tranzacție măsurată.

Niveluri afișate: sub45 scăzut; 45–59 moderat; 60–100 ridicat. Politica pentru cereri noi cere verificare de la45 și blocare de la70; severitatea afișată și acțiunea sunt concepte distincte. Un factor obișnuit adaugă zero sau puține puncte; nu adăugăm reduceri arbitrare negative. „Elemente favorabile” înseamnă contribuții mici, nu dovadă că plata este sigură. Un cont deja restricționat poate bloca cererea independent de scor.

Explicația stocată conține toate cele opt componente (profil + șapte factori), valorile observate, contribuția, plafonul și pragurile. Profilul este componenta agregată a metodelor; factorii observabili sunt componente explicite ale politicii. Nu pretindem că aceste componente sunt o atribuire cauzală SHAP sau o explicație internă a arborilor. Numele algoritmilor și formulele rămân în cod/documentație. Nici eticheta `truth`, nici `scenario_type`, nici viitorul nu intră în calcul. Factorii comportamentali reutilizează unele semnale ale modelelor: ponderile sunt intenționat compozite și nu reprezintă dovezi independente.

La reanalizare, `Transaction.risk_explanation` se actualizează și o nouă `Assessment.explanation` păstrează fotografia explicației. `Transaction.risk` și decizia inițială rămân istorice; notele și concluziile cazurilor nu se rescriu. Listele și exportul folosesc scorul actual. Profilul și lista clienților folosesc ultimul transfer evaluat, nu maximul vieții contului. Un transfer cu scor mic ulterior nu dovedește că un caz anterior este închis.

`manage.py evaluate_mia` reproduce testul **istoric original**, indiferent câte cicluri au fost redate local. Pe cele 768 de cereri: 179 TP, 6 FP, 16 FN, 567 TN; precizie 96,8%, acoperire 91,8%, F1 94,2%, alarme false 1,0%. Apar **66 de valori distincte** ale scorului. Raport: `artifacts/mia-continuous-evaluation.json`. Datele sunt sintetice, cu fraude îmbogățite și scenarii concepute pentru aceste semnale; rezultatele nu demonstrează performanță bancară reală. Politica nu a fost ajustată după citirea acestui test. Raportul anterior al voturilor binare rămâne în `artifacts/mia-demo-evaluation.json`, pentru trasabilitate.

## 1. De la o tranzacție la un vector

Un algoritm numeric primește o listă de numere, nu un obiect Django. `features.build()` calculează nouă caracteristici, în această ordine:

| Caracteristică | Calcul în cod |
|---|---|
| Sumă | `log(1 + suma)` |
| Raport față de media proprie | `log(1 + suma / media sumelor anterioare)`; raport 1 dacă media lipsește sau este zero |
| Frecvență 60 secunde | Numărul cererilor anterioare ale expeditorului în interval |
| Frecvență 300 secunde | Numărul cererilor anterioare ale expeditorului în interval |
| Volum recent | `log(1 + suma cererilor anterioare în 300 secunde)` |
| Beneficiar nou | 1 dacă expeditorul nu l-a mai folosit, altfel 0 |
| Dispozitiv nou | 1 dacă expeditorul nu l-a mai folosit, altfel 0 |
| Autentificări eșuate | Numărul asociat cererii curente |
| Încasări recente | Numărul cererilor anterioare către expeditor în 300 secunde |

De exemplu, după cinci plăți de câte 100, o cerere de 900 are raportul 9. Pentru sume folosim logaritmul ca să reducem diferențele de scară. Etichetele de fraudă, tipurile scenariilor, soldurile și deciziile nu intră în vector.

Istoricul se actualizează **după** calcularea vectorului curent. Rândurile sunt ordonate după `(timestamp, id)`; la egalitate, ID-ul stabilește ordinea. Cererile blocate intră în istoric: analizăm tentative, nu transferuri bancare executate.

Normalizarea este `z = (x − media_referinței) / max(1, abaterea_standard_referinței)`. Pragul de 1 este o alegere explicită a acestui prototip, nu standardizarea pură cu abatere standard arbitrar de mică. Scalerul învață exclusiv din referința anterioară: 256 observații pentru MIA, 128 în experimentul anterior.

## 2. Isolation Forest

**Ideea:** o observație diferită de majoritatea se separă adesea după mai puține împărțiri aleatoare. Această idee și formula scorului provin din lucrarea [Liu, Ting și Zhou, 2008](https://doi.org/10.1109/ICDM.2008.17).

Implementarea are doi pași:

1. `fit(points)` construiește arborii. Pentru fiecare arbore extrage fără înlocuire un eșantion de 64 de observații din referință. Alege aleator o caracteristică variabilă și un prag între minim și maxim. Împarte în stânga și dreapta, apoi repetă până la un singur punct, date identice sau adâncimea maximă `ceil(log2(64)) = 6`.
2. `score(point)` traversează fiecare arbore și calculează lungimea medie a căilor. Pentru o frunză cu mai multe observații adaugă corecția `c(n)`.

```text
c(n) = 2 × H(n−1) − 2 × (n−1)/n, pentru n > 1
c(0) = c(1) = 0
H(m) = 1 + 1/2 + ... + 1/m
s(x) = 2 ^ (−media_lungimilor_căilor / c(64))
```

`average_path()` memorează valorile armonice calculate, evitând repetarea sumei la fiecare frunză. Seed-ul 42 produce aceiași arbori pentru aceeași referință și aceiași parametri.

**Exemplu conceptual:** pentru `ψ = 4`, `c(4) = 2,1667`. O cale medie 1 dă aproximativ 0,726, iar o cale medie 2 dă aproximativ 0,527. Calea mai scurtă are scor mai mare. Exemplul explică formula; nu este un rezultat măsurat pe PaySim.

În experimentul anterior semnalăm `s ≥ 0,6`; MIA selectează pragul pe validare. Arborele nu explică intenția persoanei și nu transformă scorul în probabilitate de fraudă.

## 3. DBSCAN

**Ideea:** conectează punctele care formează regiuni dense și marchează observațiile fără legătură cu acestea drept noise. Definițiile de vecinătate și conectivitate urmează [Ester și colaboratorii, 1996](https://cdn.aaai.org/KDD/1996/KDD96-037.pdf).

În `fit_predict(points)`:

1. Vecinătatea conține punctele cu distanță euclidiană `≤ ε`, inclusiv punctul însuși.
2. Un punct este **core** dacă vecinătatea are cel puțin `min_samples` observații.
3. O coadă extinde grupul prin punctele core. Punctele apropiate care nu sunt core pot intra ca **border**, fără a extinde grupul.
4. O observație care nu aparține niciunui grup rămâne **noise**, cu eticheta `−1`. Un punct marcat inițial noise poate deveni ulterior border.

**Exemplu verificabil:** `DBSCAN(0.3, 2)` pe `[0; 0,1; 4; 4,1; 20]` produce `[0; 0; 1; 1; −1]`. Primele două puncte formează un grup, următoarele două alt grup, iar 20 este izolat.

SecFlow rulează algoritmul pe **ultimele 24 de observații prin cererea curentă**, nu pe toate datele și nici pe viitor. Parametrii impliciți sunt `ε = 1,8` și `min_samples = 4`. Grupul 0 dintr-o fereastră nu este neapărat grupul 0 din următoarea. Noise contribuie la risc, dar o tranzacție izolată poate fi legitimă, iar fraude repetate pot forma un grup.

## 4. Local Outlier Factor — LOF

**Ideea:** un punct este suspect local când densitatea sa este mai mică decât a vecinilor. Definițiile de reachability distance și densitate provin din [Breunig și colaboratorii, 2000](https://sigmodrecord.org/2000/06/07/lof-identifying-density-based-local-outliers/).

Pentru fiecare punct din referință, `fit()` calculează distanțele, le sortează și reține vecinătatea celui de-al k-lea vecin. Include toate egalitățile de la limita vecinătății, deci pot exista mai mult de k vecini.

```text
reach_dist(p, o) = max(k_distance(o), distance(p, o))
lrd(p) = 1 / media(reach_dist(p, o)), pentru vecinii o
LOF(p) = media(lrd(o) / lrd(p)), pentru vecinii o
```

`k_distance(o)` este distanța de la vecinul `o` la al k-lea vecin al său. Maximul împiedică distanțele foarte mici să facă estimarea densității instabilă. Pentru distanțe medii zero folosim pragul numeric `1e−12`.

**Exemplu conceptual:** dacă densitatea tranzacției este 1, iar densitățile vecinilor sunt 2 și 2, LOF este `(2/1 + 2/1)/2 = 2`. LOF aproape de 1 indică densități asemănătoare; o valoare mare indică izolare locală.

În proiect, `k = 10` implicit. `model.scores` descrie retrospectiv punctele de referință. `model.score(x)` evaluează o observație nouă față de vecinii și densitățile fixe din referința anterioară. Platforma folosește acest al doilea mod. Pragul experimentului anterior este `LOF ≥ 1,5`; MIA selectează pragul pe validare.

## 5. Combinarea într-o decizie

În experimentul anterior, `pipeline.py` este locul care definește normalizarea scorurilor, regulile și ponderile. Replay-ul și simularea apelează aceeași metodă `DetectionModel.assess()`.

```text
IF_normalizat = limitare((IF_brut − 0,35) / 0,4 × 100, 0, 100)
LOF_normalizat = limitare((LOF_brut − 1) × 50, 0, 100)
DBSCAN_normalizat = 100 pentru noise, altfel 0

risc = rotunjire(0,30 × IF_normalizat
              + 0,25 × LOF_normalizat
              + 0,15 × DBSCAN_normalizat
              + 0,30 × reguli)
```

Regulile adaugă 40 pentru o sumă peste opt ori media proprie după cel puțin cinci cereri; 30 pentru cel puțin opt cereri precedente în cinci minute; 50 pentru dispozitiv nou și cel puțin trei autentificări eșuate; 25 pentru cel puțin trei încasări recente. Totalul regulilor este limitat la 100. Regula sumei folosește raportul din dovezi, rotunjit la două zecimale.

**Exemplu verificabil:** IF brut 0,55 → 15 puncte; LOF brut 2 → 12,5 puncte; noise → 15 puncte; reguli 50 → 15 puncte. Total 57,5, rotunjit la **58 → De verificat**. Python folosește rotunjirea la cel mai apropiat întreg par pentru egalități exacte, de exemplu 52,5 → 52.

| Scor | Decizie inițială |
|---|---|
| 0–44 | Permisă |
| 45–64 | De verificat; se deschide un caz |
| 65–100 | Blocată; se deschide un caz și se restricționează expeditorul |

Un expeditor deja blocat produce o decizie de blocare independent de scor. Această politică operațională este separată de predicția numerică evaluată. Reanalizarea adaugă evaluări, fără a rescrie deciziile inițiale sau corecțiile contului.

Ponderile și pragurile sunt alegeri demonstrative. Un semnal individual nu este același lucru cu decizia combinată. „Doar algoritmii” folosește ponderile 0,43 IF + 0,36 LOF + 0,21 DBSCAN și pragul 45, fără reguli.

## 6. Costul implementării

`n` = referință, `d` = caracteristici, `t` = arbori, `ψ` = eșantion, `w` = fereastra DBSCAN.

| Algoritm | Construire | O cerere | Memorie principală |
|---|---|---|---|
| Isolation Forest | O(t · d · ψ · log ψ) | O(t · log ψ), cu valorile c(n) memorate | O(t · ψ) |
| DBSCAN prin scanare | Nu are model persistent | O(w² · d) | O(w · d + w), fără matrice de distanțe |
| LOF cu sortare | O(n² · d + n² · log n) | O(n · d + n · log n) | O(n · d + n · k), până la O(n² + n · d) din egalități |

În replay-ul anterior: `n = 128`, `d = 9`, `ψ = 64`, `w ≤ 24`, `t = 32` implicit. În MIA folosim n=256 și t=48; ceilalți parametri rămân aceiași. De aceea nu aplicăm LOF exhaustiv sau DBSCAN global pe cele 54.520 de rânduri. Pentru fiecare sursă ajustăm modelele mici o dată și apoi parcurgem cererile.

Caracteristicile păstrează istoricul partenerilor și dispozitivelor, deci memoria întregii aplicații nu este constantă. Numărătorile și suma recentă scanează fereastra de activitate a contului; în cazul patologic cu toate cererile în cinci minute, construirea caracteristicilor poate avea cost pătratic. Setul demonstrativ și ferestrele mici fac acest compromis ușor de urmărit.

## 7. Evaluare corectă pe setul existent

Setul pregătit are **50.000 de rânduri PaySim extins + 4.520 de scenarii generate**. Importul opțional `setup_demo --legacy` folosește primele 2.000 PaySim și toate scenariile. Fiecare sursă este separată: 128 referință, 64 validare, restul test. Rândurile de referință rămân fără decizie. Simulările manuale au `truth=None` și nu intră în metrici.

`evaluation.metrics()` primește etichetele numai după calcularea scorurilor. Pentru evaluarea individuală folosim pragurile IF 0,6, LOF 1,5 și noise DBSCAN. Pentru combinație, semnal înseamnă risc ≥45, incluzând atât verificarea cât și blocarea.

- TP: fraudă semnalată; FP: tranzacție legitimă semnalată.
- FN: fraudă omisă; TN: tranzacție legitimă nesemnalată.
- Precizie = TP / (TP + FP).
- Acoperire (recall) = TP / (TP + FN).
- F1 = 2 × precizie × recall / (precizie + recall).
- Rata alarmelor false = FP / (FP + TN).

Dacă numitorul este zero, codul afișează 0. Consultă numărătorile înainte de a interpreta procentul. Pragurile replay-ului sunt fixe; setul de validare este raportat, fără ajustarea lor automată.

`manage.py benchmark` face un experiment distinct pe primele 1.200 de rânduri **PaySim original**: 200 referință, 200 validare, 800 test. Folosește suma logaritmică, cereri precedente în aceeași oră și indicatori TRANSFER/CASH_OUT. Alege pragurile pe validare, apoi raportează testul. Nu folosește dispozitivele generate sau soldurile. Măsurarea memoriei prin `tracemalloc` indică alocările Python, nu memoria RSS a procesului.

Fișierele `artifacts/latest-run.json`, `artifacts/benchmark.json` și `artifacts/dataset-validation.json` păstrează rezultatele efectiv măsurate. Nu presupunem că o combinație depășește fiecare algoritm separat. Scenariile generate sunt controlate, iar prefixul PaySim nu reprezintă o lună întreagă de plăți.

## 8. Răspunsuri scurte pentru susținere

**De ce trei algoritmi?** Privesc anomalia din perspective diferite: separare aleatoare, grupare și densitate locală. Comparăm rezultatele; nu presupunem că acordul lor confirmă o fraudă.

**Este antrenare supravegheată?** Nu. IF și LOF se ajustează pe referință fără etichete; DBSCAN grupează fără etichete. Etichetele de validare calibrează pragurile MIA; etichetele testului sunt folosite numai pentru măsurare.

**De ce normalizare?** Distanțele ar fi dominate de dimensiunile cu valori mari. Normalizarea folosește numai referința anterioară.

**Cum eviți folosirea viitorului?** Construim istoricul înainte de actualizare, ajustăm referința doar pe începutul sursei și limităm DBSCAN până la cererea curentă.

**Ce nu poate demonstra proiectul?** O anomalie nu dovedește fraudă. Scorul nu este probabilitate. Rezultatele locale și generate nu demonstrează eficacitate bancară reală.

## 9. Interpretarea verificării pe setul complet

În verificarea salvată în `artifacts/dataset-validation.json`, aceeași politică implicită a parcurs toate cele 54.520 de rânduri pregătite. Aceasta verifică funcționarea pe setul existent; nu dovedește o detecție eficientă pentru orice sursă.

| Sursă / scor combinat, test | Precizie | Acoperire | F1 | Alarme false |
|---|---:|---:|---:|---:|
| Scenarii generate | 65,4% | 88,1% | 75,1% | 7,2% |
| PaySim extins complet | 0,4% | 16,3% | 0,8% | 8,3% |

Rezultatele PaySim sunt slabe cu aceste caracteristici și praguri fixe. Nu prezentăm prototipul drept detector bancar validat. LOF individual produce multe alarme și pe scenariile generate, ceea ce arată limita unei referințe mici și fixe. Îmbunătățirea performanței ar necesita un experiment separat de selecție a caracteristicilor și pragurilor pe validare, păstrând testul final neatins. Nu ascundem rezultatele și nu reglăm pragurile pe test ca să obținem un tabel favorabil.

## 10. Execuția în fundal și estimarea din profil

Cei trei algoritmi păstrează formulele de mai sus, dar acum sunt executați de workerul `analysis_worker`. Platforma salvează o cerere și un job; workerul citește istoricul numai până la acea cerere, rulează pipeline-ul și salvează rezultatul. Numele fictive și ID-urile publice sunt exclusiv prezentare.

Prognoza din profil este o **estimare a numărului de alerte**, separată de cei trei algoritmi de anomalie. Împărțim ultimele șase ore de simulare în șase intervale și numărăm cererile cu risc actual ≥45 pentru MIA (risc inițial ≥45 în experimentul anterior). Estimarea pentru următoarea oră este media ponderată `(1×a₁ + 2×a₂ + … + 6×a₆)/21`, acordând mai multă greutate orelor recente. Nu citim etichete de fraudă sau cereri viitoare. Timp O(m), memorie O(6), pentru m cereri recente ale clientului.

Este o extrapolare simplă a ritmului alertelor, nu un model validat de probabilitate sau o predicție sigură a fraudei. Fără activitate recentă, interfața indică lipsa datelor. Se afișează numai după deschiderea profilului unui client, conform cerinței utilizatorului.
