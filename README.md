# Duplicate Finder

Application desktop Python pour charger plusieurs fichiers tabulaires, détecter les doublons sur une colonne cible et exporter les résultats.

## Fonctionnalités

- Chargement multi-fichiers
- Formats supportés : `.csv`, `.xlsx`, `.ods`
- Détection des doublons internes et externes
- Affichage de la ligne complète, du fichier source et de l'index de ligne
- Export CSV et Excel dans `output/`
- Interface PySide6 avec sélection de fichiers, progression et tableau triable

## Structure

```text
duplicate-finder/
├── src/
│   ├── main.py
│   ├── ui/
│   ├── core/
│   ├── services/
│   └── utils/
├── data/
└── output/
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Lancement

```bash
python src/main.py
```

## Utilisation

1. Sélectionner un ou plusieurs fichiers.
2. Saisir le nom de la colonne à analyser.
3. Cliquer sur `Analyser`.
4. Consulter le détail des doublons dans le tableau.
5. Exporter les résultats au format CSV ou Excel.

## Jeux de test rapides

Deux fichiers d'exemple sont fournis dans `data/` :

- `sample_internal.csv` contient des doublons internes
- `sample_external.csv` contient des doublons croisés avec le premier fichier

Colonne à tester : `email`

## Robustesse gérée

- Colonne inexistante
- Encodages CSV fréquents
- Fichiers corrompus ou non lisibles
- Formats non supportés
