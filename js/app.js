/**
 * E3DC Solar Dashboard
 * Visualisierung von E3DC Energiedaten
 */

class E3DCDashboard {
  constructor() {
    this.data = [];
    this.filteredData = [];
    this.charts = {};
    this.currentPeriod = 'all';

    this.colors = {
      pv: '#f59e0b',           // Orange - PV
      battery: '#10b981',      // Grün - Batterie
      consumption: '#3b82f6',  // Blau - Hausverbrauch
      soc: '#06b6d4',          // Cyan - SOC
      gridFeed: '#22c55e',     // Grün - Einspeisung
      gridDraw: '#ef4444'      // Rot - Netzbezug
    };

    this.init();
  }

  init() {
    this.setupEventListeners();
    this.initCharts();
  }

  setupEventListeners() {
    // Datei-Upload
    const uploadInput = document.getElementById('csv-upload');
    if (uploadInput) {
      uploadInput.addEventListener('change', (e) => this.handleFileUpload(e));
    }

    // Drag & Drop
    const uploadLabel = document.querySelector('.upload-label');
    if (uploadLabel) {
      uploadLabel.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadLabel.classList.add('dragover');
      });
      uploadLabel.addEventListener('dragleave', () => {
        uploadLabel.classList.remove('dragover');
      });
      uploadLabel.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadLabel.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        if (file) this.processFile(file);
      });
    }

    // Demo-Daten Button
    const demoBtn = document.getElementById('load-demo');
    if (demoBtn) {
      demoBtn.addEventListener('click', () => this.loadDemoData());
    }

    // Zeitraum-Buttons
    document.querySelectorAll('.period-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        this.currentPeriod = e.target.dataset.period;
        this.filterDataByPeriod();
        this.updateCharts();
        this.updateStats();
      });
    });

    // Zoom-Reset Button
    const zoomResetBtn = document.getElementById('zoom-reset');
    if (zoomResetBtn) {
      zoomResetBtn.addEventListener('click', () => this.resetZoom());
    }

    // Daten laden Button
    const loadDataBtn = document.getElementById('load-data');
    if (loadDataBtn) {
      loadDataBtn.addEventListener('click', () => this.loadDataFromPortal());
    }

    // CSV speichern Button
    const saveCsvBtn = document.getElementById('save-csv');
    if (saveCsvBtn) {
      saveCsvBtn.addEventListener('click', () => this.saveDataAsCSV());
    }
  }

  resetZoom() {
    if (this.charts.main) {
      this.charts.main.resetZoom();
    }
    if (this.charts.soc) {
      this.charts.soc.resetZoom();
    }
  }

  handleFileUpload(event) {
    const file = event.target.files[0];
    if (file) this.processFile(file);
  }

  processFile(file) {
    const reader = new FileReader();

    reader.onload = (e) => {
      const content = e.target.result;

      if (file.name.endsWith('.json')) {
        this.parseJSON(content);
      } else if (file.name.endsWith('.csv')) {
        this.parseCSV(content);
      }
    };

    reader.readAsText(file);
  }

  /**
   * Parse deutsches Datum: DD.MM.YYYY HH:MM:SS
   */
  parseGermanDate(dateStr) {
    if (!dateStr) return null;

    // Format: "12.01.2026 00:00:00"
    const parts = dateStr.trim().split(' ');
    if (parts.length !== 2) return null;

    const dateParts = parts[0].split('.');
    const timeParts = parts[1].split(':');

    if (dateParts.length !== 3 || timeParts.length !== 3) return null;

    const day = parseInt(dateParts[0], 10);
    const month = parseInt(dateParts[1], 10) - 1; // Monate sind 0-basiert
    const year = parseInt(dateParts[2], 10);
    const hour = parseInt(timeParts[0], 10);
    const minute = parseInt(timeParts[1], 10);
    const second = parseInt(timeParts[2], 10);

    return new Date(year, month, day, hour, minute, second);
  }

  /**
   * Parse E3DC CSV-Format (Semikolon-getrennt, deutsche Spalten)
   */
  parseCSV(content) {
    // BOM entfernen falls vorhanden
    if (content.charCodeAt(0) === 0xFEFF) {
      content = content.slice(1);
    }

    const lines = content.trim().split('\n');
    if (lines.length < 2) return;

    // Header parsen
    const headerLine = lines[0];
    const delimiter = headerLine.includes(';') ? ';' : ',';
    const headers = headerLine.split(delimiter).map(h => h.trim().replace(/^"|"$/g, ''));

    // Spalten-Mapping für E3DC-Format
    const columnMap = {
      timestamp: headers.findIndex(h => h.toLowerCase().includes('zeitstempel')),
      soc: headers.findIndex(h => h.toLowerCase().includes('ladezustand')),
      pv: headers.findIndex(h => h.toLowerCase().includes('solarproduktion')),
      batteryCharge: headers.findIndex(h => h.toLowerCase().includes('batterie laden')),
      batteryDischarge: headers.findIndex(h => h.toLowerCase().includes('batterie entladen')),
      gridFeed: headers.findIndex(h => h.toLowerCase().includes('netzeinspeisung')),
      gridDraw: headers.findIndex(h => h.toLowerCase().includes('netzbezug')),
      consumption: headers.findIndex(h => h.toLowerCase().includes('hausverbrauch'))
    };

    // Fallback für englische/generische Spalten
    if (columnMap.timestamp === -1) {
      columnMap.timestamp = headers.findIndex(h => h.toLowerCase().includes('timestamp'));
    }

    this.data = [];

    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;

      const values = line.split(delimiter).map(v => v.trim().replace(/^"|"$/g, ''));

      // Timestamp parsen
      let timestamp;
      if (columnMap.timestamp !== -1) {
        const dateStr = values[columnMap.timestamp];
        // Versuche deutsches Format
        timestamp = this.parseGermanDate(dateStr);
        // Fallback auf ISO-Format
        if (!timestamp || isNaN(timestamp.getTime())) {
          timestamp = new Date(dateStr);
        }
      }

      if (!timestamp || isNaN(timestamp.getTime())) continue;

      // Werte extrahieren
      const getValue = (idx) => idx !== -1 ? parseFloat(values[idx]) || 0 : 0;

      const entry = {
        timestamp,
        battery_soc: getValue(columnMap.soc),
        pv_power: getValue(columnMap.pv),
        battery_charge: getValue(columnMap.batteryCharge),
        battery_discharge: getValue(columnMap.batteryDischarge),
        grid_feed: getValue(columnMap.gridFeed),
        grid_draw: getValue(columnMap.gridDraw),
        consumption: getValue(columnMap.consumption),
        // Kombinierte Werte
        battery_power: getValue(columnMap.batteryCharge) - getValue(columnMap.batteryDischarge),
        grid_power: getValue(columnMap.gridDraw) - getValue(columnMap.gridFeed)
      };

      this.data.push(entry);
    }

    this.data.sort((a, b) => a.timestamp - b.timestamp);

    console.log(`${this.data.length} Datensätze geladen`);

    this.filterDataByPeriod();
    this.updateCharts();
    this.updateStats();

    // Live-Werte mit dem neuesten Datenpunkt aktualisieren
    if (this.data.length) {
      this.updateLiveValues(this.data[this.data.length - 1]);
    }
  }

  parseJSON(content) {
    try {
      const json = JSON.parse(content);
      const rawData = json.data || json;

      if (!Array.isArray(rawData)) {
        console.error('Ungültiges JSON-Format - rawData:', rawData);
        return;
      }

      this.data = rawData.map(entry => ({
        timestamp: new Date(entry.timestamp),
        pv_power: entry.pv_power || entry.pvPower || 0,
        battery_power: entry.battery_power || entry.batteryPower || 0,
        grid_power: entry.grid_power || entry.gridPower || 0,
        grid_draw: entry.grid_draw || entry.gridConsumption || 0,
        grid_feed: entry.grid_feed || entry.gridFeedIn || 0,
        consumption: entry.consumption || entry.homePower || 0,
        battery_soc: entry.battery_soc || entry.batterySoc || 0
      })).filter(e => !isNaN(e.timestamp.getTime()));

      this.data.sort((a, b) => a.timestamp - b.timestamp);
      this.filterDataByPeriod();
      this.updateCharts();
      this.updateStats();

      if (this.data.length) {
        this.updateLiveValues(this.data[this.data.length - 1]);
      }
    } catch (err) {
      console.error('JSON Parse Error:', err);
    }
  }

  filterDataByPeriod() {
    if (!this.data.length) {
      this.filteredData = [];
      return;
    }

    // Neuestes Datum als Referenz
    const latestDate = this.data[this.data.length - 1].timestamp;
    let startDate;

    switch (this.currentPeriod) {
      case 'day':
        startDate = new Date(latestDate.getTime() - 1 * 24 * 60 * 60 * 1000);
        break;
      case 'week':
        startDate = new Date(latestDate.getTime() - 7 * 24 * 60 * 60 * 1000);
        break;
      case 'month':
        startDate = new Date(latestDate.getTime() - 30 * 24 * 60 * 60 * 1000);
        break;
      case 'year':
        startDate = new Date(latestDate.getTime() - 365 * 24 * 60 * 60 * 1000);
        break;
      case 'all':
      default:
        this.filteredData = [...this.data];
        return;
    }

    this.filteredData = this.data.filter(d => d.timestamp >= startDate);
  }

  // Plugin für Tagesgrenzen-Linien
  getDayBoundaryPlugin() {
    return {
      id: 'dayBoundaries',
      beforeDraw: (chart) => {
        if (!this.filteredData.length) return;

        const ctx = chart.ctx;
        const xAxis = chart.scales.x;
        const yAxis = chart.scales.y;

        // Finde alle Mitternachts-Zeitpunkte
        const midnights = new Set();
        this.filteredData.forEach(d => {
          const date = new Date(d.timestamp);
          if (date.getHours() === 0 && date.getMinutes() === 0) {
            midnights.add(date.getTime());
          }
        });

        ctx.save();
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
        ctx.lineWidth = 2;
        ctx.setLineDash([8, 4]);

        midnights.forEach(midnight => {
          const x = xAxis.getPixelForValue(midnight);
          if (x >= xAxis.left && x <= xAxis.right) {
            ctx.beginPath();
            ctx.moveTo(x, yAxis.top);
            ctx.lineTo(x, yAxis.bottom);
            ctx.stroke();

            // Datum-Label (direkt am oberen Rand der Chart-Area)
            const date = new Date(midnight);
            const label = date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' });
            ctx.setLineDash([]);
            ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
            ctx.font = 'bold 11px sans-serif';
            ctx.textAlign = 'center';
            // Position am oberen Rand der Chart-Area (innerhalb)
            ctx.fillText(label, x, yAxis.top + 12);
          }
        });

        ctx.restore();
      }
    };
  }

  initCharts() {
    // Day boundary plugin
    const dayBoundaryPlugin = this.getDayBoundaryPlugin();

    // Hauptdiagramm
    const mainCtx = document.getElementById('main-chart')?.getContext('2d');
    if (mainCtx) {
      this.charts.main = new Chart(mainCtx, {
        type: 'line',
        plugins: [dayBoundaryPlugin],
        data: {
          datasets: [
            {
              label: 'PV-Leistung',
              borderColor: this.colors.pv,
              backgroundColor: this.colors.pv + '20',
              fill: true,
              tension: 0.3,
              pointRadius: 0,
              borderWidth: 2,
              data: []
            },
            {
              label: 'Hausverbrauch',
              borderColor: this.colors.consumption,
              backgroundColor: this.colors.consumption + '20',
              fill: true,
              tension: 0.3,
              pointRadius: 0,
              borderWidth: 2,
              data: []
            },
            {
              label: 'Netzbezug',
              borderColor: this.colors.gridDraw,
              backgroundColor: this.colors.gridDraw + '10',
              fill: false,
              tension: 0.3,
              pointRadius: 0,
              borderWidth: 1.5,
              borderDash: [5, 5],
              data: []
            },
            {
              label: 'Netzeinspeisung',
              borderColor: this.colors.gridFeed,
              backgroundColor: this.colors.gridFeed + '10',
              fill: false,
              tension: 0.3,
              pointRadius: 0,
              borderWidth: 1.5,
              borderDash: [5, 5],
              data: []
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          layout: {
            padding: {
              top: 15,
              bottom: 10
            }
          },
          interaction: {
            mode: 'index',
            intersect: false
          },
          scales: {
            x: {
              type: 'time',
              time: {
                displayFormats: {
                  hour: 'HH:mm',
                  day: 'dd.MM',
                  month: 'MMM yyyy'
                },
                tooltipFormat: 'dd.MM.yyyy HH:mm'
              },
              grid: {
                color: 'rgba(255,255,255,0.1)'
              },
              ticks: {
                color: '#9ca3af',
                maxTicksLimit: 12
              }
            },
            y: {
              title: {
                display: true,
                text: 'Leistung (W)',
                color: '#9ca3af'
              },
              grid: {
                color: 'rgba(255,255,255,0.1)'
              },
              ticks: {
                color: '#9ca3af'
              }
            }
          },
          plugins: {
            legend: {
              position: 'top',
              align: 'center',
              labels: {
                color: '#e5e7eb',
                usePointStyle: true,
                padding: 15,
                font: {
                  size: 12
                }
              }
            },
            tooltip: {
              callbacks: {
                label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y.toLocaleString('de-DE')} W`
              }
            },
            zoom: {
              pan: {
                enabled: true,
                mode: 'x',
                modifierKey: null
              },
              zoom: {
                wheel: {
                  enabled: true,
                  modifierKey: null
                },
                pinch: {
                  enabled: true
                },
                drag: {
                  enabled: false
                },
                mode: 'x'
              },
              limits: {
                x: {
                  minRange: 3600000 // Minimum 1 Stunde sichtbar
                }
              }
            }
          }
        }
      });
    }

    // SOC-Diagramm
    const socCtx = document.getElementById('soc-chart')?.getContext('2d');
    if (socCtx) {
      this.charts.soc = new Chart(socCtx, {
        type: 'line',
        plugins: [dayBoundaryPlugin],
        data: {
          datasets: [{
            label: 'Batteriestand',
            borderColor: this.colors.soc,
            backgroundColor: this.createGradient(socCtx, this.colors.soc),
            fill: true,
            tension: 0.3,
            pointRadius: 0,
            borderWidth: 2,
            data: []
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          layout: {
            padding: {
              top: 15,
              bottom: 10
            }
          },
          scales: {
            x: {
              type: 'time',
              time: {
                displayFormats: {
                  hour: 'HH:mm',
                  day: 'dd.MM'
                },
                tooltipFormat: 'dd.MM.yyyy HH:mm'
              },
              grid: { color: 'rgba(255,255,255,0.1)' },
              ticks: { color: '#9ca3af', maxTicksLimit: 8 }
            },
            y: {
              min: 0,
              max: 100,
              title: {
                display: true,
                text: 'SOC (%)',
                color: '#9ca3af'
              },
              grid: { color: 'rgba(255,255,255,0.1)' },
              ticks: { color: '#9ca3af' }
            }
          },
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => `Batteriestand: ${ctx.parsed.y.toFixed(0)}%`
              }
            },
            zoom: {
              pan: {
                enabled: true,
                mode: 'x'
              },
              zoom: {
                wheel: {
                  enabled: true
                },
                pinch: {
                  enabled: true
                },
                mode: 'x'
              }
            }
          }
        }
      });
    }

    // Energiebilanz (Balkendiagramm)
    const balanceCtx = document.getElementById('balance-chart')?.getContext('2d');
    if (balanceCtx) {
      this.charts.balance = new Chart(balanceCtx, {
        type: 'bar',
        data: {
          labels: ['PV-Ertrag', 'Verbrauch', 'Einspeisung', 'Netzbezug'],
          datasets: [{
            data: [0, 0, 0, 0],
            backgroundColor: [
              this.colors.pv,
              this.colors.consumption,
              this.colors.gridFeed,
              this.colors.gridDraw
            ],
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: {
              grid: { display: false },
              ticks: { color: '#9ca3af' }
            },
            y: {
              title: {
                display: true,
                text: 'Energie (kWh)',
                color: '#9ca3af'
              },
              grid: { color: 'rgba(255,255,255,0.1)' },
              ticks: { color: '#9ca3af' }
            }
          },
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => `${ctx.parsed.y.toLocaleString('de-DE', {maximumFractionDigits: 1})} kWh`
              }
            }
          }
        }
      });
    }
  }

  createGradient(ctx, color) {
    const gradient = ctx.createLinearGradient(0, 0, 0, 250);
    gradient.addColorStop(0, color + '60');
    gradient.addColorStop(1, color + '05');
    return gradient;
  }

  updateCharts() {
    if (!this.filteredData.length) return;

    // Hauptdiagramm aktualisieren
    if (this.charts.main) {
      this.charts.main.data.datasets[0].data = this.filteredData.map(d => ({
        x: d.timestamp,
        y: d.pv_power
      }));
      this.charts.main.data.datasets[1].data = this.filteredData.map(d => ({
        x: d.timestamp,
        y: d.consumption
      }));
      this.charts.main.data.datasets[2].data = this.filteredData.map(d => ({
        x: d.timestamp,
        y: d.grid_draw || 0
      }));
      this.charts.main.data.datasets[3].data = this.filteredData.map(d => ({
        x: d.timestamp,
        y: d.grid_feed || 0
      }));
      this.charts.main.update('none');
    }

    // SOC-Diagramm aktualisieren
    if (this.charts.soc) {
      this.charts.soc.data.datasets[0].data = this.filteredData.map(d => ({
        x: d.timestamp,
        y: d.battery_soc
      }));
      this.charts.soc.update('none');
    }

    // Energiebilanz aktualisieren
    this.updateBalanceChart();
  }

  updateBalanceChart() {
    if (!this.charts.balance || !this.filteredData.length) return;

    // Energie berechnen: Leistung (W) * Zeit (15min = 0.25h) = Wh -> /1000 = kWh
    const intervalHours = 0.25; // 15-Minuten-Intervalle

    let totalPV = 0;
    let totalConsumption = 0;
    let totalGridFeed = 0;
    let totalGridDraw = 0;

    this.filteredData.forEach(d => {
      totalPV += (d.pv_power || 0) * intervalHours;
      totalConsumption += (d.consumption || 0) * intervalHours;
      totalGridFeed += (d.grid_feed || 0) * intervalHours;
      totalGridDraw += (d.grid_draw || 0) * intervalHours;
    });

    // Wh zu kWh
    totalPV /= 1000;
    totalConsumption /= 1000;
    totalGridFeed /= 1000;
    totalGridDraw /= 1000;

    this.charts.balance.data.datasets[0].data = [totalPV, totalConsumption, totalGridFeed, totalGridDraw];
    this.charts.balance.update('none');
  }

  updateStats() {
    if (!this.filteredData.length) return;

    const intervalHours = 0.25;

    let totalPV = 0;
    let totalConsumption = 0;
    let totalGridFeed = 0;
    let totalGridDraw = 0;

    this.filteredData.forEach(d => {
      totalPV += (d.pv_power || 0) * intervalHours;
      totalConsumption += (d.consumption || 0) * intervalHours;
      totalGridFeed += (d.grid_feed || 0) * intervalHours;
      totalGridDraw += (d.grid_draw || 0) * intervalHours;
    });

    // Wh zu kWh
    totalPV /= 1000;
    totalConsumption /= 1000;
    totalGridFeed /= 1000;
    totalGridDraw /= 1000;

    // Eigenverbrauch = (PV - Einspeisung) / PV * 100
    const selfConsumption = totalPV > 0 ? ((totalPV - totalGridFeed) / totalPV) * 100 : 0;

    // Autarkie = (Verbrauch - Netzbezug) / Verbrauch * 100
    const autarky = totalConsumption > 0 ? ((totalConsumption - totalGridDraw) / totalConsumption) * 100 : 0;

    // DOM aktualisieren
    this.setStatValue('stat-total-pv', this.formatEnergy(totalPV));
    this.setStatValue('stat-total-consumption', this.formatEnergy(totalConsumption));
    this.setStatValue('stat-grid-feed', this.formatEnergy(totalGridFeed));
    this.setStatValue('stat-grid-draw', this.formatEnergy(totalGridDraw));
    this.setStatValue('stat-self-consumption', Math.max(0, selfConsumption).toFixed(1) + ' %');
    this.setStatValue('stat-autarky', Math.max(0, autarky).toFixed(1) + ' %');
  }

  formatEnergy(kWh) {
    return kWh.toLocaleString('de-DE', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' kWh';
  }

  formatPower(watts) {
    if (Math.abs(watts) >= 1000) {
      return (watts / 1000).toLocaleString('de-DE', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' kW';
    }
    return watts.toLocaleString('de-DE', { maximumFractionDigits: 0 }) + ' W';
  }

  setStatValue(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  updateLiveValues(data) {
    this.setStatValue('live-pv', this.formatPower(data.pv_power || 0));
    this.setStatValue('live-soc', (data.battery_soc || 0).toFixed(0) + ' %');

    // Netz: Positiv = Bezug, Negativ = Einspeisung
    const gridPower = (data.grid_draw || 0) - (data.grid_feed || 0);
    const gridEl = document.getElementById('live-grid');
    if (gridEl) {
      if (gridPower > 0) {
        gridEl.textContent = this.formatPower(gridPower);
        gridEl.style.color = this.colors.gridDraw;
      } else if (gridPower < 0) {
        gridEl.textContent = '-' + this.formatPower(Math.abs(gridPower));
        gridEl.style.color = this.colors.gridFeed;
      } else {
        gridEl.textContent = '0 W';
        gridEl.style.color = '';
      }
    }

    this.setStatValue('live-consumption', this.formatPower(data.consumption || 0));
  }

  loadDemoData() {
    // Demo-Daten generieren (3 Tage, 15-Minuten-Intervalle)
    const now = new Date();
    this.data = [];

    for (let day = 2; day >= 0; day--) {
      for (let hour = 0; hour < 24; hour++) {
        for (let minute = 0; minute < 60; minute += 15) {
          const timestamp = new Date(now);
          timestamp.setDate(timestamp.getDate() - day);
          timestamp.setHours(hour, minute, 0, 0);

          // Simulierte PV-Kurve (Glockenform tagsüber)
          let pvPower = 0;
          if (hour >= 8 && hour <= 17) {
            const peakHour = 12.5;
            const spread = 3;
            pvPower = 6000 * Math.exp(-Math.pow(hour + minute/60 - peakHour, 2) / (2 * spread * spread));
            pvPower *= (0.7 + Math.random() * 0.6);
          }

          // Simulierter Verbrauch
          let consumption = 400 + Math.random() * 300;
          if (hour >= 6 && hour <= 8) consumption += 800 + Math.random() * 400;
          if (hour >= 11 && hour <= 13) consumption += 500 + Math.random() * 300;
          if (hour >= 17 && hour <= 21) consumption += 1200 + Math.random() * 800;

          // Batterie SOC (vereinfacht)
          let soc = 20;
          if (hour >= 10 && hour <= 15) soc = 60 + Math.random() * 40;
          else if (hour >= 16 && hour <= 20) soc = 40 + Math.random() * 30;
          else soc = 15 + Math.random() * 25;

          // Netzberechnung
          const surplus = pvPower - consumption;
          let gridFeed = 0;
          let gridDraw = 0;

          if (surplus > 0) {
            gridFeed = surplus * 0.6;
          } else {
            gridDraw = Math.abs(surplus) * 0.7;
          }

          this.data.push({
            timestamp,
            pv_power: Math.max(0, pvPower),
            consumption: consumption,
            battery_soc: Math.min(100, Math.max(0, soc)),
            grid_feed: gridFeed,
            grid_draw: gridDraw,
            battery_charge: surplus > 0 ? surplus * 0.4 : 0,
            battery_discharge: surplus < 0 ? Math.abs(surplus) * 0.3 : 0
          });
        }
      }
    }

    this.filterDataByPeriod();
    this.updateCharts();
    this.updateStats();

    if (this.data.length) {
      this.updateLiveValues(this.data[this.data.length - 1]);
    }
  }
}

// Dashboard initialisieren
document.addEventListener('DOMContentLoaded', () => {
  window.dashboard = new E3DCDashboard();

  // Automatisch CSV aus data-Verzeichnis laden
  window.dashboard.autoLoadCSV();

  // Logout-Button Event-Listener
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', handleLogout);
  }
});

// Auto-Load Funktion zur Klasse hinzufügen
E3DCDashboard.prototype.autoLoadCSV = async function() {
  // Automatisch die letzten 7 Tage vom E3DC laden
  try {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 7);

    const startStr = startDate.toISOString().split('T')[0];
    const endStr = endDate.toISOString().split('T')[0];

    // Datumsfelder im UI setzen
    const dateFromInput = document.getElementById('date-from');
    const dateToInput = document.getElementById('date-to');
    if (dateFromInput) dateFromInput.value = startStr;
    if (dateToInput) dateToInput.value = endStr;

    const response = await fetch(`/api/data/history?start_date=${startStr}&end_date=${endStr}&resolution=day`);

    if (response.ok) {
      const data = await response.json();
      if (data && !data.error && data.data && data.data.length > 0) {
        this.parseJSON(JSON.stringify(data));
        this.showToast(`${data.data.length} Tage automatisch geladen`, 'success');
      }
    }
  } catch (err) {
    // Kein Fehler anzeigen - beim Start ist es normal wenn keine Daten vorhanden sind
    console.log('Auto-Load: Keine Daten geladen', err.message);
  }
};

// Toast-Benachrichtigungen zur Klasse hinzufügen
E3DCDashboard.prototype.showToast = function(message, type = 'info') {
  const statusMessage = document.getElementById('status-message');
  if (!statusMessage) return;

  // Toast-Typen: success, error, warning, info
  statusMessage.textContent = message;
  statusMessage.className = `status-message status-${type}`;
  statusMessage.classList.remove('hidden');

  // Auto-Hide nach 5 Sekunden (außer bei errors)
  if (type !== 'error') {
    setTimeout(() => {
      statusMessage.classList.add('hidden');
    }, 5000);
  } else {
    // Errors bleiben länger sichtbar
    setTimeout(() => {
      statusMessage.classList.add('hidden');
    }, 8000);
  }
};

// Daten vom E3DC-Portal laden
E3DCDashboard.prototype.loadDataFromPortal = async function() {
  const dateFrom = document.getElementById('date-from').value;
  const dateTo = document.getElementById('date-to').value;

  // Validierung
  if (!dateFrom || !dateTo) {
    this.showToast('Bitte wählen Sie einen Zeitraum aus (Von und Bis Datum)', 'warning');
    return;
  }

  // Datum-Validierung
  const fromDate = new Date(dateFrom);
  const toDate = new Date(dateTo);

  if (fromDate > toDate) {
    this.showToast('Das Von-Datum muss vor dem Bis-Datum liegen', 'error');
    return;
  }

  try {
    this.showToast('Lade Daten vom E3DC-Portal...', 'info');

    const response = await fetch(`/api/data/history?start_date=${dateFrom}&end_date=${dateTo}&resolution=day`);

    if (!response.ok) {
      if (response.status === 401) {
        this.showToast('Nicht authentifiziert. Bitte melden Sie sich erneut an.', 'error');
        setTimeout(() => window.location.href = '/login', 2000);
        return;
      }

      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `Server-Fehler: ${response.status}`);
    }

    const data = await response.json();

    // Fehler vom Backend prüfen
    if (data.error) {
      this.showToast(`E3DC Portal Fehler: ${data.error}`, 'error');
      return;
    }

    if (!data || (Array.isArray(data) && data.length === 0)) {
      this.showToast('Keine Daten für den ausgewählten Zeitraum gefunden', 'warning');
      return;
    }

    // Daten verarbeiten - API gibt bereits { data: [...] } zurück
    const dataArray = data.data || data;
    this.parseJSON(JSON.stringify({ data: dataArray }));

    const dataCount = Array.isArray(dataArray) ? dataArray.length : 0;
    this.showToast(`✓ ${dataCount} Datensätze erfolgreich geladen`, 'success');

  } catch (err) {
    console.error('Fehler beim Laden der Daten:', err);
    this.showToast(`Fehler beim Laden: ${err.message}`, 'error');
  }
};

// Daten als CSV speichern
E3DCDashboard.prototype.saveDataAsCSV = function() {
  if (!this.data || this.data.length === 0) {
    this.showToast('Keine Daten zum Speichern vorhanden', 'warning');
    return;
  }

  try {
    // CSV-Header
    let csv = 'Zeitstempel,PV-Leistung (W),Hausverbrauch (W),Netzbezug (W),Netzeinspeisung (W),Batteriestand (%)\n';

    // Daten als CSV-Zeilen
    this.data.forEach(entry => {
      const timestamp = entry.timestamp.toLocaleString('de-DE');
      const pv = entry.pv_power || 0;
      const consumption = entry.consumption || 0;
      const gridDraw = entry.grid_draw || 0;
      const gridFeed = entry.grid_feed || 0;
      const soc = entry.battery_soc || 0;

      csv += `${timestamp},${pv},${consumption},${gridDraw},${gridFeed},${soc}\n`;
    });

    // Download triggern
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    const filename = `e3dc_data_${new Date().toISOString().split('T')[0]}.csv`;
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    this.showToast(`✓ CSV-Datei "${filename}" wurde heruntergeladen`, 'success');

  } catch (err) {
    console.error('Fehler beim Speichern der CSV:', err);
    this.showToast(`Fehler beim Speichern: ${err.message}`, 'error');
  }
};

// Logout-Funktion
async function handleLogout() {
  if (!confirm('Möchten Sie sich wirklich abmelden?')) {
    return;
  }

  try {
    const response = await fetch('/api/logout', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    if (response.ok) {
      // Erfolgreich ausgeloggt - zur Login-Seite weiterleiten
      window.location.href = '/login';
    } else {
      console.error('Logout fehlgeschlagen');
      alert('Fehler beim Abmelden. Bitte versuchen Sie es erneut.');
    }
  } catch (err) {
    console.error('Logout-Fehler:', err);
    alert('Verbindungsfehler beim Abmelden.');
  }
}
