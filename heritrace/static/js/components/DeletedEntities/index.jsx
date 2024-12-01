import React, { StrictMode } from 'react';
import ReactDOM from 'react-dom/client';
import CatalogueInterface from '../Catalogue/CatalogueInterface';

const timeVaultElement = document.getElementById('time-vault');

if (timeVaultElement) {
  const {
    selectedClass,
    initialPage,
    initialPerPage,
    allowedPerPage,
    sortableProperties,
    initialSortProperty,
    initialSortDirection,
  } = timeVaultElement.dataset;

  // Parse JSON data
  const parsedAllowedPerPage = JSON.parse(allowedPerPage);
  const parsedSortableProperties = JSON.parse(sortableProperties);

  // Convert string attributes to appropriate types
  const parsedInitialPage = parseInt(initialPage, 10);
  const parsedInitialPerPage = parseInt(initialPerPage, 10);

  // Create root and render
  const root = ReactDOM.createRoot(timeVaultElement);
  root.render(
    <StrictMode>
      <CatalogueInterface
        initialClasses={[]} // Classes will be fetched from the API
        initialSelectedClass={selectedClass}
        initialPage={parsedInitialPage}
        initialPerPage={parsedInitialPerPage}
        initialTotalPages={0}
        allowedPerPage={parsedAllowedPerPage}
        sortableProperties={parsedSortableProperties}
        initialSortProperty={initialSortProperty}
        initialSortDirection={initialSortDirection}
        isTimeVault={true}
      />
    </StrictMode>
  );
}