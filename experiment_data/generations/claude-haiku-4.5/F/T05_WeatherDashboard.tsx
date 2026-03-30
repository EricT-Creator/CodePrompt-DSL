import React from 'react';

const 天气Dashboard: React.FC = () => {
  const current天气 = {
    temp: 72,
    humidity: 65,
    windSpeed: 10,
    condition: 'Partly Cloudy',
  };

  const forecast = [
    { day: 'Mon', high: 75, low: 62, cond: '☀️' },
    { day: 'Tue', high: 73, low: 60, cond: '⛅' },
    { day: 'Wed', high: 70, low: 58, cond: '🌧️' },
    { day: 'Thu', high: 68, low: 56, cond: '🌧️' },
    { day: 'Fri', high: 74, low: 61, cond: '☀️' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-400 to-blue-100 p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-white mb-8">天气</h1>
        <div className="bg-white rounded-xl shadow-lg p-8 mb-6">
          <div className="text-6xl font-bold">{current天气.temp}°F</div>
          <p className="text-2xl text-gray-600 mt-2">{current天气.condition}</p>
          <div className="grid grid-cols-2 gap-4 mt-6">
            <div className="bg-blue-50 p-4 rounded">
              <p className="text-gray-600">湿度</p>
              <p className="text-2xl font-bold">{current天气.humidity}%</p>
            </div>
            <div className="bg-blue-50 p-4 rounded">
              <p className="text-gray-600">风速</p>
              <p className="text-2xl font-bold">{current天气.windSpeed} mph</p>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {forecast.map((day, i) => (
            <div key={i} className="bg-white rounded-lg p-4 text-center shadow">
              <p className="font-bold">{day.day}</p>
              <p className="text-2xl my-2">{day.cond}</p>
              <p className="text-sm text-gray-600">{day.high}°/{day.low}°</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default 天气Dashboard;