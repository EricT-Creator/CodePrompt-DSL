import React from 'react';

interface DayForecast { day: string; high: number; low: number; icon: string; }

const current = { temp: 22, humidity: 65, wind: 12, condition: 'Partly Cloudy', icon: '⛅' };
const forecast: DayForecast[] = [
  { day: 'Mon', high: 24, low: 16, icon: '☀️' },
  { day: 'Tue', high: 21, low: 14, icon: '🌧️' },
  { day: 'Wed', high: 19, low: 13, icon: '🌧️' },
  { day: 'Thu', high: 23, low: 15, icon: '⛅' },
  { day: 'Fri', high: 25, low: 17, icon: '☀️' },
];

const WeatherDashboard: React.FC = () => (
  <div className="min-h-screen bg-gradient-to-br from-blue-400 to-blue-600 p-4">
    <div className="max-w-lg mx-auto">
      <div className="bg-white/20 backdrop-blur-sm rounded-2xl p-6 text-white mb-4">
        <p className="text-sm opacity-80">{current.condition}</p>
        <div className="flex items-center justify-between mt-2">
          <span className="text-6xl font-light">{current.temp}°C</span>
          <span className="text-5xl">{current.icon}</span>
        </div>
        <div className="grid grid-cols-2 gap-4 mt-6">
          <div className="bg-white/10 rounded-lg p-3">
            <p className="text-xs opacity-70">Humidity</p>
            <p className="text-lg font-semibold">{current.humidity}%</p>
          </div>
          <div className="bg-white/10 rounded-lg p-3">
            <p className="text-xs opacity-70">Wind Speed</p>
            <p className="text-lg font-semibold">{current.wind} km/h</p>
          </div>
        </div>
      </div>
      <div className="bg-white/20 backdrop-blur-sm rounded-2xl p-4 text-white">
        <h2 className="text-sm font-semibold mb-3 opacity-80">5-Day Forecast</h2>
        <div className="flex justify-between">
          {forecast.map(d => (
            <div key={d.day} className="flex flex-col items-center gap-1">
              <span className="text-xs opacity-70">{d.day}</span>
              <span className="text-2xl">{d.icon}</span>
              <span className="text-sm font-medium">{d.high}°</span>
              <span className="text-xs opacity-60">{d.low}°</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  </div>
);

export default WeatherDashboard;
