# Algoritmii SecFlow

Implementările sunt proprii, fără scikit-learn. Bibliotecile Django și SQLite sunt infrastructură, nu implementări ale detecției.

## Isolation Forest

Pentru fiecare arbore alegem un eșantion fără înlocuire. Alegem aleator o caracteristică ce variază și un prag între minim și maxim. Împărțim recursiv până la un singur punct, date identice sau adâncimea `ceil(log2(ψ))`. Frunzele cu mai multe puncte adaugă lungimea medie `c(n) = 2 H(n-1) - 2(n-1)/n`, unde H este suma armonică exactă.

Scorul este `2 ^ (-E[h(x)] / c(ψ))`. Căile scurte produc scoruri mai mari. Seed-ul fix face rezultatul reproductibil. Scorul nu este probabilitate de fraudă.

Implementarea scanează toate dimensiunile pentru identificarea unei separări valide. Construcția costă O(t d ψ log ψ), cu limita explicită de adâncime, și stochează O(t ψ) noduri. Evaluarea costă O(t log ψ), plus calculul c(n) din frunze (O(ψ) în versiunea fără cache). Un cache pentru c(n) este o optimizare ulterioară posibilă.

## DBSCAN

Vecinătatea unui punct conține toate punctele la distanță euclidiană <= eps, inclusiv punctul însuși. Cel puțin min_samples vecini fac punctul core. Extinderea prin coadă reunește punctele core conectate și punctele border. Un punct marcat noise poate deveni ulterior border. Noise are eticheta -1.

Timp: O(n² d). Memorie suplimentară: O(n), în afara datelor O(nd), deoarece nu stocăm matricea distanțelor. În replay, n <=24: pentru fiecare transfer se reface fereastra cauzală. Identificatorii clusterelor sunt locali ferestrei. Eticheta noise nu dovedește frauda.

## Local Outlier Factor

Calculăm distanțele față de ceilalți vecini și sortăm. Vecinătatea include toate egalitățile la distanța celui de-al k-lea vecin. Reachability distance este `max(k-distance(o), distance(p,o))`. Densitatea locală este inversul mediei acestor distanțe. LOF este media rapoartelor dintre densitatea vecinilor și densitatea punctului.

În mod retrospectiv folosim `model.scores`; pentru o observație nouă `model.score(x)` folosește numai densitățile din referința anterioară. Acestea sunt două moduri distincte. Un prag numeric de 1e-12 tratează duplicatele cu densitate teoretic infinită: duplicatele identice au LOF 1, iar un punct îndepărtat poate avea LOF foarte mare.

Fit: O(n² d + n² log n). Memorie O(nk) în cazul obișnuit, până la O(n²) dacă există foarte multe egalități. O observație nouă costă O(nd + n log n). Nu păstrăm o matrice completă de distanțe.

## Caracteristici și reguli

Caracteristicile includ suma logaritmică, raportul față de media anterioară, numărul cererilor în 60/300 secunde, suma cererilor în 300 secunde, beneficiar/dispozitiv nou, autentificări eșuate și încasări recente. Etichetele, soldurile și denumirile scenariilor nu sunt consultate. Când istoricul lipsește, raportul este neutru (1) și explicația indică istoricul insuficient.

Regulile punctează: sumă >8 ori media după minimum 5 observații, >=8 transferuri precedente în 5 minute, dispozitiv nou cu >=3 autentificări eșuate, >=3 încasări precedente în 5 minute. Ele analizează indicatori observabili, nu intenția clientului.

## Evaluare

Precision = TP/(TP+FP), recall = TP/(TP+FN), F1 = media armonică a precision și recall; rata alarmelor false = FP/(FP+TN). Numitorii zero produc 0, iar matricea completă rămâne vizibilă pentru interpretare. Evaluăm separat PaySim extins, scenariile generate și benchmarkul PaySim original.

Fraudele trimise la Review nu sunt contabilizate automat ca pierderi prevenite. Valoarea blocată este efectul simulării și trebuie comparată cu valoarea fraudelor permise și blocările legitime. Nu pretindem eficacitate bancară reală.
