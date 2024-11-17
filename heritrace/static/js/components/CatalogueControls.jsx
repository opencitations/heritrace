import React, { useState } from 'react';
import SortControls from './SortControls';
import PaginationControls from './PaginationControls';

const CatalogueControls = ({ 
  initialPage,
  initialPerPage,
  totalPages: initialTotalPages,
  allowedPerPage,
  sortableProperties = [],
  initialSortProperty = undefined,
  initialSortDirection = 'ASC',
  selectedClass,
  onDataUpdate
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [currentPerPage, setCurrentPerPage] = useState(initialPerPage);
  const [totalPages, setTotalPages] = useState(initialTotalPages);
  const [sortProperty, setSortProperty] = useState(initialSortProperty);
  const [sortDirection, setSortDirection] = useState(initialSortDirection);

  const fetchData = async (page, perPage, property, direction) => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        class: selectedClass,
        page: page,
        per_page: perPage,
        sort_property: property,
        sort_direction: direction
      });

      const response = await fetch(`/api/catalogue?${params}`);
      if (!response.ok) throw new Error('Network response was not ok');
      const data = await response.json();
      
      // Update local state
      setCurrentPage(data.current_page);
      setTotalPages(data.total_pages);
      setCurrentPerPage(data.per_page);
      setSortProperty(data.sort_property);
      setSortDirection(data.sort_direction);

      // Update URL params without reloading
      const url = new URL(window.location);
      url.searchParams.set('page', data.current_page);
      url.searchParams.set('per_page', data.per_page);
      if (data.sort_property) {
        url.searchParams.set('sort_property', data.sort_property);
        url.searchParams.set('sort_direction', data.sort_direction);
      }
      window.history.pushState({}, '', url);

      onDataUpdate(data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePageChange = (newPage) => {
    fetchData(newPage, currentPerPage, sortProperty, sortDirection);
  };

  const handlePerPageChange = (newPerPage) => {
    fetchData(1, newPerPage, sortProperty, sortDirection);
  };

  const handleSortChange = (property, direction) => {
    fetchData(currentPage, currentPerPage, property, direction);
  };

  if (isLoading) {
    return (
      <div className="d-flex justify-content-center my-3">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="mb-3">
      {sortableProperties?.length > 0 && (
        <div className="mb-3">
          <SortControls
            sortableProperties={sortableProperties}
            currentProperty={sortProperty}
            currentDirection={sortDirection}
            onSortChange={handleSortChange}
          />
        </div>
      )}
      
      <PaginationControls
        currentPage={currentPage}
        totalPages={totalPages}
        itemsPerPage={currentPerPage}
        allowedPerPage={allowedPerPage}
        onPageChange={handlePageChange}
        onPerPageChange={handlePerPageChange}
      />
    </div>
  );
};

export default CatalogueControls;