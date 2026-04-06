import React, { useState } from 'react';

const CounterPanel: React.FC = () => {
  const [count, setCount] = useState<number>(0);

  const increment = () => {
    setCount(prev => prev + 1);
  };

  const decrement = () => {
    setCount(prev => {
      if (prev <= 0) return 0;
      return prev - 1;
    });
  };

  const reset = () => {
    setCount(0);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-2xl p-10">
        <header className="text-center mb-12">
          <h1 className="text-5xl font-black text-gray-900 mb-4">Counter</h1>
          <p className="text-gray-600 text-lg">A simple counter with constraint</p>
        </header>

        {/* Counter display */}
        <div className="mb-12">
          <div className="text-center">
            <div className="text-9xl font-extrabold text-blue-600 mb-6">
              {count}
            </div>
            <p className="text-gray-500 text-lg">Current count</p>
          </div>
        </div>

        {/* Buttons */}
        <div className="space-y-6 mb-10">
          <button
            onClick={increment}
            className="w-full py-5 bg-gradient-to-r from-blue-500 to-blue-600 text-white text-2xl font-bold rounded-xl hover:from-blue-600 hover:to-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-300 transition-all transform hover:scale-105"
          >
            Increment (+1)
          </button>
          
          <button
            onClick={decrement}
            disabled={count <= 0}
            className={`w-full py-5 text-2xl font-bold rounded-xl transition-all transform ${count <= 0 ? 'bg-gray-300 text-gray-500 cursor-not-allowed' : 'bg-gradient-to-r from-red-500 to-red-600 text-white hover:from-red-600 hover:to-red-700 hover:scale-105 focus:outline-none focus:ring-4 focus:ring-red-300'}`}
          >
            Decrement (-1)
          </button>
          
          <button
            onClick={reset}
            className="w-full py-5 bg-gradient-to-r from-gray-500 to-gray-600 text-white text-2xl font-bold rounded-xl hover:from-gray-600 hover:to-gray-700 focus:outline-none focus:ring-4 focus:ring-gray-300 transition-all transform hover:scale-105"
          >
            Reset to Zero
          </button>
        </div>

        {/* Constraints info */}
        <div className="bg-blue-50 border-2 border-blue-200 rounded-xl p-6 mb-8">
          <h3 className="text-xl font-bold text-blue-800 mb-3">Constraint</h3>
          <p className="text-blue-700">
            The counter cannot go below zero. Attempting to decrement when count is zero will have no effect.
          </p>
        </div>

        {/* Mock data note */}
        <div className="text-center text-gray-500 text-sm">
          <p>Mock counter component with validation constraint</p>
        </div>
      </div>
    </div>
  );
};

export default CounterPanel;