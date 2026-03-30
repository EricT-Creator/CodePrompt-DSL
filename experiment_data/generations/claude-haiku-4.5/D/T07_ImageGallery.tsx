import React, { useState } from 'react';

const ImageGallery: React.FC = () => {
  const [selected, setSelected] = useState<number | null>(null);
  const images = Array.from({ length: 12 }, (_, i) => `https://picsum.photos/300/300?random=${i}`);

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      <h1 className="text-3xl font-bold text-white mb-6">Image Gallery</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {images.map((img, i) => (
          <div
            key={i}
            onClick={() => setSelected(i)}
            className="aspect-square bg-gray-700 rounded-lg overflow-hidden cursor-pointer hover:scale-105 transition"
          >
            <img src={img} alt={`Gallery ${i}`} className="w-full h-full object-cover" />
          </div>
        ))}
      </div>
      {selected !== null && (
        <div className="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center p-4 z-50">
          <div className="relative max-w-4xl">
            <img src={images[selected]} alt="Selected" className="w-full h-auto rounded-lg" />
            <button
              onClick={() => setSelected(null)}
              className="absolute top-4 right-4 bg-white text-black rounded-full w-8 h-8 flex items-center justify-center"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ImageGallery;