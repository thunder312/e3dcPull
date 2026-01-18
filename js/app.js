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
    this.currentResolution = 'day'; // Aktuelle Auflösung: '15min', 'hour', 'day'

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

    // Resolution Radio-Buttons
    document.querySelectorAll('input[name="resolution"]').forEach(radio => {
      radio.addEventListener('change', (e) => {
        this.currentResolution = e.target.value;
      });
    });

    // Modal schließen Button
    const modalCloseBtn = document.getElementById('modal-close');
    if (modalCloseBtn) {
      modalCloseBtn.addEventListener('click', () => {
        if (this._modalConfirmCallback) {
          this._modalConfirmCallback();
          this._modalConfirmCallback = null;
        }
        this.hideModal();
      });
    }

    // Modal Abbrechen Button
    const modalCancelBtn = document.getElementById('modal-cancel');
    if (modalCancelBtn) {
      modalCancelBtn.addEventListener('click', () => {
        this._modalConfirmCallback = null;
        this.hideModal();
      });
    }

    // Modal per Klick auf Overlay schließen (nur bei Info-Modals, nicht bei Bestätigungen)
    const modalOverlay = document.getElementById('warn-modal');
    if (modalOverlay) {
      modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay && !this._modalConfirmCallback) {
          this.hideModal();
        }
      });
    }

    // Modal per Escape-Taste schließen (nur bei Info-Modals)
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !this._modalConfirmCallback) {
        this.hideModal();
      }
    });
  }

  /**
   * Zeigt ein Info-Modal an (nur OK-Button)
   */
  showModal(title, message) {
    const modal = document.getElementById('warn-modal');
    const titleEl = document.getElementById('modal-title');
    const messageEl = document.getElementById('modal-message');
    const cancelBtn = document.getElementById('modal-cancel');
    const confirmBtn = document.getElementById('modal-close');
    const iconEl = document.getElementById('modal-icon');

    if (titleEl) titleEl.textContent = title;
    if (messageEl) messageEl.textContent = message;
    if (cancelBtn) cancelBtn.classList.add('hidden');
    if (confirmBtn) confirmBtn.textContent = 'OK';
    if (iconEl) iconEl.classList.remove('modal-icon-danger');

    this._modalConfirmCallback = null;
    if (modal) modal.classList.remove('hidden');
  }

  /**
   * Zeigt ein Bestätigungs-Modal an (Bestätigen/Abbrechen)
   */
  showConfirmModal(title, message, confirmText, onConfirm, isDanger = false) {
    const modal = document.getElementById('warn-modal');
    const titleEl = document.getElementById('modal-title');
    const messageEl = document.getElementById('modal-message');
    const cancelBtn = document.getElementById('modal-cancel');
    const confirmBtn = document.getElementById('modal-close');
    const iconEl = document.getElementById('modal-icon');

    if (titleEl) titleEl.textContent = title;
    if (messageEl) messageEl.textContent = message;
    if (cancelBtn) cancelBtn.classList.remove('hidden');
    if (confirmBtn) confirmBtn.textContent = confirmText || 'Bestätigen';
    if (iconEl) {
      if (isDanger) {
        iconEl.classList.add('modal-icon-danger');
      } else {
        iconEl.classList.remove('modal-icon-danger');
      }
    }

    this._modalConfirmCallback = onConfirm;
    if (modal) modal.classList.remove('hidden');
  }

  /**
   * Versteckt das Modal
   */
  hideModal() {
    const modal = document.getElementById('warn-modal');
    if (modal) modal.classList.add('hidden');
    this._modalConfirmCallback = null;
  }

  /**
   * Liest die aktuell ausgewählte Resolution aus den Radio-Buttons
   */
  getSelectedResolution() {
    const selected = document.querySelector('input[name="resolution"]:checked');
    return selected ? selected.value : 'day';
  }

  /**
   * Gibt die Intervall-Stunden für die aktuelle Resolution zurück
   * Wird für Energieberechnungen verwendet
   */
  getIntervalHours(resolution = null) {
    const res = resolution || this.currentResolution;
    switch (res) {
      case '15min': return 0.25;  // 15 Minuten = 0.25 Stunden
      case 'hour': return 1;      // 1 Stunde
      case 'day': return 24;      // 1 Tag = 24 Stunden
      default: return 0.25;       // Fallback auf 15 Minuten
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
   * Parse deutsches Datum: DD.MM.YYYY oder DD.MM.YYYY HH:MM:SS
   */
  parseGermanDate(dateStr) {
    if (!dateStr) return null;

    // Komma durch Leerzeichen ersetzen und mehrfache Leerzeichen entfernen
    const normalized = dateStr.trim().replace(',', ' ').replace(/\s+/g, ' ');
    const parts = normalized.split(' ');

    const dateParts = parts[0].split('.');
    if (dateParts.length !== 3) return null;

    const day = parseInt(dateParts[0], 10);
    const month = parseInt(dateParts[1], 10) - 1; // Monate sind 0-basiert
    const year = parseInt(dateParts[2], 10);

    // Zeit ist optional
    let hour = 0, minute = 0, second = 0;
    if (parts.length >= 2) {
      const timeParts = parts[1].split(':');
      hour = timeParts.length >= 1 ? parseInt(timeParts[0], 10) : 0;
      minute = timeParts.length >= 2 ? parseInt(timeParts[1], 10) : 0;
      second = timeParts.length >= 3 ? parseInt(timeParts[2], 10) : 0;
    }

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

    // Spalten-Mapping für verschiedene CSV-Formate
    const findColumn = (...patterns) => {
      for (const pattern of patterns) {
        const idx = headers.findIndex(h => h.toLowerCase().includes(pattern.toLowerCase()));
        if (idx !== -1) return idx;
      }
      return -1;
    };

    const columnMap = {
      timestamp: findColumn('zeitstempel', 'timestamp', 'datum', 'date'),
      soc: findColumn('batteriestand', 'ladezustand', 'soc', 'state of charge'),
      pv: findColumn('pv-leistung', 'solarproduktion', 'pv_power', 'solar'),
      batteryCharge: findColumn('batterie laden', 'battery_charge'),
      batteryDischarge: findColumn('batterie entladen', 'battery_discharge'),
      gridFeed: findColumn('netzeinspeisung', 'grid_feed', 'einspeisung'),
      gridDraw: findColumn('netzbezug', 'grid_draw', 'bezug'),
      consumption: findColumn('hausverbrauch', 'verbrauch', 'consumption')
    };

    this.data = [];

    // Prüfen ob Komma-CSV mit Komma im Timestamp (z.B. "10.1.2026, 00:00:00")
    const hasTimestampComma = delimiter === ',' && headers.length === 6;

    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;

      let values = line.split(delimiter).map(v => v.trim().replace(/^"|"$/g, ''));

      // Fix für Komma im Timestamp: "10.1.2026, 00:00:00" wird zu zwei Spalten
      if (hasTimestampComma && values.length === 7 && values[1].includes(':')) {
        // Timestamp zusammenfügen und Array korrigieren
        values = [values[0] + ' ' + values[1], ...values.slice(2)];
      }

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

    if (this.data.length === 0) {
      this.showToast('Keine Daten in der CSV gefunden. Prüfen Sie das Format.', 'warning');
      return;
    }

    this.filterDataByPeriod();
    this.updateCharts();
    this.updateStats();

    // Live-Werte mit dem neuesten Datenpunkt aktualisieren
    if (this.data.length) {
      this.updateLiveValues(this.data[this.data.length - 1]);
      this.showToast(`${this.data.length} Datensätze aus CSV geladen`, 'success');
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

    // Energie berechnen basierend auf der aktuellen Resolution
    // Bei 'day' sind die Werte bereits in Wh (Tagesenergie), ansonsten Leistung * Zeit
    const intervalHours = this.getIntervalHours();
    const isEnergyData = this.currentResolution === 'day';

    let totalPV = 0;
    let totalConsumption = 0;
    let totalGridFeed = 0;
    let totalGridDraw = 0;

    this.filteredData.forEach(d => {
      if (isEnergyData) {
        // Tagesdaten: Werte sind bereits in Wh
        totalPV += (d.pv_power || 0);
        totalConsumption += (d.consumption || 0);
        totalGridFeed += (d.grid_feed || 0);
        totalGridDraw += (d.grid_draw || 0);
      } else {
        // 15min/Stunden-Daten: Leistung (W) * Zeit (h) = Wh
        totalPV += (d.pv_power || 0) * intervalHours;
        totalConsumption += (d.consumption || 0) * intervalHours;
        totalGridFeed += (d.grid_feed || 0) * intervalHours;
        totalGridDraw += (d.grid_draw || 0) * intervalHours;
      }
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

    // Zeitraum berechnen und anzeigen
    const firstDate = this.filteredData[0].timestamp;
    const lastDate = this.filteredData[this.filteredData.length - 1].timestamp;
    const formatDate = (d) => {
      const date = d instanceof Date ? d : new Date(d);
      return date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
    };
    const periodText = firstDate && lastDate
      ? `${formatDate(firstDate)} – ${formatDate(lastDate)} (${this.filteredData.length} Datenpunkte)`
      : '--';
    this.setStatValue('stats-period', periodText);

    // Energie berechnen basierend auf der aktuellen Resolution
    const intervalHours = this.getIntervalHours();
    const isEnergyData = this.currentResolution === 'day';

    let totalPV = 0;
    let totalConsumption = 0;
    let totalGridFeed = 0;
    let totalGridDraw = 0;

    this.filteredData.forEach(d => {
      if (isEnergyData) {
        // Tagesdaten: Werte sind bereits in Wh
        totalPV += (d.pv_power || 0);
        totalConsumption += (d.consumption || 0);
        totalGridFeed += (d.grid_feed || 0);
        totalGridDraw += (d.grid_draw || 0);
      } else {
        // 15min/Stunden-Daten: Leistung (W) * Zeit (h) = Wh
        totalPV += (d.pv_power || 0) * intervalHours;
        totalConsumption += (d.consumption || 0) * intervalHours;
        totalGridFeed += (d.grid_feed || 0) * intervalHours;
        totalGridDraw += (d.grid_draw || 0) * intervalHours;
      }
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
    // Zeitstempel formatieren und anzeigen
    if (data.timestamp) {
      const ts = data.timestamp instanceof Date ? data.timestamp : new Date(data.timestamp);
      if (!isNaN(ts.getTime())) {
        const formattedDate = ts.toLocaleDateString('de-DE', {
          day: '2-digit',
          month: '2-digit',
          year: 'numeric'
        });
        const formattedTime = ts.toLocaleTimeString('de-DE', {
          hour: '2-digit',
          minute: '2-digit'
        });
        this.setStatValue('live-timestamp', `${formattedDate}, ${formattedTime}`);
      }
    }

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
  // Automatisch die letzten 7 Tage vom E3DC laden (mit Tages-Auflösung)
  try {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 7);

    const startStr = startDate.toISOString().split('T')[0];
    const endStr = endDate.toISOString().split('T')[0];
    const resolution = 'day'; // Standard-Auflösung beim Auto-Load

    // Datumsfelder im UI setzen
    const dateFromInput = document.getElementById('date-from');
    const dateToInput = document.getElementById('date-to');
    if (dateFromInput) dateFromInput.value = startStr;
    if (dateToInput) dateToInput.value = endStr;

    // Resolution-Radio-Button auf 'day' setzen
    const dayRadio = document.querySelector('input[name="resolution"][value="day"]');
    if (dayRadio) dayRadio.checked = true;

    // Resolution für Berechnungen speichern
    this.currentResolution = resolution;

    // Loading-Toast anzeigen
    this.showToast('Lade letzte 8 Tage...', 'loading');

    const response = await fetch(`/api/data/history?start_date=${startStr}&end_date=${endStr}&resolution=${resolution}`);

    if (response.ok) {
      const data = await response.json();
      if (data && !data.error && data.data && data.data.length > 0) {
        this.parseJSON(JSON.stringify(data));
        this.showToast(`✓ ${data.data.length} Tage automatisch geladen`, 'success');
      } else {
        // Kein Toast wenn keine Daten - ist beim ersten Start normal
        const statusMessage = document.getElementById('status-message');
        if (statusMessage) statusMessage.classList.add('hidden');
      }
    } else {
      // Toast ausblenden bei Fehler (nicht eingeloggt etc.)
      const statusMessage = document.getElementById('status-message');
      if (statusMessage) statusMessage.classList.add('hidden');
    }
  } catch (err) {
    // Toast ausblenden bei Fehler
    const statusMessage = document.getElementById('status-message');
    if (statusMessage) statusMessage.classList.add('hidden');
    console.log('Auto-Load: Keine Daten geladen', err.message);
  }
};

// Toast-Benachrichtigungen zur Klasse hinzufügen
E3DCDashboard.prototype.showToast = function(message, type = 'info') {
  const statusMessage = document.getElementById('status-message');
  if (!statusMessage) return;

  // Vorherigen Timer löschen falls vorhanden
  if (this._toastTimer) {
    clearTimeout(this._toastTimer);
    this._toastTimer = null;
  }

  // Toast-Typen: success, error, warning, info, loading
  statusMessage.textContent = message;
  statusMessage.className = `status-message status-${type}`;
  statusMessage.classList.remove('hidden');

  // Loading-Toast bleibt bestehen bis er manuell ersetzt wird
  if (type === 'loading') {
    return; // Kein Auto-Hide
  }

  // Auto-Hide nach 5 Sekunden (außer bei errors)
  if (type !== 'error') {
    this._toastTimer = setTimeout(() => {
      statusMessage.classList.add('hidden');
    }, 5000);
  } else {
    // Errors bleiben länger sichtbar
    this._toastTimer = setTimeout(() => {
      statusMessage.classList.add('hidden');
    }, 8000);
  }
};

// Daten vom E3DC-Portal laden
E3DCDashboard.prototype.loadDataFromPortal = async function() {
  const dateFrom = document.getElementById('date-from').value;
  const dateTo = document.getElementById('date-to').value;
  const resolution = this.getSelectedResolution();

  // Validierung
  if (!dateFrom || !dateTo) {
    this.showToast('Bitte wählen Sie einen Zeitraum aus (Von und Bis Datum)', 'warning');
    return;
  }

  // Datum-Validierung
  const fromDate = new Date(dateFrom);
  let toDate = new Date(dateTo);
  const today = new Date();
  today.setHours(23, 59, 59, 999); // Ende des heutigen Tages

  if (fromDate > toDate) {
    this.showToast('Das Von-Datum muss vor dem Bis-Datum liegen', 'error');
    return;
  }

  // Prüfen ob Bis-Datum in der Zukunft liegt
  if (toDate > today) {
    const todayStr = new Date().toISOString().split('T')[0];
    const dateToInput = document.getElementById('date-to');

    // Modal anzeigen
    this.showModal(
      'Datum korrigiert',
      `Das Bis-Datum lag in der Zukunft. Für zukünftige Zeitpunkte gibt es keine Daten. Das Datum wurde automatisch auf heute (${new Date().toLocaleDateString('de-DE')}) korrigiert.`
    );

    // Datum auf heute setzen
    if (dateToInput) {
      dateToInput.value = todayStr;
    }
    toDate = new Date(todayStr);
  }

  // Aktualisierte Datumswerte für die Abfrage
  const dateToAdjusted = toDate.toISOString().split('T')[0];

  // Lade-Info mit Zeitraum anzeigen
  const daysDiff = Math.ceil((toDate - fromDate) / (1000 * 60 * 60 * 24)) + 1;
  const resolutionLabels = { '15min': '15-Minuten', 'hour': 'Stunden', 'day': 'Tages' };

  try {
    // Loading-Toast bleibt bis zum Ende bestehen
    this.showToast(`Lade ${resolutionLabels[resolution]}-Daten (${daysDiff} Tage)...`, 'loading');

    // Resolution speichern für Berechnungen
    this.currentResolution = resolution;

    const response = await fetch(`/api/data/history?start_date=${dateFrom}&end_date=${dateToAdjusted}&resolution=${resolution}`);

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
    this.showToast(`✓ ${dataCount} ${resolutionLabels[resolution]}-Datensätze geladen`, 'success');

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
    // CSV-Header (Semikolon-getrennt für deutsche Excel-Kompatibilität)
    let csv = 'Zeitstempel;PV-Leistung (W);Hausverbrauch (W);Netzbezug (W);Netzeinspeisung (W);Batteriestand (%)\n';

    // Daten als CSV-Zeilen
    this.data.forEach(entry => {
      // Datum formatieren: DD.MM.YYYY HH:MM:SS
      const d = entry.timestamp;
      const timestamp = `${d.getDate().toString().padStart(2,'0')}.${(d.getMonth()+1).toString().padStart(2,'0')}.${d.getFullYear()} ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}:${d.getSeconds().toString().padStart(2,'0')}`;
      const pv = entry.pv_power || 0;
      const consumption = entry.consumption || 0;
      const gridDraw = entry.grid_draw || 0;
      const gridFeed = entry.grid_feed || 0;
      const soc = entry.battery_soc || 0;

      csv += `${timestamp};${pv};${consumption};${gridDraw};${gridFeed};${soc}\n`;
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
function handleLogout() {
  // Bestätigungs-Modal anzeigen
  window.dashboard.showConfirmModal(
    'Abmelden',
    'Möchten Sie sich wirklich abmelden?',
    'Abmelden',
    async () => {
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
          window.dashboard.showModal('Fehler', 'Fehler beim Abmelden. Bitte versuchen Sie es erneut.');
        }
      } catch (err) {
        console.error('Logout-Fehler:', err);
        window.dashboard.showModal('Verbindungsfehler', 'Verbindungsfehler beim Abmelden.');
      }
    },
    true // isDanger = true für rotes Icon
  );
}
