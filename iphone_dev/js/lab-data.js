// lab-data.js — CSV parser, Lab experimental data management, and calibration error analysis

// Sample Glacial Till experimental triaxial data (from Cudny & Truty 2020 / numgeo test)
export const SAMPLE_TRIAXIAL_CSV = `eps_s_pct,q_kPa,p_eff_kPa,eps_v_pct
0.0,0.0,100.0,0.0
0.83,70.7,123.6,0.064
1.67,106.8,135.6,0.096
2.5,125.0,141.7,0.102
3.33,135.8,145.3,0.09
4.17,148.2,149.4,0.063
5.0,155.8,151.9,0.026
5.83,158.2,152.7,-0.019
6.67,162.2,154.1,-0.07
7.5,165.1,155.0,-0.124
8.33,166.4,155.5,-0.181
9.17,172.9,157.6,-0.238
10.0,176.3,158.8,-0.297
10.83,173.5,157.8,-0.356
11.67,178.7,159.6,-0.414
12.5,179.9,160.0,-0.471
13.33,179.1,159.7,-0.528
14.17,182.3,160.8,-0.583
15.0,185.0,161.7,-0.638
15.83,182.5,160.8,-0.692
16.67,181.9,160.6,-0.744
17.5,179.6,159.9,-0.796
18.33,183.8,161.3,-0.846
19.17,187.2,162.4,-0.896
20.0,186.9,162.3,-0.945`;

// Sample Glacial Till resonant column cyclic data
export const SAMPLE_CYCLIC_CSV = `gamma,G_over_G0,damping_pct
1e-06,0.998,0.84
3e-06,1.0,0.29
1e-05,0.988,0.69
3e-05,0.971,0.99
0.0001,0.887,3.72
0.0003,0.725,9.93
0.001,0.398,28.17
0.003,0.191,38.23
0.01,0.066,42.41`;

/**
 * Parses generic CSV text into array of column objects
 */
export function parseCSV(csvText) {
  const lines = csvText.trim().split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0);
  if (lines.length < 2) throw new Error("Il file CSV è vuoto o privo di intestazione.");

  // Detect delimiter: comma, semicolon, tab or spaces
  const headerLine = lines[0];
  let delimiter = ',';
  if (headerLine.includes(';')) delimiter = ';';
  else if (headerLine.includes('\t')) delimiter = '\t';
  else if (!headerLine.includes(',') && headerLine.includes(' ')) delimiter = /\s+/;

  const headers = typeof delimiter === 'string'
    ? headerLine.split(delimiter).map(h => h.trim().replace(/^["']|["']$/g, ''))
    : headerLine.split(delimiter);

  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const rawCols = typeof delimiter === 'string'
      ? lines[i].split(delimiter).map(c => c.trim().replace(/^["']|["']$/g, ''))
      : lines[i].split(delimiter);

    if (rawCols.length >= headers.length) {
      const row = {};
      headers.forEach((h, idx) => {
        const val = parseFloat(rawCols[idx].replace(',', '.'));
        row[h] = isNaN(val) ? rawCols[idx] : val;
      });
      rows.push(row);
    }
  }

  // Convert to columnar representation
  const columns = {};
  headers.forEach(h => {
    columns[h] = rows.map(r => r[h]);
  });

  return { headers, rows, columns };
}

/**
 * Computes calibration metrics between experimental data and simulated results
 * Uses linear interpolation for matching experimental X coordinates
 */
export function computeCalibrationMetrics(expX, expY, simX, simY) {
  if (!expX || !expY || expX.length === 0 || !simX || !simY) {
    return null;
  }

  // Interpolation helper
  const interp = (xTarget) => {
    if (xTarget <= simX[0]) return simY[0];
    if (xTarget >= simX[simX.length - 1]) return simY[simY.length - 1];
    for (let i = 0; i < simX.length - 1; i++) {
      if (xTarget >= simX[i] && xTarget <= simX[i + 1]) {
        const frac = (xTarget - simX[i]) / (simX[i + 1] - simX[i]);
        return simY[i] + frac * (simY[i + 1] - simY[i]);
      }
    }
    return simY[simY.length - 1];
  };

  let sumSqErr = 0;
  let maxAbsErr = 0;
  let sumY = 0;
  const n = expX.length;

  for (let i = 0; i < n; i++) {
    const yPred = interp(expX[i]);
    const err = expY[i] - yPred;
    sumSqErr += err * err;
    if (Math.abs(err) > maxAbsErr) maxAbsErr = Math.abs(err);
    sumY += expY[i];
  }

  const meanY = sumY / n;
  let ssTot = 0;
  for (let i = 0; i < n; i++) {
    ssTot += Math.pow(expY[i] - meanY, 2);
  }

  const rmse = Math.sqrt(sumSqErr / n);
  const r2 = ssTot > 1e-12 ? Math.max(0.0, 1.0 - (sumSqErr / ssTot)) : 1.0;

  return {
    nPoints: n,
    rmse: rmse,
    r2: r2,
    maxAbsError: maxAbsErr
  };
}

/**
 * Downloads a string as a file on iPhone / browser
 */
export function downloadFile(content, fileName, mimeType = 'text/plain') {
  const blob = new Blob([content], { type: `${mimeType};charset=utf-8;` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, 100);
}
