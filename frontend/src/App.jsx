import React, { useState } from 'react';
import ElementList from './components/ElementList.jsx';
import ElementDetail from './components/ElementDetail.jsx';
import ElementForm from './components/ElementForm.jsx';

// Root component coordinating the sidebar list and the main panel for
// displaying or creating elements. State for the selected element ID and
// refresh counter is managed here.

export default function App() {
  const [selectedId, setSelectedId] = useState(null);
  const [refresh, setRefresh] = useState(0);

  return (
    <div style={{ display: 'flex', height: '100vh', fontFamily: 'sans-serif' }}>
      <aside style={{ width: 360, borderRight: '1px solid #ccc', padding: 8, overflowY: 'auto' }}>
        <ElementList
          key={refresh}
          onSelect={(id) => {
            setSelectedId(id);
          }}
          onCreate={() => {
            setSelectedId(null);
          }}
        />
      </aside>
      <main style={{ flex: 1, padding: 16, overflowY: 'auto' }}>
        {selectedId ? (
          <ElementDetail
            id={selectedId}
            onUpdated={() => {
              setRefresh((r) => r + 1);
            }}
          />
        ) : (
          <ElementForm
            onCreated={() => {
              setRefresh((r) => r + 1);
            }}
          />
        )}
      </main>
    </div>
  );
}