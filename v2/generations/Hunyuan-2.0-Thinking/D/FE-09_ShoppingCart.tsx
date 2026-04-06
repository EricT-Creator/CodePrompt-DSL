import React, { useState } from 'react';

interface Product {
  id: number;
  name: string;
  price: number;
}

interface CartItem extends Product {
  quantity: number;
}

const ShoppingCart: React.FC = () => {
  const [products] = useState<Product[]>([
    { id: 1, name: '无线耳机', price: 99.99 },
    { id: 2, name: '手机壳', price: 24.99 },
    { id: 3, name: '蓝牙音箱', price: 79.99 },
    { id: 4, name: '数据线', price: 12.99 }
  ]);
  
  const [cart, setCart] = useState<CartItem[]>([]);

  const addToCart = (product: Product) => {
    setCart(prev => {
      const existing = prev.find(item => item.id === product.id);
      if (existing) {
        return prev.map(item =>
          item.id === product.id ? { ...item, quantity: item.quantity + 1 } : item
        );
      }
      return [...prev, { ...product, quantity: 1 }];
    });
  };

  const updateQuantity = (id: number, delta: number) => {
    setCart(prev =>
      prev.map(item =>
        item.id === id ? { ...item, quantity: Math.max(0, item.quantity + delta) } : item
      ).filter(item => item.quantity > 0)
    );
  };

  const clearCart = () => {
    setCart([]);
  };

  const total = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white rounded-lg shadow-md">
      <h1 className="text-2xl font-bold mb-6">购物车</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h2 className="text-xl font-semibold mb-4">商品</h2>
          <div className="space-y-3">
            {products.map(product => (
              <div key={product.id} className="flex justify-between items-center p-3 border rounded">
                <div>
                  <h3 className="font-medium">{product.name}</h3>
                  <p className="text-gray-600">${product.price}</p>
                </div>
                <button
                  onClick={() => addToCart(product)}
                  className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                  加入购物车
                </button>
              </div>
            ))}
          </div>
        </div>
        
        <div>
          <h2 className="text-xl font-semibold mb-4">购物车</h2>
          {cart.length === 0 ? (
            <p>购物车为空</p>
          ) : (
            <div className="space-y-3">
              {cart.map(item => (
                <div key={item.id} className="flex justify-between items-center p-3 border rounded">
                  <div className="flex-1">
                    <h3 className="font-medium">{item.name}</h3>
                    <p className="text-gray-600">${item.price} × {item.quantity}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => updateQuantity(item.id, -1)}
                      className="px-2 py-1 bg-gray-200 rounded"
                    >-
                    </button>
                    <span>{item.quantity}</span>
                    <button
                      onClick={() => updateQuantity(item.id, 1)}
                      className="px-2 py-1 bg-gray-200 rounded"
                    >+
                    </button>
                  </div>
                </div>
              ))}
              
              <div className="border-t pt-3">
                <div className="flex justify-between font-bold text-lg">
                  <span>总计:</span>
                  <span>${total.toFixed(2)}</span>
                </div>
                <button
                  onClick={clearCart}
                  className="mt-3 w-full px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
                >
                  清空购物车
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ShoppingCart;