import React, { useEffect, useState } from 'react';
import { listElements } from '../api.js';

// Sidebar component displaying a list of elements. Clicking on an item
// triggers onSelect. The parent controls refresh by changing key on the
// component, causing it to refetch data.

export default function ElementList({ onSelect, onCreate }) {
  const [elements, setElements] = useState([]);

  useEffect(() => {
    listElements({ limit: 200 }).then((r) => setElements(r.elements));
  }, []);

  return (
    <div>
      <button onClick={onCreate} style={{ marginBottom: 8 }}>＋ New</button>
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {elements.map((e) => (
          <li
            key={e.id}
            onClick={() => onSelect(e.id)}
            style={{ padding: '4px 0', cursor: 'pointer' }}
          >
            <span style={{ fontWeight: 'bold' }}>{e.type}</span>
            {e.format && e.format !== 'plain' ? (
              <span style={{ color: '#555' }}>[{e.format}]</span>
            ) : null}{' '}
            — {e.title}
          </li>
        ))}
      </ul>
    </div>
  );
}