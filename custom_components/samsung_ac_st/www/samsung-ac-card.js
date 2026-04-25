// Samsung AC Card v5.4.1 — titof2375
// Style : thermostat HA avec anneau SVG

const HVAC_LABELS = {
  off:      'Éteint',
  cool:     'Refroidissement',
  heat:     'Chauffage',
  auto:     'Auto',
  dry:      'Séchage',
  fan_only: 'Ventilation',
};

const HVAC_ICONS = {
  off:      'M13 3h-2v10h2V3zm4.83 2.17l-1.42 1.42C17.99 7.86 19 9.81 19 12c0 3.87-3.13 7-7 7s-7-3.13-7-7c0-2.19 1.01-4.14 2.58-5.42L6.17 5.17C4.23 6.82 3 9.26 3 12c0 4.97 4.03 9 9 9s9-4.03 9-9c0-2.74-1.23-5.18-3.17-6.83z',
  cool:     'M20 13h-3.19l2.64-2.64-1.41-1.41L14 13h-2v-2l4.05-4.05-1.41-1.41L12 8.19V5a1 1 0 0 0-2 0v3.19L7.36 5.54 5.95 6.95 10 11v2H8L3.95 8.95 2.54 10.36 5.19 13H2a1 1 0 0 0 0 2h3.19l-2.65 2.64 1.41 1.41L8 15h2v2l-4.05 4.05 1.41 1.41L10 19.81V23a1 1 0 0 0 2 0v-3.19l2.64 2.64 1.41-1.41L12 17v-2h2l4.05 4.05 1.41-1.41L16.81 15H20a1 1 0 0 0 0-2z',
  heat:     'M17.66 11.2C17.43 10.9 17.15 10.64 16.89 10.38C16.22 9.78 15.46 9.35 14.82 8.72C13.33 7.26 13 4.85 13.95 3C13 3.23 12.17 3.75 11.46 4.32C8.87 6.4 7.85 10.07 9.07 13.22C9.11 13.32 9.15 13.42 9.15 13.55C9.15 13.77 9 13.97 8.8 14.05C8.57 14.15 8.33 14.09 8.14 13.93C8.08 13.88 8.04 13.83 8 13.76C6.87 12.33 6.69 10.28 7.45 8.64C5.78 10 4.87 12.3 5 14.47C5.06 14.97 5.12 15.47 5.29 15.97C5.43 16.57 5.7 17.17 6 17.7C7.08 19.43 8.95 20.67 10.96 20.92C13.1 21.19 15.39 20.8 17.03 19.32C18.86 17.66 19.5 15 18.56 12.72L18.43 12.46C18.22 12 17.66 11.2 17.66 11.2Z',
  auto:     'M12 5C8.13 5 5 8.13 5 12s3.13 7 7 7 7-3.13 7-7-3.13-7-7-7zm0 2c1.29 0 2.48.43 3.44 1.13L6.13 15.44C5.43 14.48 5 13.29 5 12c0-2.76 2.24-5 5-5zm0 10c-1.29 0-2.48-.43-3.44-1.13l9.31-9.31C18.57 9.52 19 10.71 19 12c0 2.76-2.24 5-5 5z',
  dry:      'M12 2C9.38 2 7.25 4.13 7.25 6.75 7.25 9 9.06 11.61 12 15c2.94-3.39 4.75-6 4.75-8.25C16.75 4.13 14.62 2 12 2z',
  fan_only: 'M12 2C10.9 2 10 2.9 10 4V11.1L4.8 8.1C4.3 7.8 3.7 7.8 3.3 8.1C2.5 8.6 2.4 9.7 3 10.4L7.9 15L3 19.6C2.4 20.3 2.5 21.4 3.3 21.9C3.7 22.2 4.3 22.2 4.8 21.9L10 18.9V20C10 21.1 10.9 22 12 22C13.1 22 14 21.1 14 20V18.9L19.2 21.9C19.7 22.2 20.3 22.2 20.7 21.9C21.5 21.4 21.6 20.3 21 19.6L16.1 15L21 10.4C21.6 9.7 21.5 8.6 20.7 8.1C20.3 7.8 19.7 7.8 19.2 8.1L14 11.1V4C14 2.9 13.1 2 12 2Z',
};

const HVAC_COLORS = {
  off:      'var(--disabled-text-color, #9e9e9e)',
  cool:     '#2196f3',
  heat:     '#ff5722',
  auto:     '#4caf50',
  dry:      '#00bcd4',
  fan_only: '#9c27b0',
};

const FAN_MODES = { auto:'Auto', low:'Bas', medium:'Moyen', high:'Élevé', turbo:'Turbo' };
const SWING_MODES = { off:'Fixe', vertical:'Vertical', horizontal:'Horizontal', both:'Les deux' };
const OPTIONAL_LABELS = {
  off:'Désactivé', sleep:'Sommeil', quiet:'Silencieux',
  speed:'Turbo', windFree:"Sans courant d'air", windFreeSleep:"Sans courant d'air (nuit)",
};

// Calcul anneau SVG (270° arc, comme carte HA)
const R = 66, CX = 80, CY = 80;
const CIRC = 2 * Math.PI * R;
const ARC  = CIRC * 0.75; // 270°

function ringDash(ratio) {
  const filled = Math.max(0, Math.min(1, ratio)) * ARC;
  return `${filled} ${CIRC}`;
}

function ringOffset() {
  // offset pour commencer en bas-gauche (225°)
  return -(CIRC * (1 - 0.75) / 2 + CIRC);
}

class SamsungAcCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  setConfig(config) {
    if (!config.entity) throw new Error('"entity" requis (ex: climate.climatiseur_de_cloe)');
    this._config = config;
    this._base = config.entity.replace(/^climate\./, '');
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _eid(domain, suffix) {
    const key = suffix ? `${domain}_${suffix}` : domain;
    if (this._config[key]) return this._config[key];
    return suffix ? `${domain}.${this._base}_${suffix}` : `${domain}.${this._base}`;
  }

  _st(domain, suffix) {
    return this._hass?.states[this._eid(domain, suffix)];
  }

  _svc(domain, service, data) {
    this._hass.callService(domain, service, data);
  }

  _render() {
    if (!this._hass || !this._config) return;

    const climate = this._st('climate');
    if (!climate) {
      this.shadowRoot.innerHTML = `<ha-card style="padding:16px;color:var(--error-color)">
        Entité introuvable : ${this._eid('climate')}</ha-card>`;
      return;
    }

    const attr     = climate.attributes;
    const hvac     = climate.state;
    const isOn     = hvac !== 'off';
    const curTemp  = attr.current_temperature ?? '—';
    const tgt      = attr.temperature ?? 22;
    const minT     = attr.min_temp ?? 16;
    const maxT     = attr.max_temp ?? 30;
    const fan      = attr.fan_mode ?? 'auto';
    const swing    = attr.swing_mode ?? 'off';
    const color    = HVAC_COLORS[hvac] ?? HVAC_COLORS.off;
    const label    = HVAC_LABELS[hvac] ?? hvac;
    const name     = this._config.name || attr.friendly_name || this._base;

    // Anneau : ratio = position cible dans plage min-max
    const ratio = (tgt - minT) / (maxT - minT);
    const trackDash  = `${ARC} ${CIRC}`;
    const activeDash = ringDash(ratio);
    const offset     = ringOffset();

    // Entités optionnelles
    const modeSpecial  = this._st('select', 'mode_special');
    const ecran        = this._st('switch', 'ecran');
    const bip          = this._st('switch', 'bip');
    const nettoyage    = this._st('switch', 'nettoyage_auto');
    const humidity     = this._st('sensor', 'humidite');
    const filtreEtat   = this._st('sensor', 'filtre_etat');
    const filtreUsage  = this._st('sensor', 'filtre_usage');

    const WIND_FREE = ['windFree','windFreeSleep'];
    const COOL_MODES = ['cool','auto'];
    const optOptions = modeSpecial?.attributes?.options
      ?.filter(m => !WIND_FREE.includes(m) || COOL_MODES.includes(hvac)) ?? [];

    this.shadowRoot.innerHTML = `
<style>
  *, *::before, *::after { box-sizing: border-box; }
  ha-card { font-family: var(--primary-font-family, sans-serif); overflow: hidden; }

  /* Header */
  .card-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 14px 16px 0;
  }
  .card-title { font-size: 0.95em; font-weight: 500; color: var(--primary-text-color); }
  .card-menu  { color: var(--secondary-text-color); cursor: pointer; padding: 4px; }

  /* Anneau */
  .ring-wrap {
    display: flex; justify-content: center; align-items: center;
    padding: 8px 16px 0; position: relative;
  }
  .ring-svg { width: 160px; height: 160px; }
  .ring-center {
    position: absolute; top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    text-align: center; padding-top: 6px;
  }
  .ring-state { font-size: 0.72em; color: ${color}; margin-bottom: 2px; font-weight: 500; }
  .ring-temp  { font-size: 3em; font-weight: 200; color: var(--primary-text-color); line-height: 1; }
  .ring-unit  { font-size: 0.45em; vertical-align: super; }

  /* Contrôle température */
  .temp-ctrl {
    display: flex; align-items: center; justify-content: center;
    gap: 14px; padding: 6px 0 10px;
  }
  .temp-btn {
    width: 34px; height: 34px; border-radius: 50%; border: none;
    background: var(--secondary-background-color);
    color: var(--primary-text-color);
    font-size: 1.3em; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
  }
  .temp-btn:hover { background: var(--divider-color); }
  .temp-val { font-size: 1.1em; color: var(--primary-text-color); min-width: 70px; text-align: center; }

  .divider { border: none; border-top: 1px solid var(--divider-color); margin: 0 12px; }

  /* Boutons mode */
  .section { padding: 10px 12px 6px; }
  .sec-title { font-size: 0.68em; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px; }
  .mode-row { display: flex; gap: 4px; }
  .mode-btn {
    flex: 1; border: none; border-radius: 8px; cursor: pointer;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
    padding: 6px 2px; display: flex; flex-direction: column;
    align-items: center; gap: 3px; font-size: 0.68em;
    transition: background 0.12s, color 0.12s;
  }
  .mode-btn svg { width: 20px; height: 20px; fill: currentColor; }
  .mode-btn:hover { background: var(--divider-color); }
  .mode-btn.active { background: ${color}22; color: ${color}; }

  /* Selects */
  .selects { display: flex; gap: 8px; padding: 8px 12px; }
  .sel-wrap { flex: 1; }
  .sel-wrap label { font-size: 0.68em; color: var(--secondary-text-color); display: block; margin-bottom: 4px; }
  select {
    width: 100%; padding: 6px 8px; border-radius: 8px;
    border: 1px solid var(--divider-color);
    background: var(--secondary-background-color);
    color: var(--primary-text-color);
    font-size: 0.82em; cursor: pointer;
  }

  /* Switches */
  .switches { display: flex; gap: 6px; padding: 6px 12px 10px; }
  .sw {
    flex: 1; border-radius: 8px; cursor: pointer;
    background: var(--secondary-background-color);
    padding: 8px 4px; display: flex; flex-direction: column;
    align-items: center; gap: 3px; border: none;
    color: var(--secondary-text-color); font-size: 0.68em;
    transition: background 0.12s, color 0.12s;
  }
  .sw svg { width: 20px; height: 20px; fill: currentColor; }
  .sw.on { background: ${color}22; color: ${color}; }

  /* Capteurs */
  .sensors { display: flex; gap: 6px; padding: 6px 12px 14px; }
  .sensor { flex: 1; border-radius: 8px; background: var(--secondary-background-color); padding: 8px 6px; text-align: center; }
  .sensor-lbl { font-size: 0.65em; color: var(--secondary-text-color); }
  .sensor-val { font-size: 0.9em; font-weight: 600; color: var(--primary-text-color); margin-top: 2px; }
</style>

<ha-card>
  <div class="card-header">
    <span class="card-title">${name}</span>
    <span class="card-menu">⋮</span>
  </div>

  <!-- Anneau thermostat -->
  <div class="ring-wrap">
    <svg class="ring-svg" viewBox="0 0 160 160">
      <!-- piste -->
      <circle cx="${CX}" cy="${CY}" r="${R}" fill="none" stroke="var(--secondary-background-color)"
        stroke-width="6" stroke-dasharray="${trackDash}" stroke-dashoffset="${offset}" stroke-linecap="round"/>
      <!-- points -->
      <circle cx="${CX}" cy="${CY}" r="${R}" fill="none" stroke="var(--divider-color)"
        stroke-width="3" stroke-dasharray="2 9.5" stroke-dashoffset="${offset}"/>
      <!-- actif -->
      <circle cx="${CX}" cy="${CY}" r="${R}" fill="none" stroke="${isOn ? color : 'var(--disabled-text-color)'}"
        stroke-width="6" stroke-dasharray="${activeDash}" stroke-dashoffset="${offset}" stroke-linecap="round"/>
    </svg>
    <div class="ring-center">
      <div class="ring-state">${label}</div>
      <div class="ring-temp">${curTemp}<span class="ring-unit">°</span></div>
    </div>
  </div>

  <!-- Consigne température -->
  <div class="temp-ctrl">
    <button class="temp-btn" id="t-down">−</button>
    <span class="temp-val">${isOn ? `⊙ ${tgt} °C` : '—'}</span>
    <button class="temp-btn" id="t-up">+</button>
  </div>

  <div class="divider"></div>

  <!-- Modes ventilateur -->
  <div class="section">
    <div class="sec-title">Ventilateur</div>
    <div class="mode-row" id="fan-row">
      ${Object.entries(FAN_MODES).map(([k,v]) => `
        <button class="mode-btn ${fan===k?'active':''}" data-fan="${k}">
          <svg viewBox="0 0 24 24"><path d="M12 2C10.9 2 10 2.9 10 4V11.1L4.8 8.1C4.3 7.8 3.7 7.8 3.3 8.1C2.5 8.6 2.4 9.7 3 10.4L7.9 15L3 19.6C2.4 20.3 2.5 21.4 3.3 21.9C3.7 22.2 4.3 22.2 4.8 21.9L10 18.9V20C10 21.1 10.9 22 12 22C13.1 22 14 21.1 14 20V18.9L19.2 21.9C19.7 22.2 20.3 22.2 20.7 21.9C21.5 21.4 21.6 20.3 21 19.6L16.1 15L21 10.4C21.6 9.7 21.5 8.6 20.7 8.1C20.3 7.8 19.7 7.8 19.2 8.1L14 11.1V4C14 2.9 13.1 2 12 2Z"/></svg>
          ${v}
        </button>`).join('')}
    </div>
  </div>

  <!-- Modes HVAC -->
  <div class="section">
    <div class="sec-title">Mode</div>
    <div class="mode-row" id="hvac-row">
      ${Object.entries(HVAC_ICONS).map(([k,p]) => `
        <button class="mode-btn ${hvac===k?'active':''}" data-hvac="${k}">
          <svg viewBox="0 0 24 24"><path d="${p}"/></svg>
          ${HVAC_LABELS[k]}
        </button>`).join('')}
    </div>
  </div>

  <div class="divider"></div>

  <!-- Oscillation + Mode spécial -->
  <div class="selects">
    <div class="sel-wrap">
      <label>Oscillation</label>
      <select id="swing-sel">
        ${Object.entries(SWING_MODES).map(([k,v])=>`<option value="${k}" ${swing===k?'selected':''}>${v}</option>`).join('')}
      </select>
    </div>
    ${optOptions.length ? `
    <div class="sel-wrap">
      <label>Mode spécial</label>
      <select id="opt-sel">
        ${optOptions.map(m=>`<option value="${m}" ${modeSpecial?.state===m?'selected':''}>${OPTIONAL_LABELS[m]??m}</option>`).join('')}
      </select>
    </div>` : ''}
  </div>

  ${(ecran||bip||nettoyage) ? `
  <div class="divider"></div>
  <div class="switches">
    ${ecran ? `<button class="sw ${ecran.state==='on'?'on':''}" id="sw-ecran">
      <svg viewBox="0 0 24 24"><path d="M21 3H3c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h5v2h8v-2h5c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 14H3V5h18v12z"/></svg>
      Écran</button>` : ''}
    ${bip ? `<button class="sw ${bip.state==='on'?'on':''}" id="sw-bip">
      <svg viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/></svg>
      Bip</button>` : ''}
    ${nettoyage ? `<button class="sw ${nettoyage.state==='on'?'on':''}" id="sw-nett">
      <svg viewBox="0 0 24 24"><path d="M19.36 2.72L20.78 4.14L15.06 9.85C15.66 10.71 16 11.71 16 12.75C16 14.07 15.47 15.33 14.54 16.27L9 22.5L5.5 19L4.5 20H2V17.5L3 16.5L.5 14L6.73 8.46C7.67 7.53 8.93 7 10.25 7C11.28 7 12.29 7.34 13.15 7.94L19.36 2.72Z"/></svg>
      Nettoyage</button>` : ''}
  </div>` : ''}

  ${(humidity||filtreEtat||filtreUsage) ? `
  <div class="divider"></div>
  <div class="sensors">
    ${humidity ? `<div class="sensor">
      <div class="sensor-lbl">💧 Humidité</div>
      <div class="sensor-val">${humidity.state} %</div>
    </div>` : ''}
    ${filtreEtat ? `<div class="sensor">
      <div class="sensor-lbl">🔧 Filtre</div>
      <div class="sensor-val">${filtreEtat.state}</div>
    </div>` : ''}
    ${filtreUsage ? `<div class="sensor">
      <div class="sensor-lbl">📊 Usure</div>
      <div class="sensor-val">${filtreUsage.state} %</div>
    </div>` : ''}
  </div>` : ''}

</ha-card>`;

    // — Événements —
    const eid = this._eid('climate');

    this.shadowRoot.getElementById('t-up')?.addEventListener('click', () =>
      this._svc('climate','set_temperature',{entity_id:eid, temperature: tgt+1}));

    this.shadowRoot.getElementById('t-down')?.addEventListener('click', () =>
      this._svc('climate','set_temperature',{entity_id:eid, temperature: tgt-1}));

    this.shadowRoot.querySelectorAll('[data-hvac]').forEach(b => b.addEventListener('click', () => {
      const m = b.dataset.hvac;
      this._svc('climate', m==='off'?'turn_off':'set_hvac_mode', m==='off'?{entity_id:eid}:{entity_id:eid, hvac_mode:m});
    }));

    this.shadowRoot.querySelectorAll('[data-fan]').forEach(b => b.addEventListener('click', () =>
      this._svc('climate','set_fan_mode',{entity_id:eid, fan_mode:b.dataset.fan})));

    this.shadowRoot.getElementById('swing-sel')?.addEventListener('change', e =>
      this._svc('climate','set_swing_mode',{entity_id:eid, swing_mode:e.target.value}));

    this.shadowRoot.getElementById('opt-sel')?.addEventListener('change', e =>
      this._svc('select','select_option',{entity_id:this._eid('select','mode_special'), option: OPTIONAL_LABELS[e.target.value]??e.target.value}));

    this.shadowRoot.getElementById('sw-ecran')?.addEventListener('click', () =>
      this._svc('switch', ecran.state==='on'?'turn_off':'turn_on', {entity_id:this._eid('switch','ecran')}));

    this.shadowRoot.getElementById('sw-bip')?.addEventListener('click', () =>
      this._svc('switch', bip.state==='on'?'turn_off':'turn_on', {entity_id:this._eid('switch','bip')}));

    this.shadowRoot.getElementById('sw-nett')?.addEventListener('click', () =>
      this._svc('switch', nettoyage.state==='on'?'turn_off':'turn_on', {entity_id:this._eid('switch','nettoyage_auto')}));
  }

  getCardSize() { return 7; }

  static getStubConfig() { return { entity: 'climate.climatiseur' }; }
}

customElements.define('samsung-ac-card', SamsungAcCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: 'samsung-ac-card',
  name: 'Samsung AC Card',
  description: 'Contrôle complet climatiseur Samsung Wind-Free (SmartThings)',
  preview: false,
});
