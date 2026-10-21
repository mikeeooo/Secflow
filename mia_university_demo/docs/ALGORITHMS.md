# Algoritmii SecFlow, explicați pentru susținere

## 1. Isolation Forest — abatere globală

Construim 200 de arbori. Fiecare arbore alege aleator o caracteristică și un prag, împărțind datele până izolează observații. Un punct foarte neobișnuit ajunge de regulă singur după mai puține împărțiri. De exemplu, o cerere mare de la un dispozitiv nou poate fi izolată mai repede decât o plată recurentă. `max_samples=256`, `random_state=42`, `contamination='auto'`. Folosim `-score_samples`: valoare mai mare înseamnă abatere mai mare. Modelul vede numai caracteristici numerice, nu ID-uri sau etichete.

Cost intuitiv: pentru `t` arbori și `m` puncte eșantionate pe arbore, antrenarea este aproximativ `O(t·m·log m)`; evaluarea unei cereri traversează fiecare arbore, aproximativ `O(t·log m)`.

## 2. LOF cu novelty — abatere locală

LOF compară densitatea din jurul unei cereri cu densitatea vecinilor ei. Dacă 35 de vecini sunt strânși, dar cererea se află într-o zonă mult mai rară, rangul de anomalie crește. Un transfer de 500 MDL poate fi normal pentru un grup și ieșit din comun pentru altul. `novelty=True` permite evaluarea **cererilor noi**; nu evaluăm cu `score_samples` aceleași rânduri folosite la `fit`. Referința are cel mult 20.000 de rânduri de antrenare eșantionate pe zile. Folosim `-score_samples`, apoi un rang empiric din calibrare.

Cost intuitiv: căutarea celor mai apropiați vecini domină. Cu căutare exhaustivă, compararea unei cereri cu `n` puncte de referință și `d` caracteristici costă aproximativ `O(n·d)`; structurile spațiale pot ajuta pe date potrivite. De aceea mărimea referinței este limitată.

## 3. DBSCAN — gruparea comportamentului conturilor

O dată pe zi facem un rând pentru fiecare cont activ cu sumele intrate/ieșite în ultimele 24 de ore, numărul de contrapărți, raportul ieșiri/intrări și cât de repede s-a produs o ieșire după o intrare. DBSCAN unește punctele aflate la distanța `eps` de cel puțin `min_samples=10` vecini; punctele care nu intră într-un grup dens primesc eticheta `-1` (noise). `eps` este fixat din distribuția distanțelor pe zilele de validare, după scalarea învățată pe antrenare. Fiecare zi se grupează independent; numărul unui cluster nu are identitate între zile, iar DBSCAN nu are `predict` obișnuit pentru o plată nouă.

Separat de vectorul DBSCAN, căutăm în graful local cicluri de 2–4 conturi în cel mult 10 minute. Acesta este un indiciu contextual, nu dovada unui grup infracțional. Noise singur nu dovedește fraudă. Implementarea scikit-learn poate ajunge la memorie `O(n²)` în cazuri nefavorabile; fiecare lot este limitat la 2.000 de rânduri.

## 4. Caracteristici, scor și decizie

Motorul folosește numai date observate înainte de cererea curentă: numărul de încercări din 5 minute/o oră, suma ieșită deja în ultima oră, destinatari anteriori, intrări recente, dispozitiv observat înainte și vârsta contului. Pentru un cont cu prea puțin istoric, mediana de comparație vine din perioada de antrenare. Valorile puternic asimetrice sunt log-transformate; imputarea și scalarea sunt învățate doar pe antrenare.

Punctajele negative ale IF și LOF sunt transformate în percentile față de setul de calibrare: `pIF`, `pLOF` în `[0,1]`. Acestea sunt **ranguri**, nu probabilități de fraudă.

```text
M = 0,6 × pIF + 0,4 × pLOF
R = min(1, suma ponderilor regulilor activate)
S = 100 × (0,7 × M + 0,3 × R)

S < 60       → Permit
60 ≤ S < 85  → Verify
S ≥ 85       → Block
```

Regulile și ponderile demonstrative: cel puțin 5 încercări anterioare în 5 minute (`0,4`); dispozitiv nou **și** destinatar nou (`0,3`); sumă peste de 5 ori mediana personală cu cel puțin 10 plăți istorice (`0,3`); ieșire rapidă după intrări de la cel puțin 5 expeditori (`0,4`). Interfața arată codul și valoarea observată pentru fiecare regulă activă. Arborii IF și vecinii LOF nu produc o cauză sigură a fraudei; doar semnale de abatere.

## Ce spun la prezentare

„Simulez ce poate vedea un singur PSP înainte de trimiterea unei plăți. Isolation Forest găsește abateri globale, LOF le compară cu vecinii, iar DBSCAN examinează separat conturile pe ferestre zilnice. Combin rangurile cu reguli explicite și testez pe zile ulterioare folosind etichete pe care modelele nu le-au văzut. Unele plăți înșelătoare se pot confunda cu plăți legitime.”
