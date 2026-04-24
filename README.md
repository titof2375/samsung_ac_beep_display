# Samsung AC SmartThings — Intégration HACS

Contrôlez **complètement** vos climatiseurs Samsung depuis Home Assistant via l'API SmartThings.  
Remplace ESPHome + l'intégration SmartThings native, avec en **bonus** le contrôle du bip et de l'écran.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![version](https://img.shields.io/github/v/release/titof2375/samsung_ac_beep_display)](https://github.com/titof2375/samsung_ac_beep_display/releases)

---

## Fonctionnalités

- ✅ Contrôle complet : on/off, température, mode, ventilateur, swing
- ✅ **Écran** de la console murale (allumer/éteindre)
- ✅ **Bip sonore** (activer/désactiver)
- ✅ **Mode sans courant d'air** (Wind-Free) + Sommeil, Silencieux, Turbo
- ✅ **Nettoyage automatique** (auto-cleaning)
- ✅ Capteurs : humidité, état du filtre, usure du filtre
- ✅ Token personnel SmartThings (PAT) — pas d'expiration
- ✅ Polling toutes les 30 secondes

---

## Entités créées par climatiseur

| Type | Entité | Description |
|------|--------|-------------|
| 🌡️ Climate | `climate.NOM` | On/Off, température, mode, ventilateur, oscillation |
| 📺 Switch | `switch.NOM_ecran` | Allume/éteint l'écran de la console murale |
| 🔊 Switch | `switch.NOM_bip` | Active/désactive le bip sonore |
| 🧹 Switch | `switch.NOM_nettoyage_auto` | Active le nettoyage automatique |
| 🌀 Select | `select.NOM_mode_special` | Sans courant d'air, Sommeil, Silencieux, Turbo |
| 💧 Sensor | `sensor.NOM_humidite` | Humidité de la pièce (%) |
| 🔧 Sensor | `sensor.NOM_filtre_statut` | État du filtre (normal / laver / remplacer) |
| 📊 Sensor | `sensor.NOM_filtre_usage` | Usure du filtre (%) |

---

## Modes supportés

### Modes HVAC

| Affiché dans HA | Mode SmartThings | Description |
|----------------|-----------------|-------------|
| Froid | `cool` | Refroidissement |
| Chaud | `heat` | Chauffage |
| Auto | `auto` | Automatique |
| Ventilation | `wind` | Purifier (sans température) |
| Déshumidification | `dry` | Séchage |
| Éteint | — | Climatiseur arrêté |

### Modes spéciaux (Wind-Free)

| Affiché dans HA | Mode SmartThings | Disponible en |
|----------------|-----------------|---------------|
| Désactivé | `off` | Tous les modes |
| Sans courant d'air | `windFree` | ❄️ Froid / Auto uniquement |
| Sans courant d'air (nuit) | `windFreeSleep` | ❄️ Froid / Auto uniquement |
| Sommeil | `sleep` | Tous les modes |
| Silencieux | `quiet` | Tous les modes |
| Turbo | `speed` | Tous les modes |

> ℹ️ **Sans courant d'air** ferme les volets de soufflage et diffuse l'air via les micro-perforations de la façade. Disponible uniquement en mode refroidissement.

### Vitesses ventilateur

`Auto` · `Bas` · `Moyen` · `Élevé` · `Turbo`

### Oscillation (swing)

`Arrêt` · `Vertical` · `Horizontal` · `Les deux`

---

## Installation

### 1. Créer un Token Personnel SmartThings (PAT)

1. Allez sur [account.smartthings.com/tokens](https://account.smartthings.com/tokens)
2. Cliquez **Générer un nouveau jeton**
3. Donnez-lui un nom : `HomeAssistant`
4. Cochez au minimum :
   - `r:devices:*` (lire les appareils)
   - `x:devices:*` (exécuter des commandes)
   - `l:devices` (lister les appareils)
5. Copiez le token généré (il n'est affiché qu'une seule fois !)

> ✅ Le token personnel SmartThings **n'expire pas** tant que vous ne le supprimez pas.

### 2. Installer via HACS

1. Dans HA, allez dans **HACS** → **Intégrations**
2. Cliquez sur `⋮` → **Dépôts personnalisés**
3. Ajoutez : `https://github.com/titof2375/samsung_ac_beep_display`  
   Catégorie : **Intégration**
4. Cherchez **Samsung AC SmartThings** → **Télécharger**
5. Redémarrez Home Assistant

### 3. Configurer l'intégration

1. **Paramètres** → **Appareils & Services**
2. **+ Ajouter une intégration** → cherchez **Samsung AC SmartThings**
3. Collez votre token personnel SmartThings
4. ✅ Vos climatiseurs apparaissent automatiquement !

---

## Cartes Lovelace

Des cartes prêtes à l'emploi sont disponibles dans le dossier [`lovelace/`](./lovelace/) :

- **`card_samsung_ac.yaml`** — Carte générique pour 1 climatiseur
- **`dashboard_3_clims.yaml`** — Dashboard complet pour 3 climatiseurs

### Ajouter une carte

1. **Tableau de bord** → **Modifier** → **Ajouter une carte** → **Manuel**
2. Copiez le contenu de `card_samsung_ac.yaml`
3. Remplacez `NOM_CLIM` par le nom de votre climatiseur (ex: `climatiseur_de_cloe`)

---

## Notes techniques

- Polling SmartThings toutes les **30 secondes**
- Bip et écran contrôlés via la capability OCF `execute` (`x.com.samsung.da.options`)
  - Écran éteint : `Light_On` · Écran allumé : `Light_Off` *(nommage inversé Samsung)*
  - Bip désactivé : `Volume_Mute` · Bip activé : `Volume_100`
- Testé sur **Samsung Wind-Free** (modèles avec micro-perforations)
- Compatible Home Assistant **2024.1.0** et supérieur

---

## Auteur

[@titof2375](https://github.com/titof2375)  
[Signaler un problème](https://github.com/titof2375/samsung_ac_beep_display/issues)
