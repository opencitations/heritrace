import React, { useEffect } from 'react';

function EntityTimeline({ timelineData }) {
  useEffect(() => {
    new TL.Timeline('timeline-container', {
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
      <div id="timeline-container"></div>
    </div>
  );
}

export default EntityTimeline