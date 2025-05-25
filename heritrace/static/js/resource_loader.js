/**
 * Reusable function to load resources via AJAX with pagination.
 *
 * @param {object} options - Configuration options.
 * @param {string} options.containerSelector - jQuery selector for the list container.
 * @param {string} options.noResultsSelector - jQuery selector for the "no results" message element.
 * @param {string} options.loadMoreSelector - jQuery selector for the "load more" button.
 * @param {string} options.apiUrl - The URL for the AJAX request.
 * @param {object} options.ajaxData - An object containing static data to send with the AJAX request (e.g., { subject_uri: '...' }).
 * @param {function} options.renderItemCallback - A function that takes a single result item and returns the HTML string for it.
 * @param {number} [options.resultsPerPage=5] - Number of items per page.
 * @param {string} [options.loadingHtml='<div class="text-center my-3"><div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div></div>'] - HTML for the loading indicator.
 * @param {string} [options.errorText='Error loading resources.'] - Text to display on AJAX error.
 */
function loadResources(options) {
    const {
        containerSelector,
        noResultsSelector,
        loadMoreSelector,
        apiUrl,
        ajaxData,
        renderItemCallback,
        resultsPerPage = 5,
        loadingHtml = '<div class="text-center my-3 resource-loading-indicator"><div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div></div>',
        errorText = 'Error loading resources.'
    } = options;
    
    const state = {
        isLoading: false,
        hasLoaded: false,
        error: null
    };
    
    const $container = $(containerSelector);
    const $noResults = $(noResultsSelector);
    const $loadMoreButton = $(loadMoreSelector);
    const $parent = $container.parent();

    let currentPage = 1;
    let totalLoaded = 0;
    let hasMore = true;
    let $loadingIndicator = null;

    function fetchData(page) {
        if (!hasMore) return;

        state.isLoading = true;
        state.hasLoaded = false;
        state.error = null;
        $container.data('loaderState', {...state});
        if ($loadingIndicator) {
            $loadingIndicator.remove();
        }
        $loadingIndicator = $(loadingHtml);
        $parent.append($loadingIndicator);
        $loadMoreButton.hide();

        const requestData = {
            ...ajaxData, // Include static data
            limit: resultsPerPage,
            offset: (page - 1) * resultsPerPage
        };

        $.ajax({
            url: apiUrl,
            method: 'GET',
            data: requestData,
            success: function handleSuccess(response) {
                if ($loadingIndicator) $loadingIndicator.remove();

                if (response.status === 'success' && response.results && response.results.length > 0) {
                    if (page === 1) {
                        $container.empty(); // Clear only on first load
                    }
                    $noResults.hide();

                    response.results.forEach(function(item) {
                        const itemHtml = renderItemCallback(item);
                        if (itemHtml) {
                            $container.append(itemHtml);
                        }
                    });

                    totalLoaded += response.results.length;
                    // Use response.has_more if available, otherwise estimate based on resultsPerPage
                    hasMore = response.has_more !== undefined ? response.has_more : (response.results.length === resultsPerPage);

                    $container.show();
                    if (hasMore) {
                        $loadMoreButton.show();
                    } else {
                        $loadMoreButton.hide();
                    }

                } else {
                    hasMore = false; // Stop loading if error or no results
                    if (page === 1) { // Only show "no results" if it's the first page and no results came back
                         if (response.status === 'success' && (!response.results || response.results.length === 0)) {
                            // Keep the original "no results" text if the API call was successful but empty
                         } else {
                            // Otherwise, show a generic error or the specific API message
                            $noResults.text(response.message || errorText);
                         }
                        $noResults.show();
                        $container.hide(); // Hide container if empty on first load
                    }
                    $loadMoreButton.hide(); // Hide button if error or no results on subsequent pages

                    if (response.status !== 'success') {
                        console.error(`Error fetching resources from ${apiUrl}:`, response.message);
                    }
                }
                // Update state after successful fetch
                $container.data('loaderState', {...state, isLoading: false, hasLoaded: true});
            },
            error: function handleError(xhr) {
                if ($loadingIndicator) $loadingIndicator.remove();
                hasMore = false; // Stop loading on error
                if (page === 1) {
                    $container.hide();
                    $noResults.text(errorText).show(); // Show generic error on first page AJAX fail
                }
                $loadMoreButton.hide(); // Hide button on error
                state.isLoading = false;
                state.error = xhr.statusText;
                $container.data('loaderState', {...state});
                console.error(`AJAX error fetching resources from ${apiUrl}:`, xhr.statusText);
            }
        });
    }

    fetchData(currentPage);
    
    $loadMoreButton.on('click', function() {
        currentPage++;
        fetchData(currentPage);
    });
    
    $container.data('refresh', function() {
        currentPage = 1;
        hasMore = true;
        fetchData(currentPage);
    });
} 