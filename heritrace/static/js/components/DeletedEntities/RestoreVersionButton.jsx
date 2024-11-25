import React, { useState } from 'react';

function RestoreVersionButton({ entityUri, timestamp }) {
    const [isRestoring, setIsRestoring] = useState(false);

    const handleRestore = async () => {
      const Swal = window.Swal;
      
      try {
        const result = await Swal.fire({
          title: 'Restore Resource',
          text: 'Are you sure you want to restore this resource?',
          icon: 'question',
          showCancelButton: true,
          confirmButtonColor: '#3085d6',
          cancelButtonColor: '#d33',
          confirmButtonText: 'Yes, restore it!',
          cancelButtonText: 'Cancel'
        });
  
        if (!result.isConfirmed) {
          return;
        }
  
        setIsRestoring(true);
  
        Swal.fire({
          title: 'Restoring...',
          html: 'Please wait while we restore the version',
          allowOutsideClick: false,
          showConfirmButton: false,
          didOpen: () => {
            Swal.showLoading();
          }
        });
  
        const response = await fetch(`/restore-version/${encodeURIComponent(entityUri)}/${timestamp}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        });
  
        if (!response.ok) {
          throw new Error('Failed to restore version');
        }
  
        await Swal.fire({
          title: 'Success!',
          text: 'Version has been restored successfully',
          icon: 'success',
          confirmButtonText: 'View Entity'
        });
  
        window.location.href = `/about/${encodeURIComponent(entityUri)}`;
      } catch (error) {
        console.error('Error restoring version:', error);
        await Swal.fire({
          title: 'Error!',
          text: 'Failed to restore version. Please try again',
          icon: 'error',
          confirmButtonText: 'OK'
        });
      } finally {
        setIsRestoring(false);
      }
    };
  
    return (
      <button
        onClick={handleRestore}
        className="btn btn-primary"
        disabled={isRestoring}
        title="Restore this entity to its last valid state"
      >
        <i className={`bi ${isRestoring ? 'bi-hourglass-split' : 'bi-arrow-counterclockwise'} me-2`}></i>
        {isRestoring ? 'Restoring...' : 'Restore'}
      </button>
    );
  };
  
  export default RestoreVersionButton;  