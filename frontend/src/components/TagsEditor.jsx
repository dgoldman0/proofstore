import React, { useState, useEffect } from 'react';
import { setTags } from '../api.js';

// TagsEditor displays a comma-separated editable list of tags for an element.
// When the Save button is clicked, the tags are split, trimmed and saved via
// the API. onChange is called with the updated element (tags replaced).

export default function TagsEditor({ element, onChange }) {
  const [text, setText] = useState('');

  useEffect(() => {
    setText((element.tags || []).join(', '));
  }, [element.id]);

  async function handleSave() {
    const tags = text
      .split(',')
      .map((t) => t.trim())
      .filter((t) => t.length > 0);
    await setTags(element.id, tags);
    onChange({ ...element, tags });
  }

  return (
    <div>
      <h4>Tags</h4>
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        style={{ width: '100%', marginBottom: 4 }}
      />
      <button onClick={handleSave}>Save tags</button>
    </div>
  );
}