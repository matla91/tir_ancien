# Flintlock Range MVP

Prototype jouable en Python/Pygame d'un jeu de tir sportif à l'arme ancienne.

## Objectif du MVP

- Stand de tir simple dans une carrière de sable en forêt.
- Arme visible à droite de l'écran.
- Arme de départ : pistolet à silex de type Kentucky/Pennsylvania.
- Distances progressives : 25 m, 50 m, 75 m, 100 m, 200 m.
- Mécaniques de tir :
  - mouvement naturel de l'arme ;
  - contrôle de respiration ;
  - fatigue ;
  - délai d'allumage du silex ;
  - encrassement ;
  - rechargement ;
  - nettoyage ;
  - vent latéral simplifié ;
  - score par anneaux.
- Son de tir généré automatiquement par le code, sans fichier externe obligatoire.

## Installation

```bash
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Linux / macOS

```bash
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Contrôles

| Action | Touche |
|---|---|
| Viser | Souris |
| Tirer | Clic gauche |
| Contrôler la respiration | Espace |
| Recharger | R |
| Nettoyer le canon | C |
| Distance suivante / recommencer | Entrée |
| Quitter | Échap |

## Structure

```text
flintlock_range_mvp/
│
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── data/
│   └── weapons.json
│
├── assets/
│   ├── images/
│   │   └── weapons/
│   │       └── flintlock_basic.png
│   └── sounds/
│
└── src/
    ├── __init__.py
    ├── settings.py
    ├── utils.py
    ├── assets.py
    ├── weapons.py
    ├── target.py
    ├── effects.py
    ├── ui.py
    └── game.py
```

## Note importante

Ce MVP n'est pas encore une simulation balistique réaliste. C'est une base de jeu propre, pensée pour évoluer vers :

- un système d'argent ;
- une boutique ;
- plusieurs armes ;
- des accessoires ;
- des améliorations ;
- des cibles plus lointaines ;
- des compétitions ;
- un carnet de score ;
- des modes de difficulté.
