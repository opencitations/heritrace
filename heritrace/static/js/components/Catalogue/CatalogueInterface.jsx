import React, { useState, useEffect } from 'react';
import { SortAsc } from 'lucide-react';
import CatalogueControls from './CatalogueControls';
import RestoreVersionButton from '../DeletedEntities/RestoreVersionButton'; // Ensure this is imported

const CatalogueInterface = ({
  initialClasses,
  initialSelectedClass,
  initialPage,
  initialPerPage,
  initialTotalPages,
  allowedPerPage,
  sortableProperties: initialSortableProperties,
  initialSortProperty,
  initialSortDirection,
  isTimeVault = false
}) => {
  const urlParams = new URLSearchParams(window.location.search);
  const [classes, setClasses] = useState(initialClasses);
  const [selectedClass, setSelectedClass] = useState(
    urlParams.get('class') || initialSelectedClass || (initialClasses.length > 0 ? initialClasses[0].uri : null)
  );
  const [filteredClasses, setFilteredClasses] = useState(initialClasses);
  const [isLoading, setIsLoading] = useState(false);
  const [entities, setEntities] = useState([]);
  const [sortDirection, setSortDirection] = useState(urlParams.get('sort_direction') || 'ASC');
  const [sortableProperties, setSortableProperties] = useState(initialSortableProperties || []);

  const [currentPage, setCurrentPage] = useState(parseInt(urlParams.get('page')) || initialPage);
  const [currentPerPage, setCurrentPerPage] = useState(parseInt(urlParams.get('per_page')) || initialPerPage);
  const [sortProperty, setSortProperty] = useState(
    urlParams.get('sort_property') || initialSortProperty || (sortableProperties.length > 0 ? sortableProperties[0].property : null)
  );
  const [totalPages, setTotalPages] = useState(initialTotalPages || 0);

  const apiEndpoint = isTimeVault ? '/api/time-vault' : '/api/catalogue';

  const fetchEntitiesAndProperties = async () => {
    if (!selectedClass) return;
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        class: selectedClass,
        page: currentPage,
        per_page: currentPerPage,
        sort_property: sortProperty || initialSortProperty,
        sort_direction: sortDirection || initialSortDirection,
      });
      
      const response = await fetch(`${apiEndpoint}?${params}`);
      const data = await response.json();
      setEntities(data.entities);
      setSortableProperties(data.sortable_properties || initialSortableProperties);
      setTotalPages(data.total_pages);
      setCurrentPage(data.current_page);
      setCurrentPerPage(data.per_page);

      // Update URL
      const url = new URL(window.location);
      url.searchParams.set('class', selectedClass);
      url.searchParams.set('page', data.current_page);
      window.history.pushState({}, '', url);
    } catch (error) {
      console.error('Error fetching entities:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const sorted = [...classes].sort((a, b) => {
      return sortDirection === 'ASC' 
        ? a.label.localeCompare(b.label)
        : b.label.localeCompare(a.label);
    });
    
    setFilteredClasses(sorted);
  }, [classes, sortDirection]);

  useEffect(() => {
    const fetchClassesAndEntities = async () => {
      setIsLoading(true);
      try {
        // Fetch available classes if not provided
        let classesData = initialClasses;
        if (!initialClasses || initialClasses.length === 0) {
          const response = await fetch(`${apiEndpoint}?class=&page=1&per_page=${initialPerPage}`);
          const data = await response.json();
          classesData = data.available_classes || [];
        }

        setClasses(classesData);

        if (!selectedClass && classesData.length > 0) {
          setSelectedClass(classesData[0].uri);
        }
      } catch (error) {
        console.error('Error fetching classes:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchClassesAndEntities();
  }, [isTimeVault]);

  useEffect(() => {
    fetchEntitiesAndProperties();
  }, [selectedClass, currentPage, currentPerPage, sortProperty, sortDirection]);

  const handleClassClick = async (classUri) => {
    setIsLoading(true);
    setSelectedClass(classUri);
    setCurrentPage(1); // Reset to first page when class changes
  
    try {
      const params = new URLSearchParams({
        class: classUri,
        page: '1',
        per_page: currentPerPage,
        sort_property: sortProperty || initialSortProperty,
        sort_direction: sortDirection || initialSortDirection,
      });
      const response = await fetch(`${apiEndpoint}?${params}`);
      const data = await response.json();
      setEntities(data.entities);
      setSortableProperties(data.sortable_properties || initialSortableProperties);
      setTotalPages(data.total_pages);
      setCurrentPage(data.current_page);
      setCurrentPerPage(data.per_page);
  
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
              {isTimeVault ? 'Deleted Resources in category:' : 'Items in category:'} {classes.find(c => c.uri === selectedClass)?.label}
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
                  isTimeVault={isTimeVault}
                />

                {entities.length > 0 ? (
                  <div className="list-group">
                    {entities.map((entity) => (
                      <div key={entity.uri} className="list-group-item">
                        <div className="d-flex justify-content-between align-items-center">
                          <a
                            href={isTimeVault ? `/entity-version/${encodeURIComponent(entity.uri)}/${entity.lastValidSnapshotTime}` : `/about/${encodeURIComponent(entity.uri)}`}
                            className="text-decoration-none"
                          >
                            {entity.label}
                          </a>
                          {isTimeVault && (
                            <RestoreVersionButton 
                              entityUri={entity.uri}
                              timestamp={entity.lastValidSnapshotTime}
                            />
                          )}
                        </div>
                        {isTimeVault && (
                          <small className="text-muted">
                            Deleted on: {new Date(entity.deletionTime).toLocaleString()}
                          </small>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="alert alert-info">No {isTimeVault ? 'deleted ' : ''}entities found for this class</p>
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