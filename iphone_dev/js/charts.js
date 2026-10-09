// charts.js — High-DPI Retina Touch-Friendly Interactive Canvas Charts for iOS

export class GeotechChart {
  constructor(canvasId, options = {}) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) {
      console.warn(`Canvas #${canvasId} not found`);
      return;
    }
    this.ctx = this.canvas.getContext('2d');
    this.options = {
      title: options.title || '',
      xLabel: options.xLabel || 'X',
      yLabel: options.yLabel || 'Y',
      y2Label: options.y2Label || null,
      xLog: options.xLog || false,
      yLog: options.yLog || false,
      xMin: options.xMin !== undefined ? options.xMin : null,
      xMax: options.xMax !== undefined ? options.xMax : null,
      yMin: options.yMin !== undefined ? options.yMin : null,
      yMax: options.yMax !== undefined ? options.yMax : null,
      y2Min: options.y2Min !== undefined ? options.y2Min : null,
      y2Max: options.y2Max !== undefined ? options.y2Max : null,
      ...options
    };

    this.series = []; // Array of { name, x, y, color, width, dash, isScatter, yAxis: 1|2 }
    this.activePoint = null;
    this.padding = { top: 32, right: options.y2Label ? 45 : 20, bottom: 42, left: 48 };

    this._initEvents();
    this.resize();
  }

  resize() {
    if (!this.canvas) return;
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 2;
    this.width = rect.width || 340;
    this.height = rect.height || 240;

    this.canvas.width = this.width * dpr;
    this.canvas.height = this.height * dpr;
    this.ctx.resetTransform?.();
    this.ctx.scale(dpr, dpr);
    this.render();
  }

  clear() {
    this.series = [];
    this.activePoint = null;
    this.render();
  }

  addSeries(seriesObj) {
    this.series.push({
      name: seriesObj.name || 'Serie',
      x: seriesObj.x || [],
      y: seriesObj.y || [],
      color: seriesObj.color || '#007AFF',
      width: seriesObj.width || 2,
      dash: seriesObj.dash || [],
      isScatter: seriesObj.isScatter || false,
      marker: seriesObj.marker || 'circle',
      yAxis: seriesObj.yAxis || 1
    });
  }

  _initEvents() {
    let touching = false;
    const handleMove = (clientX, clientY) => {
      const rect = this.canvas.getBoundingClientRect();
      const x = clientX - rect.left;
      const y = clientY - rect.top;
      this._findNearestPoint(x, y);
      this.render();
    };

    this.canvas.addEventListener('mousemove', (e) => handleMove(e.clientX, e.clientY));
    this.canvas.addEventListener('mouseleave', () => {
      this.activePoint = null;
      this.render();
    });

    this.canvas.addEventListener('touchstart', (e) => {
      touching = true;
      if (e.touches.length > 0) {
        handleMove(e.touches[0].clientX, e.touches[0].clientY);
      }
    }, { passive: true });

    this.canvas.addEventListener('touchmove', (e) => {
      if (touching && e.touches.length > 0) {
        handleMove(e.touches[0].clientX, e.touches[0].clientY);
      }
    }, { passive: true });

    this.canvas.addEventListener('touchend', () => {
      touching = false;
      this.activePoint = null;
      this.render();
    });
  }

  _findNearestPoint(px, py) {
    if (this.series.length === 0) return;
    const plotW = this.width - this.padding.left - this.padding.right;
    const plotH = this.height - this.padding.top - this.padding.bottom;
    if (px < this.padding.left || px > this.width - this.padding.right) {
      this.activePoint = null;
      return;
    }

    const { xMin, xMax, yMin, yMax, y2Min, y2Max } = this._getBounds();
    const xVal = this.options.xLog
      ? Math.pow(10, Math.log10(xMin) + ((px - this.padding.left) / plotW) * (Math.log10(xMax) - Math.log10(xMin)))
      : xMin + ((px - this.padding.left) / plotW) * (xMax - xMin);

    let nearest = null;
    let minDiff = Infinity;

    for (const s of this.series) {
      for (let i = 0; i < s.x.length; i++) {
        const diff = Math.abs(s.x[i] - xVal);
        if (diff < minDiff) {
          minDiff = diff;
          nearest = { series: s, x: s.x[i], y: s.y[i], idx: i };
        }
      }
    }
    this.activePoint = nearest;
  }

  _getBounds() {
    let xMin = this.options.xMin;
    let xMax = this.options.xMax;
    let yMin = this.options.yMin;
    let yMax = this.options.yMax;
    let y2Min = this.options.y2Min;
    let y2Max = this.options.y2Max;

    if (xMin === null || xMax === null || yMin === null || yMax === null) {
      let allX = [];
      let allY1 = [];
      let allY2 = [];

      for (const s of this.series) {
        if (!s.x || s.x.length === 0) continue;
        allX.push(...s.x);
        if (s.yAxis === 2) {
          allY2.push(...s.y);
        } else {
          allY1.push(...s.y);
        }
      }

      if (allX.length > 0) {
        if (xMin === null) xMin = this.options.xLog ? Math.max(1e-7, Math.min(...allX.filter(v => v > 0))) : Math.min(...allX);
        if (xMax === null) xMax = Math.max(...allX);
      } else {
        xMin = this.options.xLog ? 1e-6 : 0;
        xMax = this.options.xLog ? 1e-2 : 1;
      }

      if (allY1.length > 0) {
        if (yMin === null) yMin = Math.min(...allY1);
        if (yMax === null) yMax = Math.max(...allY1);
      } else {
        yMin = 0;
        yMax = 1;
      }

      if (this.options.y2Label && allY2.length > 0) {
        if (y2Min === null) y2Min = Math.min(...allY2);
        if (y2Max === null) y2Max = Math.max(...allY2);
      }
    }

    if (xMin === xMax) { xMin -= 1; xMax += 1; }
    if (yMin === yMax) { yMin -= 1; yMax += 1; }
    if (y2Min !== null && y2Min === y2Max) { y2Min -= 1; y2Max += 1; }

    return { xMin, xMax, yMin, yMax, y2Min, y2Max };
  }

  toScreen(x, y, bounds, yAxis = 1) {
    const plotW = this.width - this.padding.left - this.padding.right;
    const plotH = this.height - this.padding.top - this.padding.bottom;

    let sx;
    if (this.options.xLog) {
      const logMin = Math.log10(Math.max(1e-9, bounds.xMin));
      const logMax = Math.log10(Math.max(1e-9, bounds.xMax));
      const logX = Math.log10(Math.max(1e-9, x));
      sx = this.padding.left + ((logX - logMin) / (logMax - logMin)) * plotW;
    } else {
      sx = this.padding.left + ((x - bounds.xMin) / (bounds.xMax - bounds.xMin)) * plotW;
    }

    let sy;
    if (yAxis === 2 && bounds.y2Min !== null && bounds.y2Max !== null) {
      sy = this.height - this.padding.bottom - ((y - bounds.y2Min) / (bounds.y2Max - bounds.y2Min)) * plotH;
    } else {
      sy = this.height - this.padding.bottom - ((y - bounds.yMin) / (bounds.yMax - bounds.yMin)) * plotH;
    }

    return { x: sx, y: sy };
  }

  render() {
    if (!this.canvas || !this.ctx) return;
    const ctx = this.ctx;
    const w = this.width;
    const h = this.height;

    const isDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const bgCol = isDarkMode ? '#1C1C1E' : '#FFFFFF';
    const gridCol = isDarkMode ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)';
    const textCol = isDarkMode ? '#AEAEB2' : '#8E8E93';
    const axisCol = isDarkMode ? '#48484A' : '#C7C7CC';
    const titleCol = isDarkMode ? '#FFFFFF' : '#000000';

    ctx.clearRect(0, 0, w, h);

    const bounds = this._getBounds();
    const plotW = w - this.padding.left - this.padding.right;
    const plotH = h - this.padding.top - this.padding.bottom;

    // Draw Title
    if (this.options.title) {
      ctx.font = '600 12px -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif';
      ctx.fillStyle = titleCol;
      ctx.textAlign = 'left';
      ctx.fillText(this.options.title, this.padding.left, 18);
    }

    // Draw Grid and X Axis ticks
    ctx.lineWidth = 1;
    ctx.strokeStyle = gridCol;
    ctx.font = '10px -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif';
    ctx.fillStyle = textCol;

    if (this.options.xLog) {
      const minExp = Math.floor(Math.log10(bounds.xMin));
      const maxExp = Math.ceil(Math.log10(bounds.xMax));
      for (let exp = minExp; exp <= maxExp; exp++) {
        const val = Math.pow(10, exp);
        if (val < bounds.xMin || val > bounds.xMax) continue;
        const pt = this.toScreen(val, bounds.yMin, bounds);
        ctx.beginPath();
        ctx.moveTo(pt.x, this.padding.top);
        ctx.lineTo(pt.x, h - this.padding.bottom);
        ctx.stroke();

        ctx.textAlign = 'center';
        ctx.fillText(`1e${exp}`, pt.x, h - this.padding.bottom + 14);
      }
    } else {
      const numTicks = 5;
      for (let i = 0; i <= numTicks; i++) {
        const val = bounds.xMin + (i * (bounds.xMax - bounds.xMin)) / numTicks;
        const pt = this.toScreen(val, bounds.yMin, bounds);
        ctx.beginPath();
        ctx.moveTo(pt.x, this.padding.top);
        ctx.lineTo(pt.x, h - this.padding.bottom);
        ctx.stroke();

        ctx.textAlign = 'center';
        const strVal = Math.abs(val) >= 100 ? val.toFixed(0) : val.toFixed(1);
        ctx.fillText(strVal, pt.x, h - this.padding.bottom + 14);
      }
    }

    // Draw Y1 Ticks
    const numYTicks = 4;
    for (let i = 0; i <= numYTicks; i++) {
      const val = bounds.yMin + (i * (bounds.yMax - bounds.yMin)) / numYTicks;
      const pt = this.toScreen(bounds.xMin, val, bounds);
      ctx.beginPath();
      ctx.moveTo(this.padding.left, pt.y);
      ctx.lineTo(w - this.padding.right, pt.y);
      ctx.stroke();

      ctx.textAlign = 'right';
      const strVal = Math.abs(val) >= 100 ? val.toFixed(0) : (Math.abs(val) < 0.1 ? val.toFixed(3) : val.toFixed(1));
      ctx.fillText(strVal, this.padding.left - 6, pt.y + 3);
    }

    // Draw Y2 Ticks (if dual axis)
    if (this.options.y2Label && bounds.y2Min !== null && bounds.y2Max !== null) {
      for (let i = 0; i <= numYTicks; i++) {
        const val = bounds.y2Min + (i * (bounds.y2Max - bounds.y2Min)) / numYTicks;
        const pt = this.toScreen(bounds.xMin, val, bounds, 2);
        ctx.textAlign = 'left';
        const strVal = Math.abs(val) >= 100 ? val.toFixed(0) : val.toFixed(1);
        ctx.fillStyle = '#FF3B30';
        ctx.fillText(strVal, w - this.padding.right + 6, pt.y + 3);
      }
    }

    // Draw Axis lines
    ctx.strokeStyle = axisCol;
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(this.padding.left, this.padding.top);
    ctx.lineTo(this.padding.left, h - this.padding.bottom);
    ctx.lineTo(w - this.padding.right, h - this.padding.bottom);
    if (this.options.y2Label) {
      ctx.lineTo(w - this.padding.right, this.padding.top);
    }
    ctx.stroke();

    // Axis Labels
    ctx.fillStyle = textCol;
    ctx.textAlign = 'center';
    ctx.fillText(this.options.xLabel, this.padding.left + plotW / 2, h - 8);

    ctx.save();
    ctx.translate(12, this.padding.top + plotH / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = 'center';
    ctx.fillText(this.options.yLabel, 0, 0);
    ctx.restore();

    if (this.options.y2Label) {
      ctx.save();
      ctx.translate(w - 10, this.padding.top + plotH / 2);
      ctx.rotate(Math.PI / 2);
      ctx.textAlign = 'center';
      ctx.fillStyle = '#FF3B30';
      ctx.fillText(this.options.y2Label, 0, 0);
      ctx.restore();
    }

    // Clip to plot area for series
    ctx.save();
    ctx.beginPath();
    ctx.rect(this.padding.left, this.padding.top, plotW, plotH);
    ctx.clip();

    // Render Series
    for (const s of this.series) {
      if (!s.x || s.x.length === 0) continue;

      ctx.strokeStyle = s.color;
      ctx.fillStyle = s.color;
      ctx.lineWidth = s.width;
      ctx.setLineDash(s.dash || []);

      if (s.isScatter) {
        // Draw Points
        for (let i = 0; i < s.x.length; i++) {
          const pt = this.toScreen(s.x[i], s.y[i], bounds, s.yAxis);
          ctx.beginPath();
          if (s.marker === 'triangle') {
            ctx.moveTo(pt.x, pt.y - 4);
            ctx.lineTo(pt.x + 4, pt.y + 4);
            ctx.lineTo(pt.x - 4, pt.y + 4);
            ctx.closePath();
            ctx.fill();
          } else {
            ctx.arc(pt.x, pt.y, 3.5, 0, 2 * Math.PI);
            ctx.fill();
            ctx.lineWidth = 1;
            ctx.strokeStyle = '#FFFFFF';
            ctx.stroke();
          }
        }
      } else {
        // Draw Line
        ctx.beginPath();
        let started = false;
        for (let i = 0; i < s.x.length; i++) {
          const pt = this.toScreen(s.x[i], s.y[i], bounds, s.yAxis);
          if (!started) {
            ctx.moveTo(pt.x, pt.y);
            started = true;
          } else {
            ctx.lineTo(pt.x, pt.y);
          }
        }
        ctx.stroke();
      }
    }
    ctx.setLineDash([]);
    ctx.restore();

    // Draw Legend in Top Right
    let legendX = w - this.padding.right - 10;
    let legendY = 16;
    ctx.font = '500 9px -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif';
    ctx.textAlign = 'right';

    // Reverse to display top series
    for (const s of [...this.series].slice(0, 4)) {
      ctx.fillStyle = s.color;
      ctx.beginPath();
      ctx.arc(legendX - ctx.measureText(s.name).width - 6, legendY - 3, 3, 0, 2 * Math.PI);
      ctx.fill();

      ctx.fillStyle = textCol;
      ctx.fillText(s.name, legendX, legendY);
      legendY += 12;
    }

    // Touch Active Point Tooltip
    if (this.activePoint) {
      const pt = this.toScreen(this.activePoint.x, this.activePoint.y, bounds, this.activePoint.series.yAxis);
      // Vertical line
      ctx.strokeStyle = isDarkMode ? 'rgba(255,255,255,0.4)' : 'rgba(0,0,0,0.3)';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(pt.x, this.padding.top);
      ctx.lineTo(pt.x, h - this.padding.bottom);
      ctx.stroke();
      ctx.setLineDash([]);

      // Point circle
      ctx.fillStyle = this.activePoint.series.color;
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 5, 0, 2 * Math.PI);
      ctx.fill();
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Tooltip Card
      const text = `${this.activePoint.series.name}: (${this.activePoint.x.toFixed(this.options.xLog ? 4 : 2)}, ${this.activePoint.y.toFixed(2)})`;
      ctx.font = '600 10px -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif';
      const tw = ctx.measureText(text).width + 14;
      const th = 20;
      let tx = pt.x - tw / 2;
      if (tx < this.padding.left) tx = this.padding.left;
      if (tx + tw > w - this.padding.right) tx = w - this.padding.right - tw;
      let ty = pt.y - 28;
      if (ty < 5) ty = pt.y + 12;

      ctx.fillStyle = isDarkMode ? 'rgba(44,44,46,0.92)' : 'rgba(0,0,0,0.85)';
      ctx.beginPath();
      ctx.roundRect ? ctx.roundRect(tx, ty, tw, th, 6) : ctx.rect(tx, ty, tw, th);
      ctx.fill();

      ctx.fillStyle = '#FFFFFF';
      ctx.textAlign = 'center';
      ctx.fillText(text, tx + tw / 2, ty + 14);
    }
  }
}
