import React, { StrictMode } from 'react';
import ReactDOM from 'react-dom/client';
import DeletedEntitiesInterface from './DeletedEntitiesInterface';

const deletedEntitiesElement = document.getElementById('deleted-entities-root');

if (deletedEntitiesElement) {
  const root = ReactDOM.createRoot(deletedEntitiesElement);
  root.render(
    <StrictMode>
      <DeletedEntitiesInterface />
    </StrictMode>
  );
}