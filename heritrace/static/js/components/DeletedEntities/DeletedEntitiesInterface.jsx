import React, { useState, useEffect } from 'react';
import RestoreVersionButton from './RestoreVersionButton';
import SortControls from '../Catalogue/SortControls';

function DeletedEntitiesInterface() {
  const [deletedEntities, setDeletedEntities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sortConfig, setSortConfig] = useState({
    property: 'deletionTime',
    direction: 'DESC'
  });

  useEffect(() => {
    fetchDeletedEntities();
  }, []);

  const fetchDeletedEntities = async () => {
    try {
      const response = await fetch('/api/deleted-entities');
      if (!response.ok) throw new Error('Failed to fetch deleted resources');
      const data = await response.json();
      setDeletedEntities(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const sortableProperties = [
    { property: 'deletionTime', displayName: 'Deletion Time' },
    { property: 'type', displayName: 'Resource Type' },
    { property: 'label', displayName: 'Label' }
  ];

  const handleSortChange = (property, direction) => {
    setSortConfig({ property, direction });
  };

  const getSortedEntities = () => {
    const { property, direction } = sortConfig;
    return [...deletedEntities].sort((a, b) => {
      let comparison = 0;
      if (property === 'deletionTime') {
        comparison = new Date(a.deletionTime) - new Date(b.deletionTime);
      } else {
        comparison = a[property].localeCompare(b[property]);
      }
      return direction === 'ASC' ? comparison : -comparison;
    });
  };

  const renderDeletedBy = (htmlContent) => {
    return { __html: htmlContent };
  };

  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ height: '200px' }}>
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-danger" role="alert">
        <h4 className="alert-heading">Error</h4>
        <p className="mb-0">{error}</p>
      </div>
    );
  }

  const sortedEntities = getSortedEntities();

  return (
    <>
      <div className="d-flex align-items-center justify-content-between mb-4">
        <div>
          <h2 className="mb-2">Time Vault - Deleted Resources</h2>
          <p className="text-muted">
            <i className="bi bi-info-circle me-2"></i>
            Here you can find and restore deleted resources
          </p>
        </div>
        {deletedEntities.length > 0 && (
          <SortControls
            sortableProperties={sortableProperties}
            currentProperty={sortConfig.property}
            currentDirection={sortConfig.direction}
            onSortChange={handleSortChange}
          />
        )}
      </div>

      {deletedEntities.length === 0 ? (
        <div className="alert alert-info" role="alert">
          <div className="d-flex">
            <i className="bi bi-clock-history fs-4 me-3"></i>
            <div>
              <h4 className="alert-heading">No Deleted Resources Found</h4>
              <p className="mb-0">
                The Time Vault is currently empty. When you delete resources, they will be stored here and can be restored
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="row row-cols-1 row-cols-md-2 g-4">
          {sortedEntities.map((entity) => (
            <div className="col" key={entity.uri}>
              <div className="card h-100 shadow-sm">
                <div className="card-body">
                  <h5 className="card-title text-primary mb-3">
                    {entity.label || entity.uri}
                  </h5>
                  <div className="mb-3">
                    <p className="mb-1">
                      <i className="bi bi-tag me-2"></i>
                      <strong>Resource Type:</strong> {entity.type}
                    </p>
                    <p className="mb-1">
                      <i className="bi bi-person me-2"></i>
                      <strong>Deleted By:</strong>{' '}
                      <span dangerouslySetInnerHTML={renderDeletedBy(entity.deletedBy)} />
                    </p>
                    <p className="mb-1">
                      <i className="bi bi-calendar me-2"></i>
                      <strong>Deletion Time:</strong><br/>
                      <span className="ms-4">
                        {new Date(entity.deletionTime).toLocaleString()}
                      </span>
                    </p>
                  </div>
                  <div className="d-flex flex-column gap-2">
                    <a 
                      href={`/entity-version/${encodeURIComponent(entity.uri)}/${entity.lastValidSnapshotTime}`}
                      className="btn btn-outline-primary"
                      title="View the entity's state before deletion"
                    >
                      <i className="bi bi-clock-history me-2"></i>
                      View Last Valid State
                    </a>
                    <RestoreVersionButton 
                      entityUri={entity.uri}
                      timestamp={entity.lastValidSnapshotTime}
                    />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

export default DeletedEntitiesInterface;