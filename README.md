# timbre_dl

Imprimer un timbre **La Poste « Mon Timbre en Ligne »** directement sur une **enveloppe DL** (220 × 110 mm), avec l'adresse de l'expéditeur et celle du destinataire.

## Contexte

Mon Timbre en Ligne ne propose plus l'impression directe sur enveloppe : seulement une feuille A4 (timbre forcé en position 1, en haut à gauche), une planche d'étiquettes ou une Dymo. De plus, une imprimante qui contrôle le format papier refuse d'imprimer un PDF A4 sur une enveloppe DL.

Ce projet transforme le PDF A4 téléchargé en un PDF au **format DL** :

- le timbre est détecté automatiquement sur la page A4, découpé et placé **en haut à droite** (1 cm des bords), en vectoriel et à taille réelle, ce qui garde le DataMatrix lisible ;
- **expéditeur en haut à gauche**, **destinataire en bas à droite** (recommandation La Poste) ;
- contrôles : 6 lignes maximum par adresse, 38 caractères maximum par ligne pour le destinataire, pas de chevauchement avec le timbre.

> Depuis le 16/09/2026, les timbres Mon Timbre en Ligne sont valables **6 mois**. La date limite est imprimée sur le timbre.

## Fichiers

| Fichier | Rôle |
|---|---|
| `timbre_dl.py` | Moteur + ligne de commande |
| `timbre_dl_gui.py` | Interface graphique Tkinter (aperçu en direct) |
| `requirements.txt` | Dépendances Python |

## Installation

Python 3.10+ (Tkinter est inclus avec Python sous Windows).

```powershell
python -m pip install -r requirements.txt
```

## Utilisation

### Interface graphique

```powershell
pythonw timbre_dl_gui.py
```

1. **Parcourir…** → choisir le PDF téléchargé sur Mon Timbre en Ligne (support « Feuille blanche A4 »).
2. Saisir les adresses. L'expéditeur est mémorisé dans `%USERPROFILE%\.timbre_dl.json`.
3. **Enregistrer le PDF…**, puis **Ouvrir le PDF** pour imprimer.

### Ligne de commande

```powershell
python timbre_dl.py Etiquette_Mtel.pdf --exp "Julien MATHON|1 rue X|95520 OSNY" --dest @destinataire.txt -o enveloppe.pdf
```

- Lignes d'adresse séparées par `|`, ou `@fichier.txt` (une ligne par ligne d'adresse, UTF-8).
- Sortie par défaut : `<timbre>_DL.pdf`.

## Impression

- Format papier **Enveloppe DL**, orientation **paysage**, échelle **100 % / taille réelle** (jamais « Ajuster à la page »).
- Premier essai sur une feuille découpée à 22 × 11 cm pour trouver le bon sens d'introduction de l'enveloppe.
- Utiliser une enveloppe claire : le DataMatrix doit rester net.

## Générer un exécutable Windows

```powershell
python -m pip install pyinstaller
python -m PyInstaller --onefile --windowed --name TimbreDL --collect-all pypdfium2 --collect-all pypdfium2_raw timbre_dl_gui.py
```

L'exécutable est créé dans `dist\TimbreDL.exe`. Les dossiers `build\`, `dist\` et le fichier `TimbreDL.spec` sont ignorés par git.

## Réglages

Les marges, polices et positions sont des constantes en tête de `timbre_dl.py` (`MARGE`, `EXP_SIZE`, `DEST_SIZE`, `DEST_X`, `DEST_BOTTOM`…).

## Limites

- Un seul timbre par PDF (le premier de la page).
- Enveloppe DL uniquement.
