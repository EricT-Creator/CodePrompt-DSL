import React, { useState } from 'react';

interface Data {
  id: number;
  name: string;
  email: string;
  age: number;
}

const DataTable: React.FC = () => {
  const [data, setData] = useState<Data[]>([
    { id: 1, name: 'John', email: 'john@example.com', age: 28 },
    { id: 2, name: 'Jane', email: 'jane@example.com', age: 32 },
    { id: 3, name: 'Bob', email: 'bob@example.com', age: 25 },
    { id: 4, name: 'Alice', email: 'alice@example.com', age: 29 },
    { id: 5, name: 'Charlie', email: 'charlie@example.com', age: 31 },
  ]);
  const [sortBy, setSortBy] = useState<keyof Data>('name');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const perPage = 3;

  const filtered = data.filter(d => 
    d.name.toLowerCase().includes(search.toLowerCase()) ||
    d.email.toLowerCase().includes(search.toLowerCase())
  );
  const sorted = [...filtered].sort((a, b) => {
    const aVal = a[sortBy];
    const bVal = b[sortBy];
    return typeof aVal === 'string' ? aVal.localeCompare(bVal as string) : (aVal as number) - (bVal as number);
  });
  const paged = sorted.slice((page - 1) * perPage, page * perPage);
  const maxPage = Math.ceil(sorted.length / perPage);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <h1 className="text-3xl font-bold mb-4">Data Table</h1>
      <input
        type="text"
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="Search..."
        className="w-full px-4 py-2 border rounded mb-4"
      />
      <table className="w-full bg-white rounded-lg shadow">
        <thead>
          <tr className="border-b">
            {['name', 'email', 'age'].map(col => (
              <th key={col} onClick={() => setSortBy(col as keyof Data)} className="px-4 py-2 cursor-pointer hover:bg-gray-100 text-left">
                {col} ▼
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {paged.map(row => (
            <tr key={row.id} className="border-b">
              <td className="px-4 py-2">{row.name}</td>
              <td className="px-4 py-2">{row.email}</td>
              <td className="px-4 py-2">{row.age}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-4 flex justify-center gap-2">
        <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1} className="px-3 py-1 border rounded disabled:opacity-50">
          Prev
        </button>
        <span className="px-3 py-1">{page} of {maxPage}</span>
        <button onClick={() => setPage(Math.min(maxPage, page + 1))} disabled={page === maxPage} className="px-3 py-1 border rounded disabled:opacity-50">
          Next
        </button>
      </div>
    </div>
  );
};

export default DataTable;