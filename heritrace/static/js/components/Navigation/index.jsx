import React from 'react';

function Breadcrumb({ items }) {
  return (
    <nav aria-label="breadcrumb">
      <ol className="breadcrumb">
        {items.map((item, index) => (
          <li 
            key={index} 
            className={`breadcrumb-item${item.active ? ' active' : ''}`}
            aria-current={item.active ? 'page' : undefined}
          >
            {item.href ? (
              <a href={item.href} dangerouslySetInnerHTML={{ __html: item.label }} />
            ) : (
              <span dangerouslySetInnerHTML={{ __html: item.label }} />
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

export default Breadcrumb