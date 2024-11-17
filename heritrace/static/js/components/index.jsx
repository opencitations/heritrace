import React, { StrictMode } from 'react';
import ReactDOM from 'react-dom/client';
import CatalogueControls from './CatalogueControls';

// Get the element to render into
const catalogueControlsElement = document.getElementById('catalogueControls');

if (catalogueControlsElement) {
  // Extract data attributes
  const {
    initialPage,
    initialPerPage,
    totalPages,
    allowedPerPage,
    sortableProperties,
    initialSortProperty,
    initialSortDirection,
    selectedClass,
  } = catalogueControlsElement.dataset;

  // Parse JSON data
  const parsedAllowedPerPage = JSON.parse(allowedPerPage);
  const parsedSortableProperties = JSON.parse(sortableProperties);

  // Convert string attributes to appropriate types
  const parsedInitialPage = parseInt(initialPage, 10);
  const parsedInitialPerPage = parseInt(initialPerPage, 10);
  const parsedTotalPages = parseInt(totalPages, 10);

  const onDataUpdate = (data) => {
    // Update the entity list in the DOM
    const entityListElement = document.getElementById('entityList');
    if (entityListElement) {
      const entityItems = data.entities.map(entity => `
        <li class="list-group-item">
          <a href="/about/${encodeURIComponent(entity.uri)}">
            ${entity.label}
          </a>
        </li>
      `);
  
      entityListElement.innerHTML = `
        <ul class="list-group mb-4">
          ${entityItems.join('')}
        </ul>
      `;
    }
  };
    
  // Render the component
  const root = ReactDOM.createRoot(catalogueControlsElement);
  root.render(
    <StrictMode>
      <CatalogueControls
        initialPage={parsedInitialPage}
        initialPerPage={parsedInitialPerPage}
        totalPages={parsedTotalPages}
        allowedPerPage={parsedAllowedPerPage}
        sortableProperties={parsedSortableProperties}
        initialSortProperty={initialSortProperty}
        initialSortDirection={initialSortDirection}
        selectedClass={selectedClass}
        onDataUpdate={onDataUpdate}
      />
    </StrictMode>
  );
}
