import React from 'react';
import { ArrowDown, ArrowUp } from 'lucide-react';

const SortControls = ({ 
  sortableProperties, 
  currentProperty, 
  currentDirection, 
  onSortChange 
}) => {
  const handlePropertyChange = (e) => {
    const newProperty = e.target.value;
    onSortChange(newProperty, currentDirection);
  };

  const toggleDirection = () => {
    const newDirection = currentDirection === 'ASC' ? 'DESC' : 'ASC';
    onSortChange(currentProperty, newDirection);
  };

  const getSortLabel = () => {
    const currentProp = sortableProperties.find(p => p.property === currentProperty);
    if (!currentProp) return { asc: 'Low-High', desc: 'High-Low' };

    // Se c'è una shape, indica che è una referenza a un'entità (label)
    if (currentProp.shape) {
      return {
        asc: 'A-Z',
        desc: 'Z-A'
      };
    }
    // Controlla il tipo di dato dalla configurazione di sortableBy
    switch (currentProp.sortType?.toLowerCase()) {
      case 'date':
        return {
          asc: 'Oldest first',
          desc: 'Newest first'
        };
      case 'number':
        return {
          asc: 'Low-High',
          desc: 'High-Low'
        };
      default:
        return {
          asc: 'A-Z',
          desc: 'Z-A'
        };
    }
  };

  const sortLabels = getSortLabel();
  const currentLabel = currentDirection === 'ASC' ? sortLabels.asc : sortLabels.desc;

  return (
    <div className="d-flex align-items-center gap-2">
      <label htmlFor="sort_property" className="form-label mb-0">Sort by:</label>
      <select
        id="sort_property"
        className="form-select form-select-sm"
        style={{ width: 'auto' }}
        value={currentProperty || ''}
        onChange={handlePropertyChange}
      >
        {sortableProperties.map((prop) => (
          <option key={prop.property} value={prop.property}>
            {prop.displayName}
          </option>
        ))}
      </select>

      <button 
        className="btn btn-sm btn-outline-secondary d-flex align-items-center toggleSortDirection"
        onClick={toggleDirection}
        title={`Sort ${currentDirection === 'ASC' ? 'ascending' : 'descending'}`}
      >
        {currentDirection === 'ASC' ? (
          <>
            <ArrowUp size={16} />
            <span className="ms-1">{sortLabels.asc}</span>
          </>
        ) : (
          <>
            <ArrowDown size={16} />
            <span className="ms-1">{sortLabels.desc}</span>
          </>
        )}
      </button>
    </div>
  );
};

export default SortControls;