from datetime import datetime
from functools import lru_cache
from time import sleep
from urllib.parse import urlparse

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout


class ZenodoRequestError(Exception):
    """Custom exception for Zenodo API errors"""
    pass

def is_zenodo_url(url):
    """Check if a URL is a Zenodo URL or DOI."""
    try:
        parsed = urlparse(url)
        # Check for direct Zenodo URLs
        if parsed.netloc in ['zenodo.org', 'www.zenodo.org']:
            return True
        
        # Check for DOI URLs
        if parsed.netloc in ['doi.org', 'www.doi.org']:
            doi_path = parsed.path.lstrip('/')
            return doi_path.startswith('10.5281/zenodo.')
            
        # Check for raw DOI strings
        if url.startswith('10.5281/zenodo.'):
            return True
            
        return False
    except:
        return False

def extract_zenodo_id(url):
    """
    Extract Zenodo record ID from URL or DOI.
    
    Args:
        url (str): The URL or DOI to parse
    
    Returns:
        str: The Zenodo record ID or None if not found
    """
    try:
        parsed = urlparse(url)
        
        # Handle DOI URLs
        if parsed.netloc in ['doi.org', 'www.doi.org']:
            doi_path = parsed.path.lstrip('/')
            if doi_path.startswith('10.5281/zenodo.'):
                return doi_path.split('10.5281/zenodo.')[1]
        
        # Handle direct Zenodo URLs
        elif parsed.netloc in ['zenodo.org', 'www.zenodo.org']:
            path_parts = parsed.path.strip('/').split('/')
            if 'record' in path_parts:
                return path_parts[path_parts.index('record') + 1]
            elif 'records' in path_parts:
                return path_parts[path_parts.index('records') + 1]
        
        # Handle raw DOI strings
        elif url.startswith('10.5281/zenodo.'):
            return url.split('10.5281/zenodo.')[1]
            
        return None
    except:
        return None

def make_request_with_retry(url, headers, max_retries=3, initial_delay=1):
    """
    Make HTTP request with exponential backoff retry strategy.
    
    Args:
        url (str): The URL to request
        headers (dict): Request headers
        max_retries (int): Maximum number of retry attempts
        initial_delay (int): Initial delay between retries in seconds
        
    Returns:
        requests.Response: The response if successful
        
    Raises:
        ZenodoRequestError: If all retries fail
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=5)
            
            # Check if we got rate limited
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', delay))
                sleep(retry_after)
                continue
                
            # If we get a 5xx error, retry
            if 500 <= response.status_code < 600:
                raise ZenodoRequestError(f"Server error: {response.status_code}")
                
            response.raise_for_status()
            return response
            
        except (RequestException, ConnectionError, Timeout) as e:
            last_exception = e
            
            # Don't sleep after the last attempt
            if attempt < max_retries - 1:
                sleep(delay)
                delay *= 2  # Exponential backoff
                
    raise ZenodoRequestError(f"Failed after {max_retries} attempts. Last error: {str(last_exception)}")

@lru_cache(maxsize=1000)
def get_zenodo_data(record_id):
    """Fetch record data from Zenodo API with caching and retry logic."""
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'YourApp/1.0 (your@email.com)'
    }
    
    try:
        response = make_request_with_retry(
            f'https://zenodo.org/api/records/{record_id}',
            headers=headers
        )
        
        data = response.json()
        metadata = data.get('metadata', {})
        
        # Extract all possible metadata for APA citation
        result = {
            'title': metadata.get('title'),
            'authors': [
                {
                    'name': creator.get('name', ''),
                    'orcid': creator.get('orcid', ''),
                    'affiliation': creator.get('affiliation', '')
                }
                for creator in metadata.get('creators', [])
            ],
            'doi': metadata.get('doi'),
            'publication_date': metadata.get('publication_date'),
            'version': metadata.get('version', ''),
            'type': metadata.get('resource_type', {}).get('type', ''),
            'subtype': metadata.get('resource_type', {}).get('subtype', ''),
            'journal': metadata.get('journal', {}).get('title', ''),
            'journal_volume': metadata.get('journal', {}).get('volume', ''),
            'journal_issue': metadata.get('journal', {}).get('issue', ''),
            'journal_pages': metadata.get('journal', {}).get('pages', ''),
            'conference': metadata.get('conference', {}).get('title', ''),
            'conference_acronym': metadata.get('conference', {}).get('acronym', ''),
            'conference_place': metadata.get('conference', {}).get('place', ''),
            'conference_date': metadata.get('conference', {}).get('date', ''),
            'publisher': metadata.get('publisher', ''),
            'keywords': metadata.get('keywords', []),
            'description': metadata.get('description', ''),
            'access_right': metadata.get('access_right', ''),
            'language': metadata.get('language', ''),
            'record_id': record_id,
            'notes': metadata.get('notes', '')
        }
        
        return result
            
    except ZenodoRequestError:
        return None

def format_apa_date(date_str):
    """Format a date in APA style (YYYY, Month DD)."""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%Y, %B %d')
    except ValueError:
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m')
            return date_obj.strftime('%Y, %B')
        except ValueError:
            try:
                date_obj = datetime.strptime(date_str, '%Y')
                return date_obj.strftime('%Y')
            except ValueError:
                return date_str

def format_authors_apa(authors):
    """Format author list in APA style."""
    if not authors:
        return ""
        
    if len(authors) == 1:
        author = authors[0]['name']
        # Split on last comma for "Lastname, Firstname" format
        parts = author.split(',', 1)
        if len(parts) > 1:
            return f"{parts[0].strip()}, {parts[1].strip()}"
        return author
        
    if len(authors) == 2:
        return f"{authors[0]['name']} & {authors[1]['name']}"
        
    if len(authors) > 2:
        author_list = ", ".join(a['name'] for a in authors[:-1])
        return f"{author_list}, & {authors[-1]['name']}"
    
    return ""

def format_zenodo_source(url):
    """Format Zenodo source for display with full APA citation."""
    if not is_zenodo_url(url):
        return f'<a href="{url}" target="_blank">{url}</a>'
        
    record_id = extract_zenodo_id(url)
    if not record_id:
        return f'<a href="{url}" target="_blank">{url}</a>'
        
    record_data = get_zenodo_data(record_id)
    if not record_data:
        return f'<a href="{url}" target="_blank">{url}</a>'

    # Create proper link URL for DOI
    link_url = f"https://doi.org/{record_data['doi']}" if record_data['doi'] else f"https://zenodo.org/record/{record_id}"

    # Build APA citation
    citation_parts = []
    
    # Authors and Date
    authors = format_authors_apa(record_data['authors'])
    pub_date = format_apa_date(record_data['publication_date']) if record_data['publication_date'] else 'n.d.'
    citation_parts.append(f"{authors} ({pub_date})")
    
    # Title
    title = record_data['title']
    if record_data['type'] == 'dataset':
        title = f"{title} [Data set]"
    elif record_data['type'] == 'software':
        title = f"{title} [Computer software]"
    citation_parts.append(title)
    
    # Container info (journal/conference)
    if record_data['journal']:
        journal_info = [record_data['journal']]
        if record_data['journal_volume']:
            journal_info.append(f"{record_data['journal_volume']}")
            if record_data['journal_issue']:
                journal_info.append(f"({record_data['journal_issue']})")
        if record_data['journal_pages']:
            journal_info.append(f", {record_data['journal_pages']}")
        citation_parts.append(", ".join(journal_info))
    elif record_data['conference']:
        conf_info = [f"In {record_data['conference']}"]
        if record_data['conference_place']:
            conf_info.append(f" ({record_data['conference_place']})")
        citation_parts.append("".join(conf_info))
    
    # Publisher info
    if record_data['publisher']:
        citation_parts.append(record_data['publisher'])
    
    # Version info
    if record_data['version']:
        citation_parts.append(f"Version {record_data['version']}")
    
    # DOI
    if record_data['doi']:
        citation_parts.append(f"https://doi.org/{record_data['doi']}")

    html = f'<a href="{url}" target="_blank" class="zenodo-attribution">'
    html += f'<img src="/static/images/zenodo-logo.png" alt="Zenodo" class="zenodo-icon mb-1 mx-1" style="width: 50px; height: 25px; margin-bottom: .3rem !important">'
    html += '. '.join(citation_parts)
    html += '</a>'
    
    # Add additional metadata if available
    extra_info = []
    if record_data['type']:
        extra_info.append(f"Type: {record_data['type']}")
        if record_data['subtype']:
            extra_info[-1] += f" ({record_data['subtype']})"
    if record_data['keywords']:
        extra_info.append(f"Keywords: {', '.join(record_data['keywords'])}")
    if record_data['language']:
        extra_info.append(f"Language: {record_data['language']}")
    if record_data['access_right']:
        extra_info.append(f"Access: {record_data['access_right']}")
    
    if extra_info:
        html += f'<div class="text-muted small mt-1">{" | ".join(extra_info)}</div>'
    
    return html