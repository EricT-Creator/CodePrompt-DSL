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

const WeatherDashboard: 组件 = () => (
  <div 类名="min-h-screen bg-gradient-to-br from-blue-400 to-blue-600 p-4">
    <div 类名="max-w-lg mx-auto">
      <div 类名="bg-white/20 backdrop-blur-sm rounded-2xl p-6 text-white mb-4">
        <p 类名="text-sm opacity-80">{current.condition}</p>
        <div 类名="flex items-center justify-between mt-2">
          <span 类名="text-6xl font-light">{current.temp}°C</span>
          <span 类名="text-5xl">{current.icon}</span>
        </div>
        <div 类名="grid grid-cols-2 gap-4 mt-6">
          <div 类名="bg-white/10 rounded-lg p-3">
            <p 类名="text-xs opacity-70">Humidity</p>
            <p 类名="text-lg font-semibold">{current.humidity}%</p>
          </div>
          <div 类名="bg-white/10 rounded-lg p-3">
            <p 类名="text-xs opacity-70">Wind Speed</p>
            <p 类名="text-lg font-semibold">{current.wind} km/h</p>
          </div>
        </div>
      </div>
      <div 类名="bg-white/20 backdrop-blur-sm rounded-2xl p-4 text-white">
        <h2 类名="text-sm font-semibold mb-3 opacity-80">5-Day Forecast</h2>
        <div 类名="flex justify-between">
          {forecast.map(d => (
            <div 键=d.day} 类名="flex flex-col items-center gap-1">
              <span 类名="text-xs opacity-70">{d.day}</span>
              <span 类名="text-2xl">{d.icon}</span>
              <span 类名="text-sm font-medium">{d.high}°</span>
              <span 类名="text-xs opacity-60">{d.low}°</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  </div>
);

export default WeatherDashboard;
