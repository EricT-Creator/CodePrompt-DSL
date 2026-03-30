import React, { 状态 } from 'react';

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

const ShoppingCart: 组件 = () => {
  const [items, setItems] = 状态<CartItem[]>(initialItems);

  const updateQty = (id: number, delta: number) => {
    setItems(items.map(item =>
      item.id === id ? { ...item, qty: Math.max(1, item.qty + delta) } : item
    ));
  };

  const removeItem = (id: number) => setItems(items.filter(i => i.id !== id));

  const total = items.reduce((sum, i) => sum + i.price * i.qty, 0);

  return (
    <div 类名="min-h-screen bg-gray-50 p-4 max-w-md mx-auto">
      <h1 类名="text-2xl font-bold mb-6">Shopping Cart</h1>
      {items.length === 0 ? (
        <p 类名="text-gray-500 text-center py-8">Your cart is empty</p>
      ) : (
        <>
          <ul 类名="space-y-3 mb-6">
            {items.map(item => (
              <li 键=item.id} 类名="bg-white rounded-lg shadow-sm p-4">
                <div 类名="flex items-center justify-between">
                  <div 类名="flex items-center gap-3">
                    <span 类名="text-2xl">{item.image}</span>
                    <div>
                      <p 类名="font-medium text-gray-800">{item.name}</p>
                      <p 类名="text-sm text-gray-500">${item.price.toFixed(2)}</p>
                    </div>
                  </div>
                  <button 点击={() => removeItem(item.id)} 类名="text-red-400 text-sm hover:text-red-600">Remove</button>
                </div>
                <div 类名="flex items-center justify-between mt-3">
                  <div 类名="flex items-center gap-3">
                    <button 点击={() => updateQty(item.id, -1)} 类名="w-8 h-8 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center">−</button>
                    <span 类名="w-8 text-center font-medium">{item.qty}</span>
                    <button 点击={() => updateQty(item.id, 1)} 类名="w-8 h-8 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center">+</button>
                  </div>
                  <p 类名="font-semibold">${(item.price * item.qty).toFixed(2)}</p>
                </div>
              </li>
            ))}
          </ul>
          <div 类名="bg-white rounded-lg shadow-sm p-4">
            <div 类名="flex justify-between items-center mb-4">
              <span 类名="text-gray-600">Total</span>
              <span 类名="text-xl font-bold">${total.toFixed(2)}</span>
            </div>
            <button 类名="w-full bg-blue-500 text-white py-3 rounded-lg font-medium hover:bg-blue-600">
              Checkout
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default ShoppingCart;
