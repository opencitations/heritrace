import React from 'react';
import { createRoot } from 'react-dom/client';
import Breadcrumb from './Breadcrumb';

const breadcrumbElement = document.getElementById('breadcrumb-root');
if (breadcrumbElement) {
    const breadcrumbRoot = createRoot(breadcrumbElement);
    breadcrumbRoot.render(<Breadcrumb timelineData={window.timelineData} />);
} else {
    console.error('Root element not found: breadcrumb-root');
}