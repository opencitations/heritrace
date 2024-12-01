import React, { StrictMode } from 'react';
import ReactDOM from 'react-dom/client';
import CatalogueInterface from './CatalogueInterface';

// Common function to parse dataset attributes
const parseDatasetAttributes = (element) => {
  const {
    selectedClass,
    initialPage,
    initialPerPage,
    totalPages,
    allowedPerPage,
    sortableProperties,
    initialSortProperty,
    initialSortDirection,
  } = element.dataset;

  return {
    selectedClass,
    initialPage: parseInt(initialPage, 10),
    initialPerPage: parseInt(initialPerPage, 10),
    totalPages: parseInt(totalPages || '0', 10),
    allowedPerPage: JSON.parse(allowedPerPage),
    sortableProperties: JSON.parse(sortableProperties),
    initialSortProperty,
    initialSortDirection
  };
};

// Initialize CatalogueInterface for either catalogue or time vault
const initializeCatalogue = (elementId, isTimeVault = false) => {
  const element = document.getElementById(elementId);
  
  if (element) {
    const parsedAttributes = parseDatasetAttributes(element);
    const initialClasses = element.dataset.availableClasses ? 
      JSON.parse(element.dataset.availableClasses) : [];

    const root = ReactDOM.createRoot(element);
    root.render(
      <StrictMode>
        <CatalogueInterface
          initialClasses={initialClasses}
          initialSelectedClass={parsedAttributes.selectedClass}
          initialPage={parsedAttributes.initialPage}
          initialPerPage={parsedAttributes.initialPerPage}
          initialTotalPages={parsedAttributes.totalPages}
          allowedPerPage={parsedAttributes.allowedPerPage}
          sortableProperties={parsedAttributes.sortableProperties}
          initialSortProperty={parsedAttributes.initialSortProperty}
          initialSortDirection={parsedAttributes.initialSortDirection}
          isTimeVault={isTimeVault}
        />
      </StrictMode>
    );
  }
};

// Initialize based on which element is present in the DOM
if (document.getElementById('catalogue')) {
  initializeCatalogue('catalogue', false);
} else if (document.getElementById('time-vault')) {
  initializeCatalogue('time-vault', true);
}