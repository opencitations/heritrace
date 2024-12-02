import React, { useState } from 'react';
import { SortAsc } from 'lucide-react';
import SortControls from './SortControls';
import PaginationControls from './PaginationControls';
import RestoreVersionButton from './RestoreVersionButton';

const CatalogueInterface = ({
  initialClasses = [],
  initialSelectedClass,
  initialPage = 1,
  initialPerPage = 10,
  initialTotalPages = 0,
  allowedPerPage = [],
  sortableProperties: initialSortableProperties = [],
  initialSortProperty = null,
  initialSortDirection = 'ASC',
  initialEntities = [],
  isTimeVault = false
}) => {
  const urlParams = new URLSearchParams(window.location.search);
  const getUrlParam = (key, defaultValue) => {
    const value = urlParams.get(key);
    return value === 'None' || value === 'null' ? null : (value || defaultValue);
  };

  const [state, setState] = useState({
    classes: initialClasses,
    selectedClass: getUrlParam('class', initialSelectedClass || (initialClasses[0]?.uri ?? null)),
    entities: initialEntities,
    isLoading: false,
    classesListSortDirection: 'ASC',
    itemsSortDirection: getUrlParam('sort_direction', initialSortDirection),
    sortableProperties: initialSortableProperties,
    currentPage: parseInt(getUrlParam('page', initialPage)),
    currentPerPage: parseInt(getUrlParam('per_page', initialPerPage)),
    sortProperty: getUrlParam('sort_property', initialSortProperty),
    totalPages: initialTotalPages
  });

  const apiEndpoint = isTimeVault ? '/api/time-vault' : '/api/catalogue';

  const updateUrl = (params) => {
    const url = new URL(window.location);
    Object.entries(params).forEach(([key, value]) => {
      if (value) {
        url.searchParams.set(key, value);
      } else {
        url.searchParams.delete(key);
      }
    });
    window.history.pushState({}, '', url);
  };

  const fetchData = async (params = {}) => {
    setState(prev => ({ ...prev, isLoading: true }));
    try {
      const queryParams = new URLSearchParams({
        class: params.class || state.selectedClass,
        page: params.page || state.currentPage,
        per_page: params.perPage || state.currentPerPage,
        sort_property: params.sortProperty || state.sortProperty,
        sort_direction: params.sortDirection || state.itemsSortDirection
      });

      const response = await fetch(`${apiEndpoint}?${queryParams}`);
      const data = await response.json();

      setState(prev => ({
        ...prev,
        entities: data.entities || [],
        sortableProperties: data.sortable_properties || prev.sortableProperties,
        totalPages: data.total_pages,
        currentPage: data.current_page,
        currentPerPage: data.per_page,
        sortProperty: data.sort_property || prev.sortProperty,
        itemsSortDirection: data.sort_direction || prev.itemsSortDirection
      }));

      updateUrl({
        class: params.class || state.selectedClass,
        page: data.current_page,
        per_page: data.per_page,
        sort_property: data.sort_property,
        sort_direction: data.sort_direction
      });
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setState(prev => ({ ...prev, isLoading: false }));
    }
  };

  const handleClassClick = (classUri) => {
    if (classUri === state.selectedClass) return;
    setState(prev => ({ ...prev, selectedClass: classUri }));
    fetchData({ class: classUri, page: 1 });
  };

  const handleSortChange = (property, direction) => {
    if (property === state.sortProperty && direction === state.itemsSortDirection) return;
    fetchData({ sortProperty: property, sortDirection: direction });
  };

  const handlePageChange = (page) => {
    if (page === state.currentPage) return;
    fetchData({ page });
  };

  const handlePerPageChange = (perPage) => {
    if (perPage === state.currentPerPage) return;
    fetchData({ page: 1, perPage });
  };

  const toggleClassesSort = () => {
    setState(prev => ({
      ...prev,
      classesListSortDirection: prev.classesListSortDirection === 'ASC' ? 'DESC' : 'ASC'
    }));
  };

  const sortedClasses = [...state.classes].sort((a, b) => {
    return state.classesListSortDirection === 'ASC' 
      ? a.label.localeCompare(b.label)
      : b.label.localeCompare(a.label);
  });

  if (!state.selectedClass) {
    return <div className="alert alert-info">No data available</div>;
  }

  const selectedClassName = sortedClasses.find(c => c.uri === state.selectedClass)?.label;

  return (
    <div className="row">
      <div className="col-md-4">
        <div className="card mb-4">
          <div className="card-header bg-light">
            <div className="d-flex justify-content-between align-items-center">
              <h5 className="mb-0">Categories</h5>
              <button 
                className="btn btn-sm btn-outline-secondary d-flex align-items-center justify-content-center"
                style={{ width: '32px', height: '32px', padding: 0 }}
                onClick={toggleClassesSort}
                title={`Sort ${state.classesListSortDirection === 'ASC' ? 'A-Z' : 'Z-A'}`}
              >
                <SortAsc 
                  size={16} 
                  style={{ transform: state.classesListSortDirection === 'DESC' ? 'scaleY(-1)' : 'none' }} 
                />
              </button>
            </div>
          </div>
          <div className="card-body p-0">
            <div className="list-group list-group-flush">
              {sortedClasses.map((cls) => (
                <button
                  key={cls.uri}
                  onClick={() => handleClassClick(cls.uri)}
                  className={`list-group-item list-group-item-action d-flex justify-content-between align-items-center ${
                    cls.uri === state.selectedClass ? 'active' : ''
                  }`}
                >
                  <span>{cls.label}</span>
                  <span className="badge bg-primary rounded-pill">{cls.count}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="col-md-8">
        <h3 className="mb-3">
          {isTimeVault ? 'Deleted Resources in category:' : 'Items in category:'} {selectedClassName}
        </h3>
        
        {state.isLoading ? (
          <div className="d-flex justify-content-center my-3">
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
          </div>
        ) : (
          <>
            <div className="mb-3">
              {state.sortableProperties?.length > 0 && (
                <div className="mb-3">
                  <SortControls
                    sortableProperties={state.sortableProperties}
                    currentProperty={state.sortProperty}
                    currentDirection={state.itemsSortDirection}
                    onSortChange={handleSortChange}
                  />
                </div>
              )}
              
              <PaginationControls
                currentPage={state.currentPage}
                totalPages={state.totalPages}
                itemsPerPage={state.currentPerPage}
                allowedPerPage={allowedPerPage}
                onPageChange={handlePageChange}
                onPerPageChange={handlePerPageChange}
              />
            </div>

            {state.entities.length > 0 ? (
              <div className="list-group">
                {state.entities.map((entity) => (
                  <div key={entity.uri} className="list-group-item">
                    <div className="d-flex justify-content-between align-items-center">
                      <a
                        href={isTimeVault 
                          ? `/entity-version/${entity.uri}/${entity.lastValidSnapshotTime}`
                          : `/about/${entity.uri}`
                        }
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
      </div>
    </div>
  );
};

export default CatalogueInterface;