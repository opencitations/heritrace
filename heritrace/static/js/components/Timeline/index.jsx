import React from 'react';
import { createRoot } from 'react-dom/client';
import Timeline from './Timeline';

const rootElement = document.getElementById('entity-timeline-root');
if (rootElement) {
    const root = createRoot(rootElement);
    root.render(<Timeline timelineData={window.timelineData} />);
} else {
    console.error('Root element not found: entity-timeline-root');
}