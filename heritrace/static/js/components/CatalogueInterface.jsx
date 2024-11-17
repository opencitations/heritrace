import React, { useState, useEffect } from 'react';
import { SortAsc } from 'lucide-react';
import CatalogueControls from './CatalogueControls';

const CatalogueInterface = ({
  initialClasses,
  initialSelectedClass,
  initialPage,
  initialPerPage,
  initialTotalPages,
  allowedPerPage,
  sortableProperties: initialSortableProperties,
  initialSortProperty,
  initialSortDirection
}) => {
  const [classes, setClasses] = useState(initialClasses);
  const [selectedClass, setSelectedClass] = useState(
    initialSelectedClass || (initialClasses.length > 0 ? initialClasses[0].uri : null)
  );
  const [filteredClasses, setFilteredClasses] = useState(initialClasses);
  const [isLoading, setIsLoading] = useState(false);
  const [entities, setEntities] = useState([]);
  const [sortDirection, setSortDirection] = useState('ASC');
  const [sortableProperties, setSortableProperties] = useState(initialSortableProperties || []);

  useEffect(() => {
    const sorted = [...classes].sort((a, b) => {
      return sortDirection === 'ASC' 
        ? a.label.localeCompare(b.label)
        : b.label.localeCompare(a.label);
    });
    
    setFilteredClasses(sorted);
  }, [classes, sortDirection]);

  useEffect(() => {
    const fetchEntitiesAndProperties = async () => {
      if (!selectedClass) return;
      setIsLoading(true);
      try {
        const params = new URLSearchParams({
          class: selectedClass,
          page: '1',
          per_page: initialPerPage,
          sort_property: initialSortProperty || sortableProperties[0]?.property,
          sort_direction: initialSortDirection || 'ASC'
        });
        
        const response = await fetch(`/api/catalogue?${params}`);
        const data = await response.json();
        setEntities(data.entities);
        setSortableProperties(data.sortable_properties);

        const url = new URL(window.location);
        url.searchParams.set('class', selectedClass);
        url.searchParams.set('page', '1');
        window.history.pushState({}, '', url);
      } catch (error) {
        console.error('Error fetching entities:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchEntitiesAndProperties();
  }, [selectedClass]);

  const handleClassClick = async (classUri) => {
    setIsLoading(true);
    setSelectedClass(classUri);
    
    try {
      const response = await fetch(`/api/catalogue?class=${encodeURIComponent(classUri)}&page=1&per_page=${initialPerPage}`);
      const data = await response.json();
      setEntities(data.entities);
      setSortableProperties(data.sortable_properties);
      
      const url = new URL(window.location);
      url.searchParams.set('class', classUri);
      url.searchParams.set('page', '1');
      window.history.pushState({}, '', url);
    } catch (error) {
      console.error('Error fetching entities:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDataUpdate = (data) => {
    setEntities(data.entities);
  };

  return (
    <div className="row">
      {/* Classes Panel */}
      <div className="col-md-4">
        <div className="card mb-4">
          <div className="card-header bg-light">
            <div className="d-flex justify-content-between align-items-center">
              <h5 className="mb-0">Categories</h5>
              <button 
                className="btn btn-sm btn-outline-secondary d-flex align-items-center justify-content-center"
                style={{ width: '32px', height: '32px', padding: 0 }}
                onClick={() => setSortDirection(prev => prev === 'ASC' ? 'DESC' : 'ASC')}
                title={`Sort ${sortDirection === 'ASC' ? 'A-Z' : 'Z-A'}`}
              >
                <SortAsc 
                  size={16} 
                  style={{ 
                    transform: sortDirection === 'DESC' ? 'scaleY(-1)' : 'none'
                  }} 
                />
              </button>
            </div>
          </div>
          <div className="card-body p-0">
            <div className="list-group list-group-flush">
              {filteredClasses.map((cls) => (
                <button
                  key={cls.uri}
                  onClick={() => handleClassClick(cls.uri)}
                  className={`list-group-item list-group-item-action d-flex justify-content-between align-items-center ${
                    cls.uri === selectedClass ? 'active' : ''
                  }`}
                >
                  <span>{cls.label}</span>
                  <span className="badge bg-primary rounded-pill">
                    {cls.count}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Entities Panel */}
      <div className="col-md-8">
        {selectedClass && (
          <>
            <h3 className="mb-3">
              Items in category: {classes.find(c => c.uri === selectedClass)?.label}
            </h3>
            
            {isLoading ? (
              <div className="d-flex justify-content-center my-3">
                <div className="spinner-border text-primary" role="status">
                  <span className="visually-hidden">Loading...</span>
                </div>
              </div>
            ) : (
              <>
                <CatalogueControls
                  initialPage={initialPage}
                  initialPerPage={initialPerPage}
                  totalPages={initialTotalPages}
                  allowedPerPage={allowedPerPage}
                  sortableProperties={sortableProperties}
                  initialSortProperty={sortableProperties.length > 0 ? sortableProperties[0].property : null}
                  initialSortDirection={initialSortDirection}
                  selectedClass={selectedClass}
                  onDataUpdate={handleDataUpdate}
                />

                {entities.length > 0 ? (
                  <div className="list-group">
                    {entities.map((entity) => (
                      <a
                        key={entity.uri}
                        href={`/about/${encodeURIComponent(entity.uri)}`}
                        className="list-group-item list-group-item-action"
                      >
                        {entity.label}
                      </a>
                    ))}
                  </div>
                ) : (
                  <p className="alert alert-info">No entities found for this class</p>
                )}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default CatalogueInterface;