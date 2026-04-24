# Samsung AC Beep & Display — Intégration HACS

Contrôlez le **bip sonore** et l'**écran d'affichage** de vos climatiseurs Samsung depuis Home Assistant, via l'API SmartThings.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

---

## Fonctionnalités

Pour chaque climatiseur Samsung détecté dans SmartThings, l'intégration crée **2 switchs** :

| Entité | Icône | Description |
|--------|-------|-------------|
| `switch.XXX_ecran` | 📺 | Allume/éteint l'affichage de la télécommande murale |
| `switch.XXX_bip` | 🔊 | Active/désactive le bip à chaque changement de consigne |

---

## Prérequis

- Home Assistant **2024.1+**
- HACS installé
- Climatiseur(s) Samsung connecté(s) à **SmartThings**
- Un **Personal Access Token** SmartThings

---

## Installation via HACS

1. Ouvrez HACS → **Intégrations** → Menu (⋮) → **Dépôts personnalisés**
2. Ajoutez l'URL : `https://github.com/christophe-havard/samsung_ac_beep_display`  
   Catégorie : **Intégration**
3. Cherchez **Samsung AC Beep & Display** → **Télécharger**
4. Redémarrez Home Assistant

---

## Configuration

### 1. Créer un Token SmartThings

1. Allez sur [account.smartthings.com/tokens](https://account.smartthings.com/tokens)
2. Cliquez **Generate new token**
3. Donnez un nom (ex: `home-assistant`)
4. Cochez les scopes : **Devices (list, read, execute)**
5. Copiez le token généré

### 2. Ajouter l'intégration dans HA

1. **Paramètres** → **Appareils & Services** → **Ajouter une intégration**
2. Cherchez **Samsung AC Beep & Display**
3. Collez votre token SmartThings
4. Validez — vos climatiseurs apparaissent automatiquement

---

## Utilisation

### Couper le bip et l'écran automatiquement (Automation)

```yaml
alias: "Samsung AC — Couper bip et écran la nuit"
trigger:
  - platform: time
    at: "22:00:00"
action:
  - service: switch.turn_off
    target:
      entity_id:
        - switch.parental_bip
        - switch.parental_ecran
        - switch.cloe_bip
        - switch.cloe_ecran
        - switch.clement_bip
        - switch.clement_ecran
```

---

## Notes techniques

La commande utilise la capability OCF `execute` de SmartThings avec l'option propriétaire Samsung :

```json
{
  "commands": [{
    "component": "main",
    "capability": "execute",
    "command": "execute",
    "arguments": ["mode/vs/0", {"x.com.samsung.da.options": ["Light_On"]}]
  }]
}
```

> ⚠️ Attention : le nommage Samsung est inversé — `Light_On` éteint l'écran, `Light_Off` l'allume.

---

## Compatibilité

Testé sur climatiseurs Samsung **Wind-Free** (protocole NASA via SmartThings).  
Devrait fonctionner sur tout modèle Samsung connecté à SmartThings.

---

## Licence

MIT
