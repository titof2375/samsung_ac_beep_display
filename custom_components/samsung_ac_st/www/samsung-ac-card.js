// Samsung AC Card — Carte Lovelace personnalisée
// Intégration Samsung AC SmartThings (titof2375)

const HVAC_MODES = {
  off:      { label: 'Éteint',        icon: 'mdi:power',             color: '#9e9e9e' },
  cool:     { label: 'Refroidissement', icon: 'mdi:snowflake',       color: '#2196f3' },
  heat:     { label: 'Chauffage',     icon: 'mdi:fire',              color: '#ff5722' },
  auto:     { label: 'Auto',          icon: 'mdi:autorenew',         color: '#4caf50' },
  dry:      { label: 'Séchage',       icon: 'mdi:water-percent',     color: '#00bcd4' },
  fan_only: { label: 'Purifier',      icon: 'mdi:fan',               color: '#9c27b0' },
};

const FAN_MODES = {
  auto:   'Auto',
  low:    'Bas',
  medium: 'Moyen',
  high:   'Élevé',
  turbo:  'Turbo',
};

const SWING_MODES = {
  off:        'Arrêt',
  vertical:   'Vertical',
  horizontal: 'Horizontal',
  both:       'Les deux',
};

const OPTIONAL_MODES = {
  off:           'Désactivé',
  windFree:      'Sans courant d\'air',
  windFreeSleep: 'Sans courant d\'air (nuit)',
  sleep:         'Sommeil',
  quiet:         'Silencieux',
  speed:         'Turbo',
};

const FILTER_STATUS = {
  normal:  '✅ Normal',
  wash:    '⚠️ À laver',
  replace: '🔴 À remplacer',
};

class SamsungAcCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  setConfig(config) {
    if (!config.entity) throw new Error('Propriété "entity" requise (ex: climate.climatiseur_de_cloe)');
    this._config = config;
    this._base = config.entity.replace('climate.', '');
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _eid(domain, suffix) {
    return this._config[`${domain}_${suffix}`] || `${domain}.${this._base}${suffix ? '_' + suffix : ''}`;
  }

  _state(domain, suffix) {
    const id = this._eid(domain, suffix);
    return this._hass?.states[id];
  }

  _call(domain, service, data) {
    this._hass.callService(domain, service, data);
  }

  _render() {
    if (!this._hass || !this._config) return;

    const climate = this._state('climate', '');
    if (!climate) {
      this.shadowRoot.innerHTML = `<ha-card><div style="padding:16px;color:var(--error-color)">Entité introuvable : ${this._eid('climate', '')}</div></ha-card>`;
      return;
    }

    const attr = climate.attributes;
    const hvacMode = climate.state;
    const isOn = hvacMode !== 'off';
    const currentTemp = attr.current_temperature ?? '—';
    const targetTemp = attr.temperature ?? 20;
    const fanMode = attr.fan_mode ?? 'auto';
    const swingMode = attr.swing_mode ?? 'off';
    const modeColor = HVAC_MODES[hvacMode]?.color ?? '#9e9e9e';

    const ecran   = this._state('switch', 'ecran');
    const bip     = this._state('switch', 'bip');
    const nettoyage = this._state('switch', 'nettoyage_auto');
    const modeSpecial = this._state('select', 'mode_special');
    const humidity = this._state('sensor', 'humidite');
    const filtreStatut = this._state('sensor', 'filtre_statut');
    const filtreUsage  = this._state('sensor', 'filtre_usage');

    const name = this._config.name || attr.friendly_name || this._base;

    // Modes spéciaux disponibles
    const coolModes = ['cool', 'auto'];
    const windFreeModes = ['windFree', 'windFreeSleep'];
    const supportedOptional = modeSpecial?.attributes?.options ?? Object.keys(OPTIONAL_MODES);
    const filteredOptional = supportedOptional.filter(m =>
      !windFreeModes.includes(m) || coolModes.includes(hvacMode)
    );

    this.shadowRoot.innerHTML = `
      <style>
        ha-card {
          background: var(--ha-card-background, var(--card-background-color, white));
          border-radius: var(--ha-card-border-radius, 12px);
          overflow: hidden;
          font-family: var(--primary-font-family, sans-serif);
        }
        .header {
          background: ${modeColor};
          padding: 16px;
          color: white;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }
        .header .name { font-size: 1.1em; font-weight: 500; }
        .header .current-temp { font-size: 2.5em; font-weight: 300; }
        .power-btn {
          background: rgba(255,255,255,0.2);
          border: 2px solid white;
          border-radius: 50%;
          width: 40px; height: 40px;
          color: white; cursor: pointer;
          font-size: 1.2em; display: flex;
          align-items: center; justify-content: center;
        }
        .power-btn:hover { background: rgba(255,255,255,0.3); }
        .target-row {
          display: flex; align-items: center;
          justify-content: center; padding: 12px 16px;
          gap: 16px; background: ${modeColor}22;
        }
        .temp-btn {
          background: ${modeColor};
          color: white; border: none;
          border-radius: 50%; width: 36px; height: 36px;
          font-size: 1.4em; cursor: pointer;
          display: flex; align-items: center; justify-content: center;
        }
        .temp-btn:hover { opacity: 0.85; }
        .target-temp { font-size: 2em; font-weight: 500; color: ${modeColor}; min-width: 80px; text-align: center; }
        .section { padding: 12px 16px; }
        .section-title { font-size: 0.75em; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
        .mode-grid { display: flex; gap: 6px; flex-wrap: wrap; }
        .mode-btn {
          flex: 1; min-width: 70px;
          padding: 8px 4px; border: 2px solid transparent;
          border-radius: 8px; cursor: pointer;
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
          font-size: 0.8em; text-align: center;
          transition: all 0.15s;
        }
        .mode-btn.active { border-color: ${modeColor}; background: ${modeColor}22; color: ${modeColor}; font-weight: 600; }
        .mode-btn .icon { font-size: 1.3em; display: block; margin-bottom: 2px; }
        .row { display: flex; gap: 8px; }
        .select-wrap { flex: 1; }
        .select-wrap label { font-size: 0.75em; color: var(--secondary-text-color); display: block; margin-bottom: 4px; }
        select {
          width: 100%; padding: 6px 8px;
          border-radius: 6px; border: 1px solid var(--divider-color);
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
          font-size: 0.9em; cursor: pointer;
        }
        .divider { border: none; border-top: 1px solid var(--divider-color); margin: 0; }
        .switches { display: flex; gap: 8px; flex-wrap: wrap; padding: 12px 16px; }
        .switch-item {
          flex: 1; min-width: 80px;
          display: flex; flex-direction: column;
          align-items: center; gap: 4px;
          padding: 10px; border-radius: 8px;
          background: var(--secondary-background-color);
          cursor: pointer; transition: background 0.15s;
        }
        .switch-item.on { background: ${modeColor}22; }
        .switch-item .sw-icon { font-size: 1.4em; }
        .switch-item .sw-label { font-size: 0.72em; color: var(--secondary-text-color); text-align: center; }
        .switch-item .sw-state { font-size: 0.75em; font-weight: 600; }
        .switch-item.on .sw-state { color: ${modeColor}; }
        .sensors { display: flex; gap: 8px; padding: 8px 16px 16px; flex-wrap: wrap; }
        .sensor-item {
          flex: 1; padding: 8px 10px;
          border-radius: 8px;
          background: var(--secondary-background-color);
          font-size: 0.82em;
        }
        .sensor-label { color: var(--secondary-text-color); margin-bottom: 2px; }
        .sensor-value { font-weight: 600; }
      </style>

      <ha-card>
        <!-- Header -->
        <div class="header">
          <div>
            <div class="name">${name}</div>
            <div class="current-temp">${currentTemp}°</div>
          </div>
          <button class="power-btn" id="power-btn">⏻</button>
        </div>

        <!-- Température cible -->
        ${isOn ? `
        <div class="target-row">
          <button class="temp-btn" id="temp-down">−</button>
          <div class="target-temp">${targetTemp}°C</div>
          <button class="temp-btn" id="temp-up">+</button>
        </div>` : ''}

        <!-- Modes HVAC -->
        <div class="section">
          <div class="section-title">Mode</div>
          <div class="mode-grid">
            ${Object.entries(HVAC_MODES).map(([mode, info]) => `
              <button class="mode-btn ${hvacMode === mode ? 'active' : ''}" data-mode="${mode}">
                <span class="icon">${mode === 'off' ? '⏻' : mode === 'cool' ? '❄️' : mode === 'heat' ? '🔥' : mode === 'auto' ? '🔄' : mode === 'dry' ? '💧' : '💨'}</span>
                ${info.label}
              </button>
            `).join('')}
          </div>
        </div>

        ${isOn ? `
        <hr class="divider">

        <!-- Ventilateur & Oscillation -->
        <div class="section">
          <div class="row">
            <div class="select-wrap">
              <label>Ventilateur</label>
              <select id="fan-select">
                ${Object.entries(FAN_MODES).map(([k, v]) => `<option value="${k}" ${fanMode === k ? 'selected' : ''}>${v}</option>`).join('')}
              </select>
            </div>
            <div class="select-wrap">
              <label>Oscillation</label>
              <select id="swing-select">
                ${Object.entries(SWING_MODES).map(([k, v]) => `<option value="${k}" ${swingMode === k ? 'selected' : ''}>${v}</option>`).join('')}
              </select>
            </div>
          </div>
        </div>

        <!-- Mode spécial -->
        ${modeSpecial ? `
        <hr class="divider">
        <div class="section">
          <div class="section-title">Mode spécial</div>
          <select id="optional-select">
            ${filteredOptional.map(m => `<option value="${m}" ${modeSpecial.state === m ? 'selected' : ''}>${OPTIONAL_MODES[m] ?? m}</option>`).join('')}
          </select>
        </div>` : ''}

        <hr class="divider">

        <!-- Switches -->
        <div class="switches">
          ${ecran ? `<div class="switch-item ${ecran.state === 'on' ? 'on' : ''}" id="sw-ecran">
            <span class="sw-icon">📺</span>
            <span class="sw-label">Écran</span>
            <span class="sw-state">${ecran.state === 'on' ? 'Allumé' : 'Éteint'}</span>
          </div>` : ''}
          ${bip ? `<div class="switch-item ${bip.state === 'on' ? 'on' : ''}" id="sw-bip">
            <span class="sw-icon">🔊</span>
            <span class="sw-label">Bip sonore</span>
            <span class="sw-state">${bip.state === 'on' ? 'Activé' : 'Désactivé'}</span>
          </div>` : ''}
          ${nettoyage ? `<div class="switch-item ${nettoyage.state === 'on' ? 'on' : ''}" id="sw-nettoyage">
            <span class="sw-icon">🧹</span>
            <span class="sw-label">Nettoyage auto</span>
            <span class="sw-state">${nettoyage.state === 'on' ? 'Activé' : 'Désactivé'}</span>
          </div>` : ''}
        </div>` : ''}

        <!-- Capteurs -->
        ${(humidity || filtreStatut || filtreUsage) ? `
        <hr class="divider">
        <div class="sensors">
          ${humidity ? `<div class="sensor-item">
            <div class="sensor-label">💧 Humidité</div>
            <div class="sensor-value">${humidity.state} %</div>
          </div>` : ''}
          ${filtreStatut ? `<div class="sensor-item">
            <div class="sensor-label">🔧 État filtre</div>
            <div class="sensor-value">${FILTER_STATUS[filtreStatut.state] ?? filtreStatut.state}</div>
          </div>` : ''}
          ${filtreUsage ? `<div class="sensor-item">
            <div class="sensor-label">📊 Usure filtre</div>
            <div class="sensor-value">${filtreUsage.state} %</div>
          </div>` : ''}
        </div>` : ''}
      </ha-card>
    `;

    // Events
    this.shadowRoot.getElementById('power-btn')?.addEventListener('click', () => {
      this._call('climate', isOn ? 'turn_off' : 'turn_on', { entity_id: this._eid('climate', '') });
    });

    this.shadowRoot.getElementById('temp-up')?.addEventListener('click', () => {
      this._call('climate', 'set_temperature', { entity_id: this._eid('climate', ''), temperature: targetTemp + 1 });
    });

    this.shadowRoot.getElementById('temp-down')?.addEventListener('click', () => {
      this._call('climate', 'set_temperature', { entity_id: this._eid('climate', ''), temperature: targetTemp - 1 });
    });

    this.shadowRoot.querySelectorAll('.mode-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const mode = btn.dataset.mode;
        if (mode === 'off') {
          this._call('climate', 'turn_off', { entity_id: this._eid('climate', '') });
        } else {
          this._call('climate', 'set_hvac_mode', { entity_id: this._eid('climate', ''), hvac_mode: mode });
        }
      });
    });

    this.shadowRoot.getElementById('fan-select')?.addEventListener('change', e => {
      this._call('climate', 'set_fan_mode', { entity_id: this._eid('climate', ''), fan_mode: e.target.value });
    });

    this.shadowRoot.getElementById('swing-select')?.addEventListener('change', e => {
      this._call('climate', 'set_swing_mode', { entity_id: this._eid('climate', ''), swing_mode: e.target.value });
    });

    this.shadowRoot.getElementById('optional-select')?.addEventListener('change', e => {
      this._call('select', 'select_option', { entity_id: this._eid('select', 'mode_special'), option: OPTIONAL_MODES[e.target.value] ?? e.target.value });
    });

    this.shadowRoot.getElementById('sw-ecran')?.addEventListener('click', () => {
      this._call('switch', ecran.state === 'on' ? 'turn_off' : 'turn_on', { entity_id: this._eid('switch', 'ecran') });
    });

    this.shadowRoot.getElementById('sw-bip')?.addEventListener('click', () => {
      this._call('switch', bip.state === 'on' ? 'turn_off' : 'turn_on', { entity_id: this._eid('switch', 'bip') });
    });

    this.shadowRoot.getElementById('sw-nettoyage')?.addEventListener('click', () => {
      this._call('switch', nettoyage.state === 'on' ? 'turn_off' : 'turn_on', { entity_id: this._eid('switch', 'nettoyage_auto') });
    });
  }

  getCardSize() { return 6; }

  static getConfigElement() {
    return document.createElement('samsung-ac-card-editor');
  }

  static getStubConfig() {
    return { entity: 'climate.climatiseur' };
  }
}

customElements.define('samsung-ac-card', SamsungAcCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: 'samsung-ac-card',
  name: 'Samsung AC Card',
  description: 'Contrôle complet climatiseur Samsung (SmartThings)',
  preview: true,
});
