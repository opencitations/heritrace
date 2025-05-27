import React from 'react';
import { SortAsc } from 'lucide-react';

const SortControls = ({ 
  sortableProperties, 
  currentProperty, 
  currentDirection, 
  onSortChange
}) => {
  if (!sortableProperties || sortableProperties.length === 0) {
    return null;
  }

  const handlePropertyChange = (e) => {
    const select = e.target;
    const newProperty = select.value;
    onSortChange(newProperty, currentDirection);
  };

  const toggleDirection = () => {
    const newDirection = currentDirection === 'ASC' ? 'DESC' : 'ASC';
    onSortChange(currentProperty, newDirection);
  };

  return (
    <div className="d-flex align-items-center gap-2">
      <label htmlFor="sort_property" className="form-label mb-0">Sort by:</label>
      <select
        id="sort_property"
        className="form-select form-select-sm"
        style={{ width: 'auto' }}
        value={currentProperty || ''}
        onChange={handlePropertyChange}
        data-sort-property={currentProperty || ''}
        data-sort-direction={currentDirection}
      >
        {sortableProperties.map((prop) => (
          <option key={prop.property} value={prop.property}>
            {prop.displayName}
          </option>
        ))}
      </select>

      <button 
        className="btn btn-sm btn-outline-secondary d-flex align-items-center justify-content-center toggleSortDirection"
        onClick={toggleDirection}
        title={`Change sort direction`}
        style={{ width: '32px', height: '32px', padding: 0 }}
        data-sort-property={currentProperty || ''}
        data-sort-direction={currentDirection}
      >
        <SortAsc 
          size={16} 
          style={{ 
            transform: currentDirection === 'DESC' ? 'scaleY(-1)' : 'none'
          }} 
        />
      </button>
    </div>
  );
};

export default SortControls;