// Utility functions for search functionality in Heritrace

// Function to encode search terms for Virtuoso text search
function encodeVirtuosoSearchTerm(term) {
    if (!term) return '';
    
    // Escape special characters for Virtuoso text search
    // These characters need special handling: " \ * ? {} [] ^ ~ ! - & | () : 
    return term
        .replace(/\\/g, '\\\\') // Backslashes need to be escaped twice
        .replace(/"/g, '\\"')    // Double quotes
        .replace(/\*/g, '\\*')    // Wildcards
        .replace(/\?/g, '\\?')    // Question mark wildcard
        .replace(/\{/g, '\\{')    // Curly braces
        .replace(/\}/g, '\\}')    // Curly braces
        .replace(/\[/g, '\\[')    // Square brackets
        .replace(/\]/g, '\\]')    // Square brackets
        .replace(/\^/g, '\\^')    // Caret
        .replace(/~/g, '\\~')     // Tilde
        .replace(/!/g, '\\!')     // Exclamation mark
        .replace(/-/g, '\\-')     // Hyphen
        .replace(/&/g, '\\&')     // Ampersand
        .replace(/\|/g, '\\|')    // Pipe
        .replace(/\(/g, '\\(')    // Parentheses
        .replace(/\)/g, '\\)')    // Parentheses
        .replace(/:/g, '\\:');    // Colon
}

// Function to escape special regex characters in a search term
function escapeRegexSpecialChars(term) {
    if (!term) return '';
    return term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}