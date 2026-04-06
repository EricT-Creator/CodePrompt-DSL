import React, { useState } from 'react';

const CounterPanel: React.FC = () => {
  const [count, setCount] = useState(0);

  const increment = () => {
    setCount(prev => prev + 1);
  };

  const decrement = () => {
    setCount(prev => Math.max(0, prev - 1));
  };

  const reset = () => {
    setCount(0);
  };

  return (
    <div className="max-w-xs mx-auto mt-8 p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold text-center mb-6">Counter</h2>
      
      <div className="text-6xl font-mono text-center mb-8 text-gray-800">
        {count}
      </div>
      
      <div className="flex justify-center gap-4">
        <button
          onClick={decrement}
          className="px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          -1
        </button>
        
        <button
          onClick={reset}
          className="px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500"
        >
          Reset
        </button>
        
        <button
          onClick={increment}
          className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-green-500"
        >
          +1
        </button>
      </div>
      
      <p className="text-sm text-gray-500 text-center mt-4">
        Count cannot go below zero
      </p>
    </div>
  );
};

export default CounterPanel;