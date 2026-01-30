import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler
} from 'chart.js';
import ChartDataLabels from 'chartjs-plugin-datalabels';
import { Radar, Line } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  ChartDataLabels
);

export default function ATSCharts({ atsScore }) {
  if (!atsScore || !atsScore.rule_breakdown) return null;

  const breakdown = atsScore.rule_breakdown;

  // Progress Line Chart Data - Category Performance
  const lineData = {
    labels: Object.keys(breakdown).map(key =>
      key.replace(/_/g, ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
    ),
    datasets: [
      {
        label: 'Achievement Percentage',
        data: Object.values(breakdown).map(v => (v.score / v.max) * 100),
        fill: true,
        backgroundColor: 'rgba(102, 126, 234, 0.1)',
        borderColor: 'rgba(102, 126, 234, 1)',
        borderWidth: 3,
        tension: 0.4,
        pointBackgroundColor: Object.values(breakdown).map(v => {
          const pct = (v.score / v.max) * 100;
          return pct >= 80 ? '#10b981' : pct >= 50 ? '#f59e0b' : '#ef4444';
        }),
        pointBorderColor: '#fff',
        pointBorderWidth: 3,
        pointRadius: 8,
        pointHoverRadius: 10,
      },
    ],
  };

  const lineOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
      },
      title: {
        display: true,
        text: 'ATS Performance Across Categories',
        font: { size: 18, weight: 'bold' },
        padding: 20,
        color: '#333'
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        padding: 12,
        titleFont: { size: 13, weight: 'bold' },
        bodyFont: { size: 12 },
        callbacks: {
          label: function(context) {
            const breakdown = Object.values(atsScore.rule_breakdown)[context.dataIndex];
            return [
              `Performance: ${context.parsed.y.toFixed(1)}%`,
              `Score: ${breakdown.score} / ${breakdown.max}`
            ];
          }
        }
      },
      datalabels: {
        display: true,
        color: '#333',
        font: {
          weight: 'bold',
          size: 12
        },
        formatter: function(value, context) {
          const breakdown = Object.values(atsScore.rule_breakdown)[context.dataIndex];
          return `${breakdown.score}/${breakdown.max}`;
        },
        anchor: 'end',
        align: 'top',
        offset: 4
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        grid: {
          color: 'rgba(0, 0, 0, 0.05)',
        },
        ticks: {
          callback: function(value) {
            return value + '%';
          },
          font: { size: 11 }
        }
      },
      x: {
        grid: {
          display: false,
        },
        ticks: {
          font: { size: 10 },
          maxRotation: 45,
          minRotation: 45
        }
      }
    },
  };

  // Radar Chart Data - Performance Profile
  const radarData = {
    labels: Object.keys(breakdown).map(key =>
      key.replace(/_/g, ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
    ),
    datasets: [
      {
        label: 'Performance %',
        data: Object.values(breakdown).map(v => (v.score / v.max) * 100),
        backgroundColor: 'rgba(102, 126, 234, 0.2)',
        borderColor: 'rgba(102, 126, 234, 1)',
        borderWidth: 3,
        pointBackgroundColor: 'rgba(102, 126, 234, 1)',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 5,
        pointHoverRadius: 7,
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: 'rgba(102, 126, 234, 1)',
      },
    ],
  };

  const radarOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
      },
      title: {
        display: true,
        text: 'ATS Performance Profile',
        font: { size: 18, weight: 'bold' },
        padding: 20,
        color: '#333'
      },
    },
    scales: {
      r: {
        beginAtZero: true,
        max: 100,
        ticks: {
          stepSize: 20,
          font: { size: 10 },
          backdropColor: 'transparent'
        },
        pointLabels: {
          font: { size: 11, weight: 'bold' },
          color: '#333'
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.1)'
        }
      },
    },
  };

  return (
    <div className="ats-charts">
      <div className="chart-row">
        <div className="chart-container chart-large">
          <Line data={lineData} options={lineOptions} />
        </div>
      </div>
      
      <div className="chart-row">
        <div className="chart-container chart-large">
          <Radar data={radarData} options={radarOptions} />
        </div>
      </div>
    </div>
  );
}
