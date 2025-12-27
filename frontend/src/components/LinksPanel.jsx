import React, { useEffect, useState } from 'react';
import { listLinksForElement, createLink } from '../api.js';

// LinksPanel lists existing links for the given element and allows adding
// new links. The user must enter a destination UUID and choose a relation
// type. After creation the list refreshes.

export default function LinksPanel({ elementId }) {
  const [links, setLinks] = useState([]);
  const [dst, setDst] = useState('');
  const [rel, setRel] = useState('uses');

  async function fetchLinks() {
    const r = await listLinksForElement(elementId);
    setLinks(r.links);
  }

  useEffect(() => {
    fetchLinks().catch((err) => console.error(err));
  }, [elementId]);

  async function handleAdd() {
    try {
      await createLink({ src_id: elementId, dst_id: dst.trim(), rel });
      setDst('');
      await fetchLinks();
    } catch (err) {
      alert(err.message);
    }
  }

  return (
    <div>
      <h4>Links</h4>
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {links.map((l) => (
          <li key={l.id} style={{ padding: '2px 0' }}>
            {l.rel}: {l.src_id} → {l.dst_id}
          </li>
        ))}
      </ul>
      <input
        placeholder="Destination UUID"
        value={dst}
        onChange={(e) => setDst(e.target.value)}
        style={{ width: '60%', marginRight: 4 }}
      />
      <select value={rel} onChange={(e) => setRel(e.target.value)} style={{ marginRight: 4 }}>
        {[
          'proves',
          'uses',
          'implies',
          'equivalent_to',
          'example_of',
          'counterexample_to',
          'related',
        ].map((r) => (
          <option key={r} value={r}>
            {r}
          </option>
        ))}
      </select>
      <button onClick={handleAdd}>Add link</button>
    </div>
  );
}