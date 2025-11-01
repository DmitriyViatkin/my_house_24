// diagram.js — обновлённая версия под Chart.js 4.x
window.addEventListener("load", function() {
  'use strict';

  // ======================
  // 1️⃣ Диаграмма №1 — Задолженность / Погашение
  // ======================
  const ctx1 = document.getElementById('barChart');
  if (ctx1) {
    new Chart(ctx1, {
      type: 'bar',
      data: {
        labels: [
          "янв., 2025", "февр., 2025", "март, 2025", "апр., 2025", "май, 2025",
          "июнь, 2025", "июль, 2025", "авг., 2025", "сент., 2025",
          "окт., 2025", "нояб., 2025", "дек., 2025"
        ],
        datasets: [
          {
            label: 'Задолженность',
            backgroundColor: 'rgba(221, 75, 57, 0.8)',
            borderColor: 'rgba(221, 75, 57, 1)',
            borderWidth: 1,
            data: [0, 0, 0, 2890, 0, 0, 0, 0, 0, 0, 0, 0]
          },
          {
            label: 'Погашение задолженности',
            backgroundColor: 'rgba(0, 166, 90, 0.8)',
            borderColor: 'rgba(0, 166, 90, 1)',
            borderWidth: 1,
            data: [0, 0, 0, 4425, 0, 0, 0, 0, 0, 0, 0, 0]
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: 'Сумма, грн' },
            ticks: {
              callback: value => value.toFixed(2)
            }
          },
          x: {
            title: { display: true, text: 'Месяцы' }
          }
        },
        plugins: {
          legend: { position: 'top' },
          tooltip: {
            callbacks: {
              label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y + ' грн'
            }
          }
        }
      }
    });
  }

  // ======================
  // 2️⃣ Диаграмма №2 — Приход / Расход
  // ======================
  const ctx2 = document.getElementById('barChart2');
  if (ctx2) {
    new Chart(ctx2, {
      type: 'bar',
      data: {
        labels: [
          "янв., 2025", "февр., 2025", "март, 2025", "апр., 2025", "май, 2025",
          "июнь, 2025", "июль, 2025", "авг., 2025", "сент., 2025",
          "окт., 2025", "нояб., 2025", "дек., 2025"
        ],
        datasets: [
          {
            label: 'Приход',
            backgroundColor: 'rgba(0, 166, 90, 0.8)',
            borderColor: 'rgba(0, 166, 90, 1)',
            borderWidth: 1,
            data: [null, null, null, 18450.00, null, null, null, null, null, null, null, null]
          },
          {
            label: 'Расход',
            backgroundColor: 'rgba(221, 75, 57, 0.8)',
            borderColor: 'rgba(221, 75, 57, 1)',
            borderWidth: 1,
            data: [null, null, null, 1000.00, null, null, null, null, null, null, null, null]
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: 'Сумма, грн' },
            ticks: {
              callback: value => value.toFixed(2)
            }
          },
          x: {
            title: { display: true, text: 'Месяцы' }
          }
        },
        plugins: {
          legend: { position: 'top' },
          tooltip: {
            callbacks: {
              label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y + ' грн'
            }
          }
        }
      }
    });
  }
});
