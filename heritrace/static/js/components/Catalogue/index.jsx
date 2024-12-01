import React, { StrictMode } from 'react';
import ReactDOM from 'react-dom/client';
import CatalogueInterface from './CatalogueInterface';

// Get the catalogue element
const catalogueElement = document.getElementById('catalogue');

if (catalogueElement) {
  // Get data from the page
  const availableClasses = catalogueElement.dataset.availableClasses ? 
    JSON.parse(catalogueElement.dataset.availableClasses) : [];
  
  const {
    selectedClass,
    initialPage,
    initialPerPage,
    totalPages,
    allowedPerPage,
    sortableProperties,
    initialSortProperty,
    initialSortDirection,
  } = catalogueElement.dataset;

  // Parse JSON data
  const parsedAllowedPerPage = JSON.parse(allowedPerPage);
  const parsedSortableProperties = JSON.parse(sortableProperties);

  // Convert string attributes to appropriate types
  const parsedInitialPage = parseInt(initialPage, 10);
  const parsedInitialPerPage = parseInt(initialPerPage, 10);
  const parsedTotalPages = parseInt(totalPages, 10);

  // Create root and render
  const root = ReactDOM.createRoot(catalogueElement);
  root.render(
    <StrictMode>
      <CatalogueInterface
        initialClasses={availableClasses}
        initialSelectedClass={selectedClass}
        initialPage={parsedInitialPage}
        initialPerPage={parsedInitialPerPage}
        initialTotalPages={parsedTotalPages}
        allowedPerPage={parsedAllowedPerPage}
        sortableProperties={parsedSortableProperties}
        initialSortProperty={initialSortProperty}
        initialSortDirection={initialSortDirection}
        isTimeVault={false}
      />
    </StrictMode>
  );
}