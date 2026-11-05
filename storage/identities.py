"""Stable generated identities for SecFlow accounts and external counterparties.

Every identity here is generated. Names are plausible and varied, but they do not refer to
verified real people or businesses. Identities are derived from a fixed identity seed so
that the training corpus and the demonstration dataset share the same 400 named accounts.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

IDENTITY_SEED = 42
ACCOUNT_COUNT = 400

FIRST_NAMES = (
    "Amara", "Lukas", "Sofia", "Mateo", "Ines", "Jonas", "Leila", "Tomasz", "Hana", "Rafael",
    "Elena", "Dmitri", "Aisha", "Henrik", "Mei", "Oskar", "Priya", "Nikolai", "Chiara", "Kwame",
    "Ingrid", "Yusuf", "Clara", "Andrei", "Noor", "Felix", "Valentina", "Kenji", "Marta", "Idris",
    "Astrid", "Diego", "Zara", "Pieter", "Leona", "Arjun", "Freya", "Emre", "Beatriz", "Sven",
    "Yara", "Mihai", "Camille", "Tariq", "Greta", "Luca", "Anouk", "Samir", "Helena", "Bruno",
    "Selin", "Joaquim", "Maren", "Viktor", "Lucia", "Omar", "Elsa", "Matteo", "Rania", "Florian",
    "Nadia", "Teodor", "Ayla", "Hugo", "Magdalena", "Kofi", "Liv", "Rui", "Sakura", "Anton",
    "Dalia", "Jakob", "Irene", "Malik", "Paula", "Stefan", "Leyla", "Nils", "Carmen", "Ravi",
    "Alma", "Benedikt", "Fatima", "Gustavo", "Ilse", "Karim", "Lena", "Milan", "Olga", "Pablo",
    "Rosa", "Simon", "Tanja", "Ulrich", "Vera", "Wiktor", "Xenia", "Yannick", "Zofia", "Adrian",
    "Bianca", "Cedric", "Daniela", "Emil", "Farah", "Gabriel", "Hedda", "Ivan", "Julia", "Kasper",
    "Lina", "Marco", "Nora", "Otto", "Petra", "Quentin", "Rebecca", "Sami", "Thea", "Vincent",
)

LAST_NAMES = (
    "Okafor", "Lindqvist", "Moreau", "Novak", "Haddad", "Fischer", "Kowalski", "Rossi", "Tanaka",
    "Silva", "Petrov", "Jansen", "Mensah", "Dubois", "Nakamura", "Costa", "Andersen", "Yilmaz",
    "Hoffmann", "Popescu", "Bauer", "Esposito", "Larsen", "Nowak", "Ferreira", "Weber", "Kaya",
    "Horvath", "Schmidt", "Ivanova", "Martins", "Berg", "Rahman", "Vogel", "Romano", "Sato",
    "Kovacs", "Laurent", "Ortega", "Svensson", "Demir", "Marino", "Krause", "Lopes", "Varga",
    "Nielsen", "Chowdhury", "Wagner", "Greco", "Holm", "Aydin", "Mendes", "Keller", "Bianchi",
    "Dahl", "Mazur", "Fontaine", "Richter", "Santos", "Eriksson", "Arslan", "Conti", "Lehmann",
    "Pereira", "Moller", "Wojcik", "Bertrand", "Szabo", "Hansen", "Ricci", "Brandt", "Alves",
    "Lund", "Celik", "Gallo", "Wolff", "Ramos", "Strand", "Dumont", "Kaminski", "Vieira", "Frank",
    "Mancini", "Engel", "Toth", "Sorensen", "Rocha", "Ozturk", "Barbieri", "Zimmermann", "Nunes",
    "Lambert", "Lewandowski", "Pinto", "Hartmann", "Farouk", "Molnar", "Aksoy", "Bergstrom",
    "Achterberg", "Quist", "Ibrahim", "Castellano", "Delacroix", "Abara", "Valdivia", "Oyelaran",
)

BUSINESS_PREFIXES = (
    "Harbor Lane", "Northwind", "Bluegate", "Copperleaf", "Riverside", "Summit", "Brightwater",
    "Old Mill", "Greenfield", "Stonebridge", "Lakeside", "Cedar Point", "Silverline", "Maple Row",
    "Westbrook", "Eastgate", "Pinecrest", "Redwood", "Seabright", "Hillview", "Fairhaven", "Kestrel",
    "Ironwood", "Sunfield", "Ashford", "Moonridge", "Clearwater", "Oakmont", "Bellhaven", "Larkspur",
)

BUSINESS_KINDS = (
    ("Utilities", "utility"), ("Dental Clinic", "health"), ("Grocers", "retail"),
    ("Property Management", "housing"), ("Telecom", "utility"), ("Insurance", "finance"),
    ("Fitness Club", "leisure"), ("Bakery", "retail"), ("Auto Repair", "services"),
    ("Pharmacy", "health"), ("Books", "retail"), ("Energy", "utility"), ("Language School", "education"),
    ("Veterinary Practice", "health"), ("Hardware", "retail"), ("Travel", "leisure"),
    ("Furniture", "retail"), ("Logistics", "services"), ("Accounting", "services"), ("Cafe", "retail"),
)

COUNTRIES = ("DE", "NL", "FR", "IT", "ES", "PT", "AT", "BE", "PL", "SE", "DK", "FI", "IE", "RO", "CZ")
HOME_COUNTRY_WEIGHTS = (0.22, 0.12, 0.12, 0.09, 0.08, 0.04, 0.05, 0.05, 0.06, 0.04, 0.03, 0.03, 0.02, 0.03, 0.02)


@dataclass(frozen=True)
class AccountIdentity:
    account_id: str
    display_name: str
    account_type: str  # "personal" | "business"
    home_country: str


@dataclass(frozen=True)
class CounterpartyIdentity:
    counterparty_id: str
    display_name: str
    kind: str  # "person" | "business"
    category: str


def _unique_person_names(rng: np.random.Generator, count: int, exclude: set[str]) -> list[str]:
    names: list[str] = []
    seen = set(exclude)
    while len(names) < count:
        name = f"{FIRST_NAMES[rng.integers(len(FIRST_NAMES))]} {LAST_NAMES[rng.integers(len(LAST_NAMES))]}"
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def build_accounts(seed: int = IDENTITY_SEED, count: int = ACCOUNT_COUNT) -> list[AccountIdentity]:
    """Return `count` accounts with unique, stable display names."""
    rng = np.random.default_rng(seed)
    person_names = _unique_person_names(rng, count, exclude=set())
    accounts: list[AccountIdentity] = []
    business_count = 0
    for index in range(count):
        is_business = rng.random() < 0.14
        home = str(rng.choice(COUNTRIES, p=np.array(HOME_COUNTRY_WEIGHTS) / sum(HOME_COUNTRY_WEIGHTS)))
        if is_business:
            prefix = BUSINESS_PREFIXES[business_count % len(BUSINESS_PREFIXES)]
            label, _ = BUSINESS_KINDS[(business_count * 7 + 3) % len(BUSINESS_KINDS)]
            surname = person_names[index].split(" ", 1)[1]
            name = f"{prefix} {label}" if business_count < len(BUSINESS_PREFIXES) else f"{surname} {label}"
            suffix = 2
            base_name = name
            while name in {a.display_name for a in accounts} or name in person_names:
                name = f"{base_name} {suffix}"
                suffix += 1
            business_count += 1
        else:
            name = person_names[index]
        accounts.append(
            AccountIdentity(
                account_id=f"ACC-{index + 1:04d}",
                display_name=name,
                account_type="business" if is_business else "personal",
                home_country=home,
            )
        )
    names = [a.display_name for a in accounts]
    if len(set(names)) != len(names):  # pragma: no cover - deterministic guard
        raise RuntimeError("Generated account names are not unique")
    return accounts


def build_counterparties(
    rng: np.random.Generator,
    count: int,
    id_prefix: str,
    start_index: int,
    reserved_names: set[str],
    business_share: float = 0.55,
) -> list[CounterpartyIdentity]:
    """Generate external participants with understandable display names."""
    result: list[CounterpartyIdentity] = []
    used = set(reserved_names)
    index = start_index
    while len(result) < count:
        if rng.random() < business_share:
            prefix = BUSINESS_PREFIXES[rng.integers(len(BUSINESS_PREFIXES))]
            label, category = BUSINESS_KINDS[rng.integers(len(BUSINESS_KINDS))]
            name = f"{prefix} {label}"
            kind = "business"
        else:
            name = f"{FIRST_NAMES[rng.integers(len(FIRST_NAMES))]} {LAST_NAMES[rng.integers(len(LAST_NAMES))]}"
            kind, category = "person", "individual"
        if name in used:
            continue
        used.add(name)
        result.append(CounterpartyIdentity(f"{id_prefix}{index:05d}", name, kind, category))
        index += 1
    return result
