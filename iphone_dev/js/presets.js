// presets.js — Definition of HS-MN-Bricks Material Presets and parameters.inp parser/serializer

export const PARAM_DEFINITIONS = [
  { id: "E50", name: "E₅₀ʳᵉᶠ", desc: "Modulo secante a pref (taglio primario triassiale)", unit: "kPa", default: 8500.0, step: 100, min: 10, max: 1000000, category: "stiffness" },
  { id: "Eoed", name: "EₒₑᏧʳᵉᶠ", desc: "Modulo edometrico tangente a pref (carico primario)", unit: "kPa", default: 6150.0, step: 100, min: 10, max: 1000000, category: "stiffness" },
  { id: "Eur", name: "Eᵤᵣʳᵉᶠ", desc: "Modulo di scarico-ricarico a pref", unit: "kPa", default: 25750.0, step: 100, min: 50, max: 3000000, category: "stiffness" },
  { id: "m", name: "m", desc: "Esponente della dipendenza dallo stato tensionale", unit: "-", default: 0.70, step: 0.01, min: 0.2, max: 1.2, category: "stiffness" },
  { id: "c", name: "c'", desc: "Coesione efficace del terreno", unit: "kPa", default: 6.0, step: 0.5, min: 0.0, max: 500, category: "strength" },
  { id: "phi", name: "φ'", desc: "Angolo di attrito efficace (Matsuoka-Nakai)", unit: "°", default: 28.0, step: 0.5, min: 10.0, max: 55.0, category: "strength" },
  { id: "psi", name: "ψ", desc: "Angolo di dilatanza", unit: "°", default: 6.0, step: 0.5, min: 0.0, max: 35.0, category: "strength" },
  { id: "nu", name: "νᵤᵣ", desc: "Coefficiente di Poisson elastico scarico/ricarico", unit: "-", default: 0.29, step: 0.01, min: 0.05, max: 0.49, category: "stiffness" },
  { id: "pref", name: "pʳᵉᶠ", desc: "Pressione di riferimento di laboratorio", unit: "kPa", default: 100.0, step: 10, min: 10, max: 1000, category: "cap" },
  { id: "K0nc", name: "K₀ⁿᶜ", desc: "Coefficiente di spinta a riposo normalmente consolidato", unit: "-", default: 0.80, step: 0.01, min: 0.2, max: 1.2, category: "cap" },
  { id: "Rf", name: "R_f", desc: "Rapporto di rottura q_f / q_a (iperbole)", unit: "-", default: 0.90, step: 0.01, min: 0.5, max: 0.99, category: "strength" },
  { id: "Ei", name: "Eᵢʳᵉᶠ", desc: "Modulo di Young iniziale asintotico a pref", unit: "kPa", default: 15460.0, step: 100, min: 100, max: 2000000, category: "stiffness" },
  { id: "alpha", name: "α", desc: "Parametro di forma del cap ellittico", unit: "-", default: 0.515, step: 0.001, min: 0.01, max: 5.0, category: "cap" },
  { id: "Hpp", name: "H_pp", desc: "Modulo di incrudimento plastico del cap", unit: "kPa", default: 9866.0, step: 50, min: 10, max: 500000, category: "cap" },
  { id: "gamma07", name: "γ₀.₇", desc: "Soglia di scorrimento al 72.2% di decadimento (G/G₀ = 0.722)", unit: "-", default: 0.000300, step: 0.00001, min: 0.00001, max: 0.01, category: "bricks" },
  { id: "G0", name: "G₀ʳᵉᶠ", desc: "Modulo di taglio a piccolissime deformazioni a pref", unit: "kPa", default: 60000.0, step: 500, min: 1000, max: 2000000, category: "bricks" }
];

export const PRESETS = {
  "glacial-till": {
    name: "Glacial Till (Cudny & Truty 2020)",
    desc: "Argilla limosa morenica sovraconsolidata, terreno di riferimento numgeo",
    params: {
      E50: 8500.0, Eoed: 6150.0, Eur: 25750.0, m: 0.70,
      c: 6.0, phi: 28.0, psi: 6.0, nu: 0.29,
      pref: 100.0, K0nc: 0.80, Rf: 0.90, Ei: 15460.0,
      alpha: 0.515, Hpp: 9866.0, gamma07: 0.000300, G0: 60000.0
    }
  },
  "hostun-sand": {
    name: "Dense Hostun Sand (Benz 2007)",
    desc: "Sabbia silicea densa di Hostun (Francia), elevata dilatanza e rigidezza",
    params: {
      E50: 30000.0, Eoed: 30000.0, Eur: 90000.0, m: 0.55,
      c: 0.1, phi: 42.0, psi: 16.0, nu: 0.25,
      pref: 100.0, K0nc: 0.40, Rf: 0.90, Ei: 65000.0,
      alpha: 1.46, Hpp: 72000.0, gamma07: 0.000100, G0: 108000.0
    }
  },
  "berlin-sand": {
    name: "Medium Berlin Sand (numgeo / Cudny)",
    desc: "Sabbia media quarzosa di Berlino a media addensamento",
    params: {
      E50: 45000.0, Eoed: 45000.0, Eur: 135000.0, m: 0.50,
      c: 0.5, phi: 35.0, psi: 5.0, nu: 0.20,
      pref: 100.0, K0nc: 0.43, Rf: 0.90, Ei: 90000.0,
      alpha: 1.25, Hpp: 95000.0, gamma07: 0.000150, G0: 140000.0
    }
  },
  "london-clay": {
    name: "Stiff London Clay",
    desc: "Argilla dura fissurata di Londra, comportamento duttile-fragile",
    params: {
      E50: 12000.0, Eoed: 8000.0, Eur: 36000.0, m: 0.75,
      c: 15.0, phi: 24.0, psi: 2.0, nu: 0.30,
      pref: 100.0, K0nc: 0.65, Rf: 0.88, Ei: 20000.0,
      alpha: 0.72, Hpp: 16500.0, gamma07: 0.000250, G0: 75000.0
    }
  },
  "soft-kaolin": {
    name: "Soft Kaolin Clay",
    desc: "Argilla caolinitica normalmente consolidata ad elevata comprimibilità",
    params: {
      E50: 4000.0, Eoed: 2500.0, Eur: 12000.0, m: 0.85,
      c: 2.0, phi: 22.0, psi: 0.0, nu: 0.35,
      pref: 100.0, K0nc: 0.68, Rf: 0.92, Ei: 7000.0,
      alpha: 0.48, Hpp: 4200.0, gamma07: 0.000500, G0: 32000.0
    }
  }
};

/**
 * Parses a standard parameters.inp string used by numgeo / IncrementalDriver.exe
 */
export function parseParametersInp(text) {
  const lines = text.split(/\r?\n/)
    .map(l => l.trim())
    .filter(l => l.length > 0 && !l.startsWith("#"));

  if (lines.length < 3) {
    throw new Error("Il file parameters.inp è troppo corto o non valido.");
  }

  const result = {};
  const names = PARAM_DEFINITIONS.map(p => p.id);

  // Line 0 is cmname, Line 1 is nprops
  for (let i = 0; i < names.length; i++) {
    const lineIdx = 2 + i;
    if (lineIdx < lines.length) {
      const parts = lines[lineIdx].split(/\s+/);
      const valStr = parts[0].replace(/d/gi, "e");
      const num = parseFloat(valStr);
      if (!isNaN(num)) {
        result[names[i]] = num;
      }
    }
  }
  return result;
}

/**
 * Generates parameters.inp text format 100% compatible with numgeo / IncrementalDriver
 */
export function generateParametersInp(params, cmname = "Hardening-Soil-MN-Bricks") {
  let out = `    ${cmname.padEnd(28)} cmname\n`;
  out += `    16                           nprops\n`;
  for (const def of PARAM_DEFINITIONS) {
    const val = params[def.id] !== undefined ? params[def.id] : def.default;
    // Format in scientific notation or clean decimal
    const numStr = val < 0.01 || val >= 100000 ? val.toExponential(6) : val.toFixed(def.step < 0.01 ? 6 : 2);
    out += `    ${numStr.padEnd(16)} ${def.id.padEnd(12)} # ${def.desc}\n`;
  }
  return out;
}
