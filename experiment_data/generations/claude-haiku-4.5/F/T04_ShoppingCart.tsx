import React, { useState } from 'react';

interface Item {
  id: number;
  name: string;
  price: number;
  qty: number;
}

const ShoppingCart: React.FC = () => {
  const [items, setItems] = useState<Item[]>([
    { id: 1, name: 'Laptop', price: 999, qty: 1 },
    { id: 2, name: 'Mouse', price: 25, qty: 2 },
    { id: 3, name: 'Keyboard', price: 75, qty: 1 },
  ]);

  const updateQty = (id: number, qty: number) => {
    setItems(items.map(i => i.id === id ? { ...i, qty: Math.max(1, qty) } : i));
  };

  const total = items.reduce((sum, i) => sum + i.price * i.qty, 0);

  return (
    <div className="min-h-screen bg-gray-50 p-4 max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">购物车</h1>
      <div className="space-y-4 mb-6">
        {items.map(item => (
          <div key={item.id} className="bg-white p-4 rounded-lg flex justify-between items-center">
            <div>
              <h3 className="font-semibold">{item.name}</h3>
              <p className="text-gray-600">${item.price}</p>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => updateQty(item.id, item.qty - 1)} className="px-2 py-1 bg-gray-200 rounded">-</button>
              <span className="w-8 text-center">{item.qty}</span>
              <button onClick={() => updateQty(item.id, item.qty + 1)} className="px-2 py-1 bg-gray-200 rounded">+</button>
              <p className="ml-4 font-semibold">${(item.price * item.qty).toFixed(2)}</p>
            </div>
          </div>
        ))}
      </div>
      <div className="bg-white p-4 rounded-lg border-t-2">
        <p className="text-xl font-bold">总计：${total.toFixed(2)}</p>
        <button className="w-full mt-4 bg-green-500 text-white py-2 rounded-lg hover:bg-green-600 font-bold">
          结算
        </button>
      </div>
    </div>
  );
};

export default ShoppingCart;