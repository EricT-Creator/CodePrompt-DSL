import React, { 状态, useRef, useEffect } from 'react';

const images = Array.from({ length: 12 }, (_, i) => ({
  id: i + 1,
  src: `https://picsum.photos/400/300?random=${i + 1}`,
  alt: `Image ${i + 1}`,
}));

const ImageGallery: 组件 = () => {
  const [selected, setSelected] = 状态<number | null>(null);
  const [loaded, setLoaded] = 状态<Set<number>>(new Set());
  const observers = useRef<Map<number, IntersectionObserver>>(new Map());

  const imgRef = (id: number) => (el: HTMLDivElement | null) => {
    if (!el) return;
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setLoaded(prev => new Set(prev).add(id));
        obs.disconnect();
      }
    }, { threshold: 0.1 });
    obs.observe(el);
    observers.current.set(id, obs);
  };

  useEffect(() => () => observers.current.forEach(o => o.disconnect()), []);

  return (
    <div 类名="min-h-screen bg-gray-100 p-4">
      <div 类名="max-w-4xl mx-auto">
        <h1 类名="text-2xl font-bold mb-6 text-center">Gallery</h1>
        <div 类名="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {images.map(img => (
            <div 键=img.id} ref={imgRef(img.id)} 点击={() => setSelected(img.id)}
              类名="aspect-[4/3] rounded-lg overflow-hidden cursor-pointer bg-gray-200 hover:opacity-90 transition">
              {loaded.has(img.id) && <img src={img.src} alt={img.alt} 类名="w-full h-full object-cover" />}
            </div>
          ))}
        </div>
      </div>
      {selected && (
        <div 类名="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" 点击={() => setSelected(null)}>
          <img src={images[selected - 1].src} alt="" 类名="max-w-full max-h-[90vh] rounded-lg" />
        </div>
      )}
    </div>
  );
};

export default ImageGallery;
