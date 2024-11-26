import React, { useEffect } from 'react';
import Breadcrumb from '../Navigation';

function EntityTimeline({ timelineData }) {
  const { entityUri, entityLabel, entityClasses } = timelineData;

  const breadcrumbItems = [
    {
      label: `<em>${entityLabel}</em>`,
      href: `/about/${encodeURIComponent(entityUri)}`
    },
    {
      label: `History of <em>${entityLabel}</em>`,
      active: true
    }
  ];

  useEffect(() => {
    const timeline = new TL.Timeline('timeline-container', {
      events: timelineData.events.map((event, index, array) => {
        if (index === array.length - 1 && event.end_date === "Present") {
          return {
            ...event,
            end_date: {
              display_date: "Present"
            }
          };
        }
        return event;
      })
    });

    return () => {
      const container = document.getElementById('timeline-container');
      if (container) {
        container.innerHTML = '';
      }
    };
  }, [timelineData]);

  return (
    <div className="space-y-4">
      <Breadcrumb items={breadcrumbItems} />

      <h2 className="mb-4 word-wrap">
        Version history for <em dangerouslySetInnerHTML={{ __html: entityLabel }} />
      </h2>

      <div id="timeline-container"></div>

      <style>{`
        #timeline-container {
            width: 100%;
            height: 70vh;
        }
        .tl-text-content p {
          margin-bottom: 5px;
        }
        .modifications h4 {
          margin-top: 10px;
          margin-bottom: 5px;
          font-size: 1em;
          font-weight: bold;
        }
        .modifications ul {
          list-style-type: none;
          padding-left: 0;
          margin-bottom: 10px;
        }
        .modifications li {
          margin-bottom: 3px;
        }
        .tl-timeline a.view-version {
          color: #0d6efd;
          text-decoration: none;
        }
        .tl-timeline a.view-version:hover {
          color: white;
        }
        .tl-slide {
          padding: 2rem 0;
        }
        .tl-timeline .tl-slide-titleslide .tl-headline-date,
        .tl-timeline .tl-slide-titleslide .tl-headline {
          font-size: 32px !important;
          line-height: 36px !important;
        }
        .tl-timeline .tl-slide-titleslide .tl-text .tl-text-content p {
          font-size: 18px !important;
          line-height: 24px !important;
        }
        .tl-text-content .orcid-attribution img,
        .tl-text-content .zenodo-attribution img {
          vertical-align: middle;
          margin-right: 4px;
        }
        .tl-text-content .text-muted {
          color: #6c757d !important;
          font-size: 0.9em;
        }
        .tl-text-content .small {
          font-size: 85%;
        }
        .tl-skinny .tl-slidenav-next .tl-slidenav-icon {
          margin-left: 0;
        }
      `}</style>
    </div>
  );
}

export default EntityTimeline