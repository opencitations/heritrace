import React from 'react';
import { ChevronFirst, ChevronLast, ChevronLeft, ChevronRight } from 'lucide-react';

const PaginationControls = ({ 
  currentPage, 
  totalPages, 
  itemsPerPage, 
  allowedPerPage, 
  onPageChange,
  onPerPageChange 
}) => {
  const handlePerPageChange = (e) => {
    const newPerPage = parseInt(e.target.value);
    onPerPageChange(newPerPage);
  };

  return (
    <div className="d-flex justify-content-between align-items-center">
      <div className="d-flex align-items-center">
        <label htmlFor="per_page" className="form-label me-2 mb-0">Items per page:</label>
        <select
          id="per_page"
          className="form-select form-select-sm"
          style={{ width: 'auto' }}
          value={itemsPerPage}
          onChange={handlePerPageChange}
          data-per-page={itemsPerPage}
          data-current-page={currentPage}
        >
          {allowedPerPage.map((pp) => (
            <option key={pp} value={pp}>{pp}</option>
          ))}
        </select>
      </div>

      {totalPages > 1 && (
        <nav aria-label="Pagination">
          <ul className="pagination pagination-sm mb-0">
            <li className={`page-item ${currentPage === 1 ? 'disabled' : ''}`}>
              <button 
                className="page-link" 
                onClick={() => onPageChange(1)}
                disabled={currentPage === 1}
                data-page="1"
                data-per-page={itemsPerPage}
              >
                <ChevronFirst size={16} />
              </button>
            </li>
            <li className={`page-item ${currentPage === 1 ? 'disabled' : ''}`}>
              <button 
                className="page-link" 
                onClick={() => onPageChange(currentPage - 1)}
                disabled={currentPage === 1}
                data-page={currentPage - 1}
                data-per-page={itemsPerPage}
              >
                <ChevronLeft size={16} />
              </button>
            </li>
            <li className="page-item active">
              <span className="page-link">{currentPage} / {totalPages}</span>
            </li>
            <li className={`page-item ${currentPage === totalPages ? 'disabled' : ''}`}>
              <button 
                className="page-link" 
                onClick={() => onPageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                data-page={currentPage + 1}
                data-per-page={itemsPerPage}
              >
                <ChevronRight size={16} />
              </button>
            </li>
            <li className={`page-item ${currentPage === totalPages ? 'disabled' : ''}`}>
              <button 
                className="page-link" 
                onClick={() => onPageChange(totalPages)}
                disabled={currentPage === totalPages}
                data-page={totalPages}
                data-per-page={itemsPerPage}
              >
                <ChevronLast size={16} />
              </button>
            </li>
          </ul>
        </nav>
      )}
    </div>
  );
};

export default PaginationControls;