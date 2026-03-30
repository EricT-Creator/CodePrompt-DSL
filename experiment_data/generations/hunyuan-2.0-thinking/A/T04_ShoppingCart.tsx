import React, { useState } from 'react';

interface CartItem {
  id: number;
  name: string;
  price: number;
  qty: number;
  image: string;
}

const initialItems: CartItem[] = [
  { id: 1, name: 'Wireless Headphones', price: 59.99, qty: 1, image: '🎧' },
  { id: 2, name: 'USB-C Cable', price: 12.99, qty: 2, image: '🔌' },
  { id: 3, name: 'Phone Case', price: 24.99, qty: 1, image: '📱' },
];

const ShoppingCart: React.FC = () => {
  const [items, setItems] = useState<CartItem[]>(initialItems);

  const updateQty = (id: number, delta: number) => {
    setItems(items.map(item =>
      item.id === id ? { ...item, qty: Math.max(1, item.qty + delta) } : item
    ));
  };

  const removeItem = (id: number) => setItems(items.filter(i => i.id !== id));

  const total = items.reduce((sum, i) => sum + i.price * i.qty, 0);

  return (
    <div className="min-h-screen bg-gray-50 p-4 max-w-md mx-auto">
      <h1 className="text-2xl font-bold mb-6">Shopping Cart</h1>
      {items.length === 0 ? (
        <p className="text-gray-500 text-center py-8">Your cart is empty</p>
      ) : (
        <>
          <ul className="space-y-3 mb-6">
            {items.map(item => (
              <li key={item.id} className="bg-white rounded-lg shadow-sm p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{item.image}</span>
                    <div>
                      <p className="font-medium text-gray-800">{item.name}</p>
                      <p className="text-sm text-gray-500">${item.price.toFixed(2)}</p>
                    </div>
                  </div>
                  <button onClick={() => removeItem(item.id)} className="text-red-400 text-sm hover:text-red-600">Remove</button>
                </div>
                <div className="flex items-center justify-between mt-3">
                  <div className="flex items-center gap-3">
                    <button onClick={() => updateQty(item.id, -1)} className="w-8 h-8 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center">−</button>
                    <span className="w-8 text-center font-medium">{item.qty}</span>
                    <button onClick={() => updateQty(item.id, 1)} className="w-8 h-8 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center">+</button>
                  </div>
                  <p className="font-semibold">${(item.price * item.qty).toFixed(2)}</p>
                </div>
              </li>
            ))}
          </ul>
          <div className="bg-white rounded-lg shadow-sm p-4">
            <div className="flex justify-between items-center mb-4">
              <span className="text-gray-600">Total</span>
              <span className="text-xl font-bold">${total.toFixed(2)}</span>
            </div>
            <button className="w-full bg-blue-500 text-white py-3 rounded-lg font-medium hover:bg-blue-600">
              Checkout
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default ShoppingCart;
