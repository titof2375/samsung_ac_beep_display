# Samsung AC SmartThings — Intégration HACS complète

Contrôlez **complètement** vos climatiseurs Samsung depuis Home Assistant via l'API SmartThings.  
Remplace ESPHome + l'intégration SmartThings native, avec en **bonus** le contrôle du bip et de l'écran.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

---

## Entités créées par climatiseur

| Type | Entité | Description |
|------|--------|-------------|
| 🌡️ Climate | `climate.XXX` | On/Off, température, mode, ventilateur, swing |
| 📺 Switch | `switch.XXX_ecran` | Allume/éteint l'écran de la console murale |
| 🔊 Switch | `switch.XXX_bip` | Active/désactive le bip sonore |
| 💧 Sensor | `sensor.XXX_humidite` | Humidité de la pièce (%) |

---

## Modes supportés

| Mode HA | Mode Samsung |
|---------|-------------|
| Froid (`cool`) | cool |
| Chaud (`heat`) | heat |
| Auto | auto |
| Ventilation (`fan_only`) | wind |
| Déshumidification (`dry`) | dry |
| Éteint (`off`) | — |

**Vitesses ventilateur** : auto, low, medium, high, turbo  
**Swing** : off, vertical, horizontal, both

---

## Installation

### 1. Créer un Token SmartThings

1. Allez sur [account.smartthings.com/tokens](https://account.smartthings.com/tokens)
2. **Generate new token** → nom : `home-assistant`
3. Cochez : **Devices** (list, read, execute)
4. Copiez le token

### 2. Installer via HACS

1. HACS → Intégrations → `⋮` → **Dépôts personnalisés**
2. URL : `https://github.com/titof2375/samsung_ac_beep_display`  
   Catégorie : **Intégration**
3. Cherchez **Samsung AC SmartThings** → Télécharger
4. Redémarrez Home Assistant

### 3. Configurer

**Paramètres** → **Appareils & Services** → **Ajouter une intégration** → **Samsung AC SmartThings** → collez votre token.

---

## Notes techniques

- Polling SmartThings toutes les **30 secondes**
- Bip/Écran via capability OCF `execute` (`x.com.samsung.da.options`)
- Testé sur Samsung Wind-Free (protocole NASA)
